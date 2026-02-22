import unittest
import sys
from unittest.mock import MagicMock, patch
from datetime import datetime

class TestDetectorTimestamp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create mocks for dependencies
        cls.mock_pr = MagicMock()
        cls.mock_db = MagicMock()
        cls.mock_models = MagicMock()

        # Patch sys.modules to inject mocks BEFORE importing src.detector
        cls.modules_patcher = patch.dict(sys.modules, {
            'src.product_recognizer': cls.mock_pr,
            'src.database': cls.mock_db,
            'src.models': cls.mock_models
        })
        cls.modules_patcher.start()

        # Import the module under test *after* patching
        try:
            import src.detector
            cls.detector_module = src.detector
            cls.FoodDetector = src.detector.FoodDetector
        except ImportError as e:
            # If import fails, we should know why (e.g. unexpected dependency)
            raise e

    @classmethod
    def tearDownClass(cls):
        # Stop patching sys.modules
        cls.modules_patcher.stop()

        # Clean up imported modules from sys.modules to prevent pollution
        # We remove 'src.detector' so subsequent tests don't get our mocked version
        if 'src.detector' in sys.modules:
            del sys.modules['src.detector']

    def setUp(self):
        # Setup specific mock behavior for each test
        # FoodDetector init calls ProductRecognizer()
        self.mock_recognizer_class = self.mock_pr.ProductRecognizer
        self.mock_recognizer_instance = self.mock_recognizer_class.return_value

    def test_valid_timestamp(self):
        """Test with a valid filename format: capture_YYYYMMDD_HHMMSS.jpg"""
        detector = self.FoodDetector(model_path="dummy.pt")

        filename = "capture_20231027_103000.jpg"
        expected = datetime(2023, 10, 27, 10, 30, 0)
        result = detector.get_timestamp_from_filename(filename)

        self.assertEqual(result, expected)

    def test_invalid_format(self):
        """Test with a filename that doesn't match the expected format."""
        detector = self.FoodDetector(model_path="dummy.pt")

        fixed_now = datetime(2024, 1, 1, 12, 0, 0)

        # Mock datetime in src.detector to control utcnow()
        with patch('src.detector.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = fixed_now
            # We must forward strptime to the real implementation because existing code calls it
            mock_datetime.strptime.side_effect = datetime.strptime

            filename = "image.jpg"
            result = detector.get_timestamp_from_filename(filename)

            self.assertEqual(result, fixed_now)

    def test_invalid_date(self):
        """Test with a filename containing an invalid date."""
        detector = self.FoodDetector(model_path="dummy.pt")

        fixed_now = datetime(2024, 1, 1, 12, 0, 0)

        with patch('src.detector.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = fixed_now
            mock_datetime.strptime.side_effect = datetime.strptime

            filename = "capture_20231301_000000.jpg"
            result = detector.get_timestamp_from_filename(filename)

            self.assertEqual(result, fixed_now)

    def test_empty_filename(self):
        """Test with an empty filename."""
        detector = self.FoodDetector(model_path="dummy.pt")

        fixed_now = datetime(2024, 1, 1, 12, 0, 0)

        with patch('src.detector.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = fixed_now
            mock_datetime.strptime.side_effect = datetime.strptime

            filename = ""
            result = detector.get_timestamp_from_filename(filename)

            self.assertEqual(result, fixed_now)

if __name__ == '__main__':
    unittest.main()
