import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock dependencies before import
sys.modules['src.product_recognizer'] = MagicMock()
sys.modules['src.database'] = MagicMock()
sys.modules['src.models'] = MagicMock()

# Now import detector
from src.detector import FoodDetector

class TestFoodDetectorProcessFolder(unittest.TestCase):
    def setUp(self):
        # Setup detector instance
        # Mock ProductRecognizer inside FoodDetector.__init__
        with patch('src.detector.ProductRecognizer'):
            self.detector = FoodDetector(image_folder="mock_images", model_path="mock_model.pt")

        self.detector.processed_images = set()

    @patch('src.detector.os.listdir')
    @patch('src.detector.os.path.exists')
    @patch('src.detector.os.makedirs')
    def test_process_folder_sorts_correctly(self, mock_makedirs, mock_exists, mock_listdir):
        mock_exists.return_value = True

        # Scenario:
        # - existing files: capture_1.jpg, capture_3.jpg (already processed)
        # - new files: capture_2.jpg, capture_4.jpg
        # - unrelated files: .DS_Store

        # os.listdir returns unordered
        mock_listdir.return_value = ["capture_3.jpg", "capture_1.jpg", ".DS_Store", "capture_4.jpg", "capture_2.jpg"]

        self.detector.processed_images = {"capture_1.jpg", "capture_3.jpg"}

        # Mock analyze_image to verify call order
        self.detector.analyze_image = MagicMock()

        self.detector.process_folder()

        # Check that analyze_image was called for capture_2.jpg then capture_4.jpg
        self.assertEqual(self.detector.analyze_image.call_count, 2)

        calls = self.detector.analyze_image.call_args_list
        # Check first call is for capture_2.jpg
        args1, _ = calls[0]
        self.assertTrue(args1[0].endswith("capture_2.jpg"), f"Expected capture_2.jpg, got {args1[0]}")

        # Check second call is for capture_4.jpg
        args2, _ = calls[1]
        self.assertTrue(args2[0].endswith("capture_4.jpg"), f"Expected capture_4.jpg, got {args2[0]}")

        # Verify processed_images updated
        self.assertIn("capture_2.jpg", self.detector.processed_images)
        self.assertIn("capture_4.jpg", self.detector.processed_images)

if __name__ == '__main__':
    unittest.main()
