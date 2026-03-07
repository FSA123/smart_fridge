import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestFoodDetectorProcessFolder(unittest.TestCase):
    def setUp(self):
        self.modules_patcher = patch.dict(sys.modules, {
            'src.product_recognizer': MagicMock(),
            'src.database': MagicMock(),
            'src.models': MagicMock(),
        })
        self.modules_patcher.start()

        sys.modules.pop('src.detector', None)

        from src.detector import FoodDetector
        with patch('src.detector.ProductRecognizer'):
            self.detector = FoodDetector(image_folder="mock_images", model_path="mock_model.pt")
        self.detector.processed_images = set()

    def tearDown(self):
        self.modules_patcher.stop()
        sys.modules.pop('src.detector', None)

    @patch('src.detector.os.listdir')
    @patch('src.detector.os.path.exists')
    @patch('src.detector.os.makedirs')
    def test_process_folder_sorts_correctly(self, mock_makedirs, mock_exists, mock_listdir):
        mock_exists.return_value = True
        mock_listdir.return_value = ["capture_3.jpg", "capture_1.jpg", ".DS_Store", "capture_4.jpg", "capture_2.jpg"]

        self.detector.processed_images = {"capture_1.jpg", "capture_3.jpg"}
        self.detector.analyze_image = MagicMock()

        self.detector.process_folder()

        self.assertEqual(self.detector.analyze_image.call_count, 2)

        calls = self.detector.analyze_image.call_args_list
        args1, _ = calls[0]
        self.assertTrue(args1[0].endswith("capture_2.jpg"), f"Expected capture_2.jpg, got {args1[0]}")

        args2, _ = calls[1]
        self.assertTrue(args2[0].endswith("capture_4.jpg"), f"Expected capture_4.jpg, got {args2[0]}")

        self.assertIn("capture_2.jpg", self.detector.processed_images)
        self.assertIn("capture_4.jpg", self.detector.processed_images)

    @patch('src.detector.os.listdir')
    @patch('src.detector.os.path.exists')
    @patch('src.detector.os.makedirs')
    def test_memory_leak_fix_intersection_update(self, mock_makedirs, mock_exists, mock_listdir):
        """Test that processed_images shrinks when files are deleted."""
        mock_exists.return_value = True

        self.detector.processed_images = {"capture_old.jpg", "capture_1.jpg"}
        mock_listdir.return_value = ["capture_1.jpg", "capture_2.jpg"]
        self.detector.analyze_image = MagicMock()

        self.detector.process_folder()

        self.assertNotIn("capture_old.jpg", self.detector.processed_images)
        self.assertIn("capture_1.jpg", self.detector.processed_images)
        self.assertIn("capture_2.jpg", self.detector.processed_images)

if __name__ == '__main__':
    unittest.main()
