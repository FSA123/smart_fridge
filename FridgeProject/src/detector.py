import os
import time
import threading
from datetime import datetime, timedelta
from ultralytics import YOLO
from src.database import db_session
from src.models import Item

class FoodDetector(threading.Thread):
    def __init__(self, image_folder="images", model_path="yolov8n.pt", interval=5, grace_period=300):
        super().__init__()
        self.image_folder = image_folder
        self.model_path = model_path
        self.interval = interval
        self.grace_period = grace_period # Seconds before marking undetected item as removed
        self.processed_images = set()
        self.running = True
        self.daemon = True # Daemon thread exits when main program exits

        # Load model
        print(f"Loading YOLO model from {self.model_path}...")
        try:
            self.model = YOLO(self.model_path)
            print("Model loaded successfully.")
        except Exception as e:
            print(f"Error loading model: {e}")
            self.running = False

    def run(self):
        print("FoodDetector started monitoring...")
        while self.running:
            try:
                self.process_folder()
                # We can also run a cleanup based on real time for items not seen recently
                # but if we process images, we do cleanup there based on image time.
                # If no images come, we might want to cleanup based on real time?
                # For now, let's rely on image processing to trigger updates.
                pass
            except Exception as e:
                print(f"Error in detector loop: {e}")
            time.sleep(self.interval)

    def stop(self):
        self.running = False

    def get_timestamp_from_filename(self, filename):
        try:
            # filename format: capture_YYYYMMDD_HHMMSS.jpg
            base = filename.replace("capture_", "").replace(".jpg", "")
            return datetime.strptime(base, "%Y%m%d_%H%M%S")
        except ValueError:
            # If format doesn't match, return None or current time
            return datetime.utcnow()

    def process_folder(self):
        if not os.path.exists(self.image_folder):
            os.makedirs(self.image_folder)

        current_files = sorted([f for f in os.listdir(self.image_folder) if f.endswith(".jpg")])

        # Process only new files
        new_files = [f for f in current_files if f not in self.processed_images]

        for file in new_files:
            self.processed_images.add(file)
            print(f"Processing {file}...")
            img_path = os.path.join(self.image_folder, file)
            timestamp = self.get_timestamp_from_filename(file)
            self.analyze_image(img_path, timestamp)

    def analyze_image(self, img_path, timestamp):
        # 1. Detect
        try:
            results = self.model.predict(source=img_path, conf=0.25, save=False, verbose=False)

            detected_counts = {}
            for result in results:
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    label = self.model.names[class_id]
                    detected_counts[label] = detected_counts.get(label, 0) + 1

            print(f"Detected in {img_path} at {timestamp}: {detected_counts}")
            self.update_database(detected_counts, img_path, timestamp)
            self.cleanup_items(timestamp)

        except Exception as e:
            print(f"Error analyzing image {img_path}: {e}")

    def update_database(self, detected_counts, img_path, timestamp):
        # Get all active items
        active_items = Item.query.filter_by(status='active').all()

        # Group active items by label
        db_counts = {}
        for item in active_items:
            if item.label not in db_counts:
                db_counts[item.label] = []
            db_counts[item.label].append(item)

        # Iterate over all detected labels
        all_labels = set(detected_counts.keys())

        for label in all_labels:
            detected_n = detected_counts.get(label, 0)
            db_items = db_counts.get(label, [])
            db_n = len(db_items)

            # Sort db_items by last_confirmed descending (most recently seen first)
            # This ensures we update the ones we are likely tracking
            db_items.sort(key=lambda x: x.last_confirmed, reverse=True)

            # Update existing items
            matched_count = min(detected_n, db_n)
            for i in range(matched_count):
                item = db_items[i]
                item.last_confirmed = timestamp
                item.image_path = img_path

            # Create new items if detected > db
            if detected_n > db_n:
                diff = detected_n - db_n
                for _ in range(diff):
                    new_item = Item(label=label, image_path=img_path, entry_date=timestamp, last_confirmed=timestamp)
                    db_session.add(new_item)
                print(f"Added {diff} new {label}(s).")

        db_session.commit()

    def cleanup_items(self, current_time):
        # Check for items that haven't been seen for grace_period relative to current_time
        limit = current_time - timedelta(seconds=self.grace_period)

        expired_items = Item.query.filter(Item.status == 'active', Item.last_confirmed < limit).all()

        if expired_items:
            for item in expired_items:
                item.status = 'history'
                print(f"Item {item.label} (ID: {item.id}) marked as removed (expired).")
            db_session.commit()
