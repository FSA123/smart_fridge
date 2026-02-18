import os
import time
import threading
from datetime import datetime, timedelta
import numpy as np
from PIL import Image
from ultralytics import YOLO
from src.database import db_session
from src.models import Item

class FoodDetector(threading.Thread):
    def __init__(self, image_folder="images", model_path="yolov8s-world.pt", interval=5, grace_period=300):
        super().__init__()
        self.image_folder = image_folder
        self.model_path = model_path
        self.interval = interval
        self.grace_period = grace_period
        self.processed_images = set()
        self.running = True
        self.daemon = True

        # Zero-Shot Classes
        self.target_classes = [
            "milk carton", "egg carton", "cheese block", "butter", "apple",
            "tomato", "potato", "bread loaf", "juice bottle"
        ]

        # Crops directory
        self.crops_dir = "src/web/static/crops"
        if not os.path.exists(self.crops_dir):
            os.makedirs(self.crops_dir)

        # Load model
        print(f"Loading YOLO model from {self.model_path}...")
        try:
            self.model = YOLO(self.model_path)
            # Set classes for YOLO-World
            self.model.set_classes(self.target_classes)
            print("Model loaded and classes set.")
        except Exception as e:
            print(f"Error loading model: {e}")
            self.running = False

    def run(self):
        print("FoodDetector started monitoring...")
        while self.running:
            try:
                self.process_folder()
                self.cleanup_crops()
            except Exception as e:
                print(f"Error in detector loop: {e}")
            time.sleep(self.interval)

    def stop(self):
        self.running = False

    def get_timestamp_from_filename(self, filename):
        try:
            base = filename.replace("capture_", "").replace(".jpg", "")
            return datetime.strptime(base, "%Y%m%d_%H%M%S")
        except ValueError:
            return datetime.utcnow()

    def process_folder(self):
        if not os.path.exists(self.image_folder):
            os.makedirs(self.image_folder)

        current_files = sorted([f for f in os.listdir(self.image_folder) if f.endswith(".jpg")])
        new_files = [f for f in current_files if f not in self.processed_images]

        for file in new_files:
            self.processed_images.add(file)
            print(f"Processing {file}...")
            img_path = os.path.join(self.image_folder, file)
            timestamp = self.get_timestamp_from_filename(file)
            self.analyze_image(img_path, timestamp)

    def analyze_image(self, img_path, timestamp):
        try:
            # Predict with confidence threshold 0.3, NMS 0.5 (iou argument in ultralytics)
            results = self.model.predict(source=img_path, conf=0.3, iou=0.5, save=False, verbose=False)

            detected_items = [] # List of dicts: {label, crop_path}

            # Open image for cropping
            with Image.open(img_path) as im:
                for result in results:
                    for box in result.boxes:
                        # Get class and label
                        class_id = int(box.cls[0])
                        original_label = self.model.names[class_id]

                        # Get coordinates
                        x1, y1, x2, y2 = map(int, box.xyxy[0])

                        # Crop
                        crop = im.crop((x1, y1, x2, y2))

                        # Liquid Logic
                        final_label = self.apply_liquid_logic(crop, original_label)

                        # Save Crop
                        safe_label = final_label.replace(' ', '_').replace('/', '_')
                        crop_filename = f"{safe_label}_{timestamp.strftime('%Y%m%d_%H%M%S_%f')}.jpg"
                        crop_path_rel = os.path.join("static/crops", crop_filename)
                        crop_path_full = os.path.join(self.crops_dir, crop_filename)
                        crop.save(crop_path_full)

                        detected_items.append({
                            'label': final_label,
                            'crop_path': crop_path_rel
                        })

            print(f"Detected in {img_path}: {[d['label'] for d in detected_items]}")
            self.update_database(detected_items, img_path, timestamp)
            self.cleanup_items(timestamp)

        except Exception as e:
            print(f"Error analyzing image {img_path}: {e}")

    def apply_liquid_logic(self, crop_img, label):
        # Rule: If "bottle" or "carton" in label, check whiteness
        if "bottle" in label.lower() or "carton" in label.lower():
            # Analyze center pixels
            # Convert to numpy array
            arr = np.array(crop_img)
            h, w, _ = arr.shape

            # Take center 50%
            center_h_start = int(h * 0.25)
            center_h_end = int(h * 0.75)
            center_w_start = int(w * 0.25)
            center_w_end = int(w * 0.75)

            center_region = arr[center_h_start:center_h_end, center_w_start:center_w_end]

            # Calculate average RGB
            if center_region.size > 0:
                avg_rgb = np.mean(center_region, axis=(0, 1))
                # Check whiteness: R, G, B > 200
                if np.all(avg_rgb > 200):
                    return "Milk"
                else:
                    # If it was milk carton but not white, maybe it's juice?
                    # Or if it was juice bottle but not white, keep it juice.
                    # Prompt: "Otherwise, label it as 'Juice/Drink'"
                    return "Juice/Drink"
            return "Juice/Drink" # Default if analysis fails or empty

        return label

    def update_database(self, detected_items, img_path, timestamp):
        # detected_items is a list of {label, crop_path}

        # Get all active items
        active_items = Item.query.filter_by(status='active').all()

        # Group active items by label
        db_counts = {}
        for item in active_items:
            if item.label not in db_counts:
                db_counts[item.label] = []
            db_counts[item.label].append(item)

        # Group detected items by label
        detected_counts = {}
        for d in detected_items:
            lbl = d['label']
            if lbl not in detected_counts:
                detected_counts[lbl] = []
            detected_counts[lbl].append(d)

        all_labels = set(detected_counts.keys())

        for label in all_labels:
            d_list = detected_counts.get(label, [])
            detected_n = len(d_list)

            db_list = db_counts.get(label, [])
            db_n = len(db_list)

            # Update existing items
            # We match detections to existing items.
            # Ideally we'd match by location, but here we just match by count
            matched_count = min(detected_n, db_n)

            # Sort db_items by last_confirmed to update most recent ones first?
            # actually it doesn't matter much without tracking ID.
            db_list.sort(key=lambda x: x.last_confirmed, reverse=True)

            for i in range(matched_count):
                item = db_list[i]
                item.last_confirmed = timestamp
                item.image_path = img_path
                item.crop_path = d_list[i]['crop_path'] # Update with new crop

            # Create new items
            if detected_n > db_n:
                diff = detected_n - db_n
                for i in range(diff):
                    # We need to take the remaining detections
                    # The first matched_count were used above.
                    # So we take from index matched_count to end
                    # Actually, the loop above used d_list[0]...d_list[matched_count-1]
                    # Wait, no. I iterated i in range(matched_count).
                    # I should assign d_list[i] to db_list[i].

                    # For new items, we use d_list[db_n + i]
                    d_item = d_list[db_n + i]
                    new_item = Item(
                        label=label,
                        image_path=img_path,
                        crop_path=d_item['crop_path'],
                        entry_date=timestamp,
                        last_confirmed=timestamp
                    )
                    db_session.add(new_item)
                print(f"Added {diff} new {label}(s).")

        db_session.commit()

    def cleanup_items(self, current_time):
        limit = current_time - timedelta(seconds=self.grace_period)
        expired_items = Item.query.filter(Item.status == 'active', Item.last_confirmed < limit).all()
        if expired_items:
            for item in expired_items:
                item.status = 'history'
                print(f"Item {item.label} marked as removed.")
            db_session.commit()

    def cleanup_crops(self):
        # Delete crops older than 24h
        now = time.time()
        for f in os.listdir(self.crops_dir):
            fpath = os.path.join(self.crops_dir, f)
            if os.stat(fpath).st_mtime < now - 86400: # 24 hours
                os.remove(fpath)
                print(f"Deleted old crop: {f}")
