import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestFoodDetectorTracker(unittest.TestCase):
    def setUp(self):
        self.modules_patcher = patch.dict(sys.modules, {
            'src.product_recognizer': MagicMock(),
            'src.database': MagicMock(),
            'src.models': MagicMock(),
            'ultralytics': MagicMock(),
            'easyocr': MagicMock(),
            'clip': MagicMock(),
            'torch': MagicMock(),
            'cv2': MagicMock(),
        })
        self.modules_patcher.start()

        # Remove cached detector module to force re-import with our mocks
        sys.modules.pop('src.detector', None)

        from src.detector import FoodDetector
        with patch('src.detector.ProductRecognizer') as MockRecognizer:
            self.detector = FoodDetector(model_path="dummy_path", grace_period=30)

        self.detector.active_tracks = {}
        self.detector.next_track_id = 1
        self.start_time = datetime(2023, 1, 1, 12, 0, 0)

    def tearDown(self):
        self.modules_patcher.stop()
        sys.modules.pop('src.detector', None)

    def test_initial_detection(self):
        """Test that new detections create new tracks."""
        detections = [
            {'label': 'Apple', 'confidence': 0.9, 'bbox': [100, 100, 200, 200]},
            {'label': 'Banana', 'confidence': 0.8, 'bbox': [300, 300, 400, 400]}
        ]

        counts = self.detector._update_tracks(detections, self.start_time)

        self.assertEqual(len(self.detector.active_tracks), 2)
        self.assertEqual(counts['Apple'], 1)
        self.assertEqual(counts['Banana'], 1)

    def test_update_existing_track(self):
        """Test that detection close to existing track updates it."""
        self.detector.active_tracks[1] = {
            'label': 'Apple',
            'bbox': [100, 100, 200, 200],
            'last_seen': self.start_time
        }
        self.detector.next_track_id = 2

        new_time = self.start_time + timedelta(seconds=1)
        detections = [{'label': 'Apple', 'confidence': 0.9, 'bbox': [105, 105, 205, 205]}]

        counts = self.detector._update_tracks(detections, new_time)

        self.assertEqual(len(self.detector.active_tracks), 1)
        self.assertEqual(counts['Apple'], 1)
        track = self.detector.active_tracks[1]
        self.assertEqual(track['last_seen'], new_time)
        self.assertEqual(track['bbox'], [105, 105, 205, 205])

    def test_new_track_far_distance(self):
        """Test that detection far from existing track creates new track."""
        self.detector.active_tracks[1] = {
            'label': 'Apple',
            'bbox': [100, 100, 200, 200],
            'last_seen': self.start_time
        }
        self.detector.next_track_id = 2

        new_time = self.start_time + timedelta(seconds=1)
        detections = [{'label': 'Banana', 'confidence': 0.9, 'bbox': [500, 500, 600, 600]}]

        counts = self.detector._update_tracks(detections, new_time)

        self.assertEqual(len(self.detector.active_tracks), 2)
        self.assertEqual(counts['Apple'], 1)
        self.assertEqual(counts['Banana'], 1)

    def test_track_expiration(self):
        """Test that stale tracks are removed."""
        self.detector.active_tracks[1] = {
            'label': 'Apple',
            'bbox': [100, 100, 200, 200],
            'last_seen': self.start_time
        }

        new_time = self.start_time + timedelta(seconds=31)
        counts = self.detector._update_tracks([], new_time)

        self.assertEqual(len(self.detector.active_tracks), 0)
        self.assertEqual(counts.get('Apple', 0), 0)

    def test_label_persistence_when_new_is_unknown(self):
        """Test that known label persists if new detection is Unknown."""
        self.detector.active_tracks[1] = {
            'label': 'Apple',
            'bbox': [100, 100, 200, 200],
            'last_seen': self.start_time
        }

        new_time = self.start_time + timedelta(seconds=1)
        detections = [{'label': 'Unknown', 'confidence': 0.5, 'bbox': [100, 100, 200, 200]}]

        self.detector._update_tracks(detections, new_time)
        self.assertEqual(self.detector.active_tracks[1]['label'], 'Apple')

    def test_label_update_high_confidence(self):
        """Test that label updates if new detection has high confidence."""
        self.detector.active_tracks[1] = {
            'label': 'Apple',
            'bbox': [100, 100, 200, 200],
            'last_seen': self.start_time
        }

        new_time = self.start_time + timedelta(seconds=1)
        detections = [{'label': 'Banana', 'confidence': 0.85, 'bbox': [100, 100, 200, 200]}]

        self.detector._update_tracks(detections, new_time)
        self.assertEqual(self.detector.active_tracks[1]['label'], 'Banana')

if __name__ == '__main__':
    unittest.main()
