import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock external dependencies that are not installed
sys.modules['flask'] = MagicMock()
sys.modules['sqlalchemy'] = MagicMock()
sys.modules['sqlalchemy.orm'] = MagicMock()
sys.modules['sqlalchemy.ext.declarative'] = MagicMock()

# Setup flask route decorator to return the function unmodified
def route_side_effect(*args, **kwargs):
    def decorator(f):
        return f
    return decorator

# Configure the mock flask instance
flask_mock = sys.modules['flask']
flask_mock.Blueprint.return_value.route.side_effect = route_side_effect

# Configure sqlalchemy mocks to prevent errors on import
sqlalchemy_mock = sys.modules['sqlalchemy']
sqlalchemy_orm_mock = sys.modules['sqlalchemy.orm']

# Import the module under test
# We wrap this in a try-except to catch import errors
try:
    from src.web import routes
except ImportError as e:
    print(f"ImportError during setup: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error during setup: {e}")
    sys.exit(1)

class TestUploadSecurity(unittest.TestCase):
    def setUp(self):
        # Reset mocks
        flask_mock.request.reset_mock()
        flask_mock.abort.reset_mock()

        # Default request data (simulate image upload)
        flask_mock.request.data = b'fake_image_data'

        # Mock file operations to prevent file system changes
        self.open_patcher = patch('builtins.open', new_callable=MagicMock)
        self.mock_open = self.open_patcher.start()

        self.makedirs_patcher = patch('os.makedirs')
        self.mock_makedirs = self.makedirs_patcher.start()

        # Also mock os.path.exists
        self.exists_patcher = patch('os.path.exists')
        self.mock_exists = self.exists_patcher.start()
        self.mock_exists.return_value = True

        # Ensure env is clean for each test
        self.env_patcher = patch.dict(os.environ, {}, clear=True)
        self.env_patcher.start()

    def tearDown(self):
        self.open_patcher.stop()
        self.makedirs_patcher.stop()
        self.exists_patcher.stop()
        self.env_patcher.stop()

    def test_missing_server_config(self):
        """Test that upload fails safely (500) if FRIDGE_API_KEY is not set on server."""
        print("\nTesting missing FRIDGE_API_KEY configuration...")
        # Ensure FRIDGE_API_KEY is not in env
        if 'FRIDGE_API_KEY' in os.environ:
            del os.environ['FRIDGE_API_KEY']

        # Call upload
        response = routes.upload()

        # Check response
        print(f"Response: {response}")
        self.assertEqual(response, ("Server misconfiguration", 500))

    def test_missing_request_key(self):
        """Test that upload fails (401) if X-API-Key header is missing."""
        print("\nTesting missing X-API-Key header...")
        os.environ['FRIDGE_API_KEY'] = 'secret_key'
        flask_mock.request.headers = {}

        response = routes.upload()

        print(f"Response: {response}")
        self.assertEqual(response, ("Unauthorized", 401))

    def test_incorrect_request_key(self):
        """Test that upload fails (401) if X-API-Key is incorrect."""
        print("\nTesting incorrect X-API-Key...")
        os.environ['FRIDGE_API_KEY'] = 'secret_key'
        flask_mock.request.headers = {'X-API-Key': 'wrong_key'}

        response = routes.upload()

        print(f"Response: {response}")
        self.assertEqual(response, ("Unauthorized", 401))

    def test_successful_upload(self):
        """Test that upload succeeds (200) with correct API key."""
        print("\nTesting successful upload...")
        os.environ['FRIDGE_API_KEY'] = 'secret_key'
        flask_mock.request.headers = {'X-API-Key': 'secret_key'}

        response = routes.upload()

        print(f"Response: {response}")
        self.assertEqual(response, ("SUCCESS", 200))
        # Verify file write occurred
        self.mock_open.assert_called()

if __name__ == '__main__':
    unittest.main()
