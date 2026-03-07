import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import importlib

class TestInvalidImagePath(unittest.TestCase):
    def setUp(self):
        self.mock_cv2 = MagicMock()
        self.mock_torch = MagicMock()
        self.mock_clip = MagicMock()
        self.mock_easyocr = MagicMock()
        self.mock_ultralytics = MagicMock()
        self.mock_pil = MagicMock()
        self.mock_numpy = MagicMock()

        self.modules_patcher = patch.dict(sys.modules, {
            'cv2': self.mock_cv2,
            'torch': self.mock_torch,
            'clip': self.mock_clip,
            'easyocr': self.mock_easyocr,
            'ultralytics': self.mock_ultralytics,
            'PIL': self.mock_pil,
            'numpy': self.mock_numpy
        })
        self.modules_patcher.start()

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        if project_root not in sys.path:
            sys.path.append(project_root)

        try:
            import src.product_recognizer
            importlib.reload(src.product_recognizer)
            self.product_recognizer_module = src.product_recognizer
        except ImportError as e:
            self.fail(f"Failed to import src.product_recognizer even with mocks: {e}")

    def tearDown(self):
        self.modules_patcher.stop()
        if 'src.product_recognizer' in sys.modules:
            del sys.modules['src.product_recognizer']

    def test_detect_objects_invalid_path(self):
        """Test that detect_objects returns an empty list for an invalid image path."""
        ProductRecognizer = self.product_recognizer_module.ProductRecognizer

        with patch.object(ProductRecognizer, '__init__', return_value=None):
            recognizer = ProductRecognizer()
            self.mock_cv2.imread.return_value = None

            image_path = "non_existent_image.jpg"
            detections = recognizer.detect_objects(image_path)

            self.assertEqual(detections, [], "Should return an empty list for an invalid image path.")
            self.mock_cv2.imread.assert_called_with(image_path)

if __name__ == "__main__":
    unittest.main()
