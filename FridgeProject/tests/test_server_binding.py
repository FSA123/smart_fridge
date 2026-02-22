import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the FridgeProject directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

# Mock dependencies BEFORE importing main
# This avoids ImportError due to missing packages like sqlalchemy, ultralytics, etc.
# and avoids side effects from importing real modules.
sys.modules['src'] = MagicMock()
sys.modules['src.database'] = MagicMock()
sys.modules['src.detector'] = MagicMock()
sys.modules['src.web'] = MagicMock()

# Now import main
import main

class TestServerBinding(unittest.TestCase):
    def setUp(self):
        # Clean up env var before each test
        if 'FLASK_HOST' in os.environ:
            del os.environ['FLASK_HOST']

    def tearDown(self):
        # Clean up env var after each test
        if 'FLASK_HOST' in os.environ:
            del os.environ['FLASK_HOST']

    @patch('main.create_app')
    @patch('main.FoodDetector')
    @patch('main.init_db')
    def test_default_host(self, mock_init_db, mock_detector_cls, mock_create_app):
        # Setup mocks
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app
        mock_detector = MagicMock()
        mock_detector_cls.return_value = mock_detector

        # Run main
        main.main()

        # Check that app.run was called with default host
        mock_app.run.assert_called_once()
        args, kwargs = mock_app.run.call_args
        self.assertEqual(kwargs.get('host'), '127.0.0.1')
        self.assertEqual(kwargs.get('port'), 5001)

    @patch('main.create_app')
    @patch('main.FoodDetector')
    @patch('main.init_db')
    def test_custom_host(self, mock_init_db, mock_detector_cls, mock_create_app):
        # Setup mocks
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app
        mock_detector = MagicMock()
        mock_detector_cls.return_value = mock_detector

        # Set env var
        os.environ['FLASK_HOST'] = '0.0.0.0'

        # Run main
        main.main()

        # Check that app.run was called with custom host
        mock_app.run.assert_called_once()
        args, kwargs = mock_app.run.call_args
        self.assertEqual(kwargs.get('host'), '0.0.0.0')
        self.assertEqual(kwargs.get('port'), 5001)

if __name__ == '__main__':
    unittest.main()
