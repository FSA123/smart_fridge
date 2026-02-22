import unittest
from unittest.mock import MagicMock, patch
import sys
from datetime import datetime, timedelta

# Mock dependencies before import to avoid errors in minimal environment
sys.modules['src.product_recognizer'] = MagicMock()
sys.modules['src.database'] = MagicMock()
sys.modules['src.models'] = MagicMock()
sys.modules['ultralytics'] = MagicMock()
sys.modules['easyocr'] = MagicMock()
sys.modules['clip'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['cv2'] = MagicMock()

# Now import detector
from src.detector import FoodDetector

class TestFoodDetectorTracker(unittest.TestCase):
    def setUp(self):
        # Prevent detector from doing heavy init
        with patch('src.detector.ProductRecognizer') as MockRecognizer:
            self.detector = FoodDetector(model_path="dummy_path", grace_period=30)

        # Ensure active_tracks is empty
        self.detector.active_tracks = {}
        self.detector.next_track_id = 1

        # Set a fixed start time
        self.start_time = datetime(2023, 1, 1, 12, 0, 0)

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

        # Verify track details
        track_ids = list(self.detector.active_tracks.keys())
        # Sort by label to ensure deterministic check
        tracks_by_label = {v['label']: v for k, v in self.detector.active_tracks.items()}

        self.assertEqual(tracks_by_label['Apple']['last_seen'], self.start_time)
        self.assertEqual(tracks_by_label['Banana']['last_seen'], self.start_time)

    def test_update_existing_track(self):
        """Test that detection close to existing track updates it."""
        # Setup existing track
        initial_bbox = [100, 100, 200, 200]
        self.detector.active_tracks[1] = {
            'label': 'Apple',
            'bbox': initial_bbox,
            'last_seen': self.start_time
        }
        self.detector.next_track_id = 2

        # New detection slightly moved
        new_time = self.start_time + timedelta(seconds=1)
        detections = [
            {'label': 'Apple', 'confidence': 0.9, 'bbox': [105, 105, 205, 205]} # Centroid moved slightly
        ]

        counts = self.detector._update_tracks(detections, new_time)

        self.assertEqual(len(self.detector.active_tracks), 1)
        self.assertEqual(counts['Apple'], 1)

        # Verify track updated
        track = self.detector.active_tracks[1]
        self.assertEqual(track['last_seen'], new_time)
        self.assertEqual(track['bbox'], [105, 105, 205, 205])

    def test_new_track_far_distance(self):
        """Test that detection far from existing track creates new track."""
        # Setup existing track
        self.detector.active_tracks[1] = {
            'label': 'Apple',
            'bbox': [100, 100, 200, 200],
            'last_seen': self.start_time
        }
        self.detector.next_track_id = 2

        # New detection far away
        new_time = self.start_time + timedelta(seconds=1)
        detections = [
            {'label': 'Banana', 'confidence': 0.9, 'bbox': [500, 500, 600, 600]}
        ]

        counts = self.detector._update_tracks(detections, new_time)

        self.assertEqual(len(self.detector.active_tracks), 2)
        self.assertEqual(counts['Apple'], 1) # Existing track included (persistence)
        self.assertEqual(counts['Banana'], 1)

        self.assertIn(2, self.detector.active_tracks)
        self.assertEqual(self.detector.active_tracks[2]['label'], 'Banana')

    def test_track_expiration(self):
        """Test that stale tracks are removed."""
        # Setup existing track
        self.detector.active_tracks[1] = {
            'label': 'Apple',
            'bbox': [100, 100, 200, 200],
            'last_seen': self.start_time
        }

        # Time passes beyond grace period (30s set in setUp)
        new_time = self.start_time + timedelta(seconds=31)
        detections = [] # No detections

        counts = self.detector._update_tracks(detections, new_time)

        self.assertEqual(len(self.detector.active_tracks), 0)
        self.assertEqual(counts.get('Apple', 0), 0)

    def test_label_update_logic(self):
        """Test label update logic (e.g. unknown -> known)."""
        # Setup existing track as Unknown
        self.detector.active_tracks[1] = {
            'label': 'Unknown',
            'bbox': [100, 100, 200, 200],
            'last_seen': self.start_time
        }

        # New detection with specific label
        new_time = self.start_time + timedelta(seconds=1)
        detections = [
            {'label': 'Apple', 'confidence': 0.9, 'bbox': [100, 100, 200, 200]}
        ]

        counts = self.detector._update_tracks(detections, new_time)

        self.assertEqual(self.detector.active_tracks[1]['label'], 'Apple')
        self.assertEqual(counts['Apple'], 1)

    def test_label_persistence_when_new_is_unknown(self):
        """Test that known label persists if new detection is Unknown."""
        # Setup existing track as Apple
        self.detector.active_tracks[1] = {
            'label': 'Apple',
            'bbox': [100, 100, 200, 200],
            'last_seen': self.start_time
        }

        # New detection is Unknown (e.g. low confidence or occlusion)
        new_time = self.start_time + timedelta(seconds=1)
        detections = [
            {'label': 'Unknown', 'confidence': 0.5, 'bbox': [100, 100, 200, 200]}
        ]

        self.detector._update_tracks(detections, new_time)

        self.assertEqual(self.detector.active_tracks[1]['label'], 'Apple')

    def test_label_update_high_confidence(self):
        """Test that label updates if new detection has high confidence."""
        # Setup existing track as Apple
        self.detector.active_tracks[1] = {
            'label': 'Apple',
            'bbox': [100, 100, 200, 200],
            'last_seen': self.start_time
        }

        # New detection is Banana with high confidence
        new_time = self.start_time + timedelta(seconds=1)
        detections = [
            {'label': 'Banana', 'confidence': 0.85, 'bbox': [100, 100, 200, 200]}
        ]

        self.detector._update_tracks(detections, new_time)

        self.assertEqual(self.detector.active_tracks[1]['label'], 'Banana')

if __name__ == '__main__':
    unittest.main()
