import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import sys
import os

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.web import create_app
from src.models import Item

class TestWebRoutes(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    @patch('src.models.Item.query')
    def test_api_data(self, mock_query):
        # Create dummy items
        item1 = Item(id=1, label='apple', entry_date=datetime.utcnow(), status='active')
        item2 = Item(id=2, label='milk', entry_date=datetime.utcnow() - timedelta(days=2), status='active')

        # Configure mock
        mock_filter_by = mock_query.filter_by.return_value
        mock_filter_by.all.return_value = [item1, item2]

        # Make request
        response = self.client.get('/api/data')

        # Check status code
        self.assertEqual(response.status_code, 200)

        # Check JSON response
        data = response.get_json()
        self.assertIn('inventory', data)
        self.assertIn('missing', data)
        self.assertIn('count', data)

        self.assertEqual(data['count'], 2)
        self.assertEqual(len(data['inventory']), 2)

        # Check inventory structure
        inventory_item = data['inventory'][0]
        self.assertIn('id', inventory_item)
        self.assertIn('label', inventory_item)
        self.assertIn('days_in_fridge', inventory_item)
        self.assertIn('days_remaining', inventory_item)
        self.assertIn('status', inventory_item)

        # Check missing items
        self.assertIsInstance(data['missing'], list)

if __name__ == '__main__':
    unittest.main()
