import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.web import create_app
from src.database import init_db, db_session

class TestUploadSecurity(unittest.TestCase):
    def setUp(self):
        init_db()
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        # Ensure FRIDGE_API_KEY is clean for each test
        if 'FRIDGE_API_KEY' in os.environ:
            del os.environ['FRIDGE_API_KEY']

    def tearDown(self):
        db_session.remove()
        if 'FRIDGE_API_KEY' in os.environ:
            del os.environ['FRIDGE_API_KEY']

    def test_missing_server_config(self):
        """Test that upload fails safely (500) if FRIDGE_API_KEY is not set on server."""
        response = self.client.post('/upload', data=b'fake_image_data',
                                    content_type='image/jpeg')
        self.assertEqual(response.status_code, 500)
        print("\n[SUCCESS] Upload blocked (500) when FRIDGE_API_KEY is not set.")

    def test_missing_request_key(self):
        """Test that upload fails (401) if X-API-Key header is missing."""
        os.environ['FRIDGE_API_KEY'] = 'secret_key'
        response = self.client.post('/upload', data=b'fake_image_data',
                                    content_type='image/jpeg')
        self.assertEqual(response.status_code, 401)
        print("\n[SUCCESS] Upload blocked (401) when X-API-Key is missing.")

    def test_incorrect_request_key(self):
        """Test that upload fails (401) if X-API-Key is incorrect."""
        os.environ['FRIDGE_API_KEY'] = 'secret_key'
        response = self.client.post('/upload', data=b'fake_image_data',
                                    content_type='image/jpeg',
                                    headers={'X-API-Key': 'wrong_key'})
        self.assertEqual(response.status_code, 401)
        print("\n[SUCCESS] Upload blocked (401) when X-API-Key is wrong.")

    def test_invalid_image_data(self):
        """Test that upload fails (400) if data is not a valid JPEG."""
        os.environ['FRIDGE_API_KEY'] = 'secret_key'
        response = self.client.post('/upload', data=b'not_an_image',
                                    content_type='image/jpeg',
                                    headers={'X-API-Key': 'secret_key'})
        self.assertEqual(response.status_code, 400)
        print("\n[SUCCESS] Upload blocked (400) for invalid image data.")

if __name__ == '__main__':
    unittest.main()
