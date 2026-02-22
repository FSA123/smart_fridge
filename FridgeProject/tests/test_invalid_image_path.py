import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import importlib

class TestInvalidImagePath(unittest.TestCase):
    def setUp(self):
        """
        Setup mocks for dependencies before importing the module under test.
        This ensures that we can run the test even if the environment lacks these packages.
        """
        # Create mocks for all external dependencies
        self.mock_cv2 = MagicMock()
        self.mock_torch = MagicMock()
        self.mock_clip = MagicMock()
        self.mock_easyocr = MagicMock()
        self.mock_ultralytics = MagicMock()
        self.mock_pil = MagicMock()
        self.mock_numpy = MagicMock()

        # Patch sys.modules to inject our mocks
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

        # Add project root to sys.path so we can import src
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        if project_root not in sys.path:
            sys.path.append(project_root)

        # Import or reload the module under test to ensure it uses the mocked modules
        # If src.product_recognizer was already imported, we must reload it
        # because it might have cached the original (or missing) modules.
        try:
            import src.product_recognizer
            importlib.reload(src.product_recognizer)
            self.product_recognizer_module = src.product_recognizer
        except ImportError as e:
            self.fail(f"Failed to import src.product_recognizer even with mocks: {e}")

    def tearDown(self):
        """
        Clean up patches and remove the module from sys.modules to avoid side effects on other tests.
        """
        self.modules_patcher.stop()

        # Remove the module from sys.modules so subsequent tests re-import it cleanly
        if 'src.product_recognizer' in sys.modules:
            del sys.modules['src.product_recognizer']

    def test_detect_objects_invalid_path(self):
        """
        Test that detect_objects returns an empty list when the image path is invalid.
        """
        ProductRecognizer = self.product_recognizer_module.ProductRecognizer

        # Mock __init__ to avoid any heavy initialization logic during instantiation
        with patch.object(ProductRecognizer, '__init__', return_value=None):
            recognizer = ProductRecognizer()

            # Configure cv2.imread (via our mock) to return None, simulating an invalid path
            self.mock_cv2.imread.return_value = None

            # Define an invalid path
            image_path = "non_existent_image.jpg"

            # Call the method
            detections = recognizer.detect_objects(image_path)

            # Assertions
            self.assertEqual(detections, [], "Should return an empty list for an invalid image path.")

            # Verify cv2.imread was called correctly
            self.mock_cv2.imread.assert_called_with(image_path)

if __name__ == "__main__":
    unittest.main()
