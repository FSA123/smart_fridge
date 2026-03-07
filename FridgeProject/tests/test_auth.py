import sys
import os
import unittest

# Ensure we can import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.web import create_app
from src.database import init_db, db_session

class TestAuth(unittest.TestCase):
    def setUp(self):
        # Initialize DB (creates fridge.db in current directory if relative path)
        init_db()
        self.app = create_app()
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True
        # Ensure we use the default password 'admin' for tests
        os.environ['ADMIN_PASSWORD'] = 'admin'

    def tearDown(self):
        db_session.remove()

    def test_unauthenticated_api_access(self):
        """Test accessing /api/data without authentication."""
        response = self.client.get('/api/data')
        self.assertEqual(response.status_code, 401, "Expected 401 Unauthorized for unauthenticated API access.")
        print("\n[SUCCESS] /api/data blocked (401) without auth.")

    def test_unauthenticated_dashboard_access(self):
        """Test accessing / without authentication."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302, "Expected 302 Redirect for unauthenticated dashboard access.")
        self.assertIn('/login', response.headers['Location'], "Expected redirect to /login.")
        print("\n[SUCCESS] / blocked (302 -> /login) without auth.")

    def test_login_flow(self):
        """Test login and subsequent access."""
        # 1. Login with correct password
        response = self.client.post('/login', data={'password': 'admin'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200, "Login failed or redirect failed.")
        self.assertIn(b'Smart Fridge Monitor', response.data, "Did not land on dashboard after login.")
        print("\n[SUCCESS] Login successful.")

        # 2. Access API with session
        response = self.client.get('/api/data')
        self.assertEqual(response.status_code, 200, "Authenticated API access failed.")
        print("\n[SUCCESS] /api/data accessible (200) with auth.")

    def test_invalid_login(self):
        """Test login with incorrect password."""
        response = self.client.post('/login', data={'password': 'wrong'}, follow_redirects=True)
        self.assertIn(b'Invalid password', response.data, "Should show invalid password message.")
        print("\n[SUCCESS] Invalid login rejected.")

if __name__ == '__main__':
    unittest.main()
