import unittest
import os
import shutil
import tempfile
from unittest.mock import patch

# Adjust path to import src
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.web import create_app

class TestRoutes(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for images
        self.test_dir = tempfile.mkdtemp()

        # Patch the SAVE_PATH in src.web.routes to point to our temp dir
        self.patcher = patch('src.web.routes.SAVE_PATH', self.test_dir)
        self.patcher.start()

        # Create the app and test client
        self.app = create_app()
        self.client = self.app.test_client()
        self.app.testing = True

    def tearDown(self):
        # Stop the patcher
        self.patcher.stop()
        # Remove the temporary directory
        shutil.rmtree(self.test_dir)

        # Clean up fridge.db if it was created in the current directory
        if os.path.exists('fridge.db'):
            try:
                os.remove('fridge.db')
            except OSError:
                pass

    def test_upload_success(self):
        # Simulate binary image data (minimal valid JPEG header)
        img_data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb'

        response = self.client.post('/upload', data=img_data)

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b'SUCCESS')

        # Verify file creation
        files = os.listdir(self.test_dir)
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].startswith('capture_'))
        self.assertTrue(files[0].endswith('.jpg'))

        # Verify file content
        with open(os.path.join(self.test_dir, files[0]), 'rb') as f:
            content = f.read()
        self.assertEqual(content, img_data)

    def test_upload_failure(self):
        # Send empty request
        response = self.client.post('/upload', data=None)

        # Check response
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, b'FAILED')

        # Verify no file was created
        files = os.listdir(self.test_dir)
        self.assertEqual(len(files), 0)

if __name__ == '__main__':
    unittest.main()
