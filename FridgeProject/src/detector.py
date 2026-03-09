import os
import time
import threading
from datetime import datetime, timedelta
from src.product_recognizer import ProductRecognizer
from src.database import db_session
from src.models import Item
from src.config import IMAGES_DIR

class FoodDetector(threading.Thread):
    def __init__(self, image_folder=IMAGES_DIR, model_path="yolov8n.pt", interval=5, grace_period=300):
        super().__init__()
        self.image_folder = image_folder
        self.model_path = model_path
        self.interval = interval
        self.grace_period = grace_period # Seconds before marking undetected item as removed
        self.processed_images = set()

        # Optimization: Prevent processing storm on restart by skipping old images
        if os.path.exists(self.image_folder):
            existing_files = sorted([f for f in os.listdir(self.image_folder) if f.endswith(".jpg")])
            # Keep the last 5 images for context/track initialization, skip the rest
            if len(existing_files) > 5:
                self.processed_images.update(existing_files[:-5])
                print(f"Skipped {len(existing_files) - 5} old images to prevent processing storm.")

        self.running = True
        self.daemon = True # Daemon thread exits when main program exits

        # Track active objects for temporal consistency
        # Format: {tracking_id: {'label': label, 'bbox': [x1, y1, x2, y2], 'last_seen': timestamp}}
        self.active_tracks = {}
        self.next_track_id = 1

        # Load model
        print(f"Loading ProductRecognizer with model {self.model_path}...")
        try:
            self.recognizer = ProductRecognizer(model_path=self.model_path)
            print("ProductRecognizer loaded successfully.")
        except Exception as e:
            print(f"Error loading ProductRecognizer: {e}")
            self.running = False

    def run(self):
        print("FoodDetector started monitoring...")
        while self.running:
            try:
                self.process_folder()
                # Note: Cleanup is handled within process_folder() based on image timestamps.
                # Real-time cleanup is intentionally avoided to prevent expiring items
                # during camera sleep intervals.
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

        all_files = os.listdir(self.image_folder)
        jpg_files = {f for f in all_files if f.endswith(".jpg")}

        # Memory leak fix: remove processed images that no longer exist in the folder
        self.processed_images.intersection_update(jpg_files)

        # Process only new files, in sorted order for deterministic processing
        new_files = sorted([f for f in jpg_files if f not in self.processed_images])

        for file in new_files:
            self.processed_images.add(file)
            print(f"Processing {file}...")
            img_path = os.path.join(self.image_folder, file)
            timestamp = self.get_timestamp_from_filename(file)
            self.analyze_image(img_path, timestamp)

    def analyze_image(self, img_path, timestamp):
        # 1. Recognize
        try:
            detections = self.recognizer.recognize(img_path)

            # 2. Update Tracks (Temporal Consistency)
            current_counts = self._update_tracks(detections, timestamp)

            print(f"Detected in {img_path} at {timestamp}: {current_counts}")
            self.update_database(current_counts, img_path, timestamp)
            self.cleanup_items(timestamp)

        except Exception as e:
            print(f"Error analyzing image {img_path}: {e}")

    def _update_tracks(self, detections, timestamp):
        """
        Updates active tracks with new detections using centroid matching.
        Returns a dictionary of counts for the current frame.
        """
        # Calculate centroids for new detections
        new_objects = []
        for det in detections:
            bbox = det['bbox']
            cx = (bbox[0] + bbox[2]) / 2
            cy = (bbox[1] + bbox[3]) / 2
            new_objects.append({
                'centroid': (cx, cy),
                'bbox': bbox,
                'label': det['label'],
                'confidence': det['confidence']
            })

        # Match with active tracks
        matched_track_ids = set()

        # Simple greedy matching
        for obj in new_objects:
            best_track_id = None
            min_dist = float('inf')

            for track_id, track in self.active_tracks.items():
                if track_id in matched_track_ids:
                    continue

                # Check if track is stale (not seen in last 60 seconds, handled by cleanup but good to check)
                # Here we just check distance
                tcx = (track['bbox'][0] + track['bbox'][2]) / 2
                tcy = (track['bbox'][1] + track['bbox'][3]) / 2

                dist = ((obj['centroid'][0] - tcx)**2 + (obj['centroid'][1] - tcy)**2)**0.5

                # Threshold for matching (e.g., 100 pixels)
                if dist < 100 and dist < min_dist:
                    min_dist = dist
                    best_track_id = track_id

            if best_track_id:
                # Update existing track
                matched_track_ids.add(best_track_id)
                track = self.active_tracks[best_track_id]

                # Logic: If object was previously identified with high confidence,
                # and current confidence is low (occlusion?), keep old label.
                # Otherwise, update label if current is better or different.

                # If current is "Unknown", keep old label
                if obj['label'] == "Unknown" and track['label'] != "Unknown":
                    final_label = track['label']
                # If current is high confidence, update
                elif obj['confidence'] > 0.8:
                    final_label = obj['label']
                else:
                    # Moderate confidence, maybe update?
                    # If old label was high confidence (we don't store old conf, but assume track label is good)
                    # Let's trust the track label if it's specific and current is generic?
                    # For now, just update.
                    final_label = obj['label']

                track['bbox'] = obj['bbox']
                track['last_seen'] = timestamp
                track['label'] = final_label

            else:
                # Create new track
                new_id = self.next_track_id
                self.next_track_id += 1
                self.active_tracks[new_id] = {
                    'label': obj['label'],
                    'bbox': obj['bbox'],
                    'last_seen': timestamp
                }

        # Remove stale tracks (not seen in this frame? No, we keep them if grace period allows,
        # but for *counting* purposes in this frame, we only count what we matched or added?
        # Actually, if an object is occluded completely, we might still want to count it?
        # The requirement says: "If a product ... hasn't been 'removed' (tracked via centroid displacement)".
        # This implies we keep tracking it.
        # But `analyze_image` returns counts for `update_database`.
        # `update_database` updates `last_confirmed`.
        # If we don't return it in counts, `update_database` won't update `last_confirmed`.
        # If we return it, `update_database` will update `last_confirmed`.

        # So we should return counts for ALL active tracks that are not "expired".
        # But `cleanup_items` handles expiration from DB.
        # Here we handle tracks.

        # Let's count all active tracks that have been seen recently (e.g. in this frame or very recently).
        # Actually, `update_database` uses the count to update DB.
        # If we report a count, it assumes it's present.

        counts = {}
        # Clean up internal tracks that are too old (e.g. > grace_period)
        limit = timestamp - timedelta(seconds=self.grace_period)
        keys_to_remove = []

        for track_id, track in self.active_tracks.items():
            if track['last_seen'] < limit:
                keys_to_remove.append(track_id)
            else:
                # Include in counts?
                # If we only include items seen IN THIS FRAME, we are strict.
                # If we include items seen recently (temporal persistence), we are robust to flickering.
                # I'll include items seen in the last 10 seconds (short persistence) to handle temporary occlusion/flicker.
                if track['last_seen'] >= timestamp - timedelta(seconds=10):
                    lbl = track['label']
                    if lbl != "Unknown":
                        counts[lbl] = counts.get(lbl, 0) + 1

        for k in keys_to_remove:
            del self.active_tracks[k]

        return counts

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
