import unittest
import sys
import os
from unittest.mock import patch
from datetime import datetime, timedelta

# Add the project root to the path so we can import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models import Item
from src.utils import get_recommendations, get_missing_items, _calculate_recommendations


class MockItem:
    def __init__(self, label):
        self.label = label


# =============================================================================
# Tests for get_recommendations (from PR #12)
# =============================================================================

class TestGetRecommendations(unittest.TestCase):

    def setUp(self):
        # Clear LRU cache before each test to avoid stale results
        _calculate_recommendations.cache_clear()

    @patch('src.utils.datetime')
    def test_basic_recommendations(self, mock_datetime):
        fixed_now = datetime(2023, 10, 27, 12, 0, 0)
        mock_datetime.utcnow.return_value = fixed_now

        # Milk: shelf life 7 days, entered 2 days ago -> 5 remaining -> Good
        # Eggs: shelf life 21 days, entered 20 days ago -> 1 remaining -> Critical
        items = [
            Item(id=1, label='Milk', entry_date=fixed_now - timedelta(days=2), image_path='img1.jpg'),
            Item(id=2, label='Eggs', entry_date=fixed_now - timedelta(days=20), image_path='img2.jpg')
        ]

        recommendations = get_recommendations(items)

        self.assertEqual(len(recommendations), 2)
        self.assertEqual(recommendations[0]['label'], 'Eggs')
        self.assertEqual(recommendations[0]['days_remaining'], 1)
        self.assertEqual(recommendations[0]['status'], 'Critical')
        self.assertEqual(recommendations[1]['label'], 'Milk')
        self.assertEqual(recommendations[1]['days_remaining'], 5)
        self.assertEqual(recommendations[1]['status'], 'Good')

    @patch('src.utils.datetime')
    def test_unknown_item_default(self, mock_datetime):
        fixed_now = datetime(2023, 10, 27, 12, 0, 0)
        mock_datetime.utcnow.return_value = fixed_now

        items = [
            Item(id=3, label='UnknownFood', entry_date=fixed_now - timedelta(days=1), image_path='img3.jpg')
        ]

        recommendations = get_recommendations(items)

        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0]['label'], 'UnknownFood')
        self.assertEqual(recommendations[0]['days_remaining'], 6)

    @patch('src.utils.datetime')
    def test_case_insensitivity(self, mock_datetime):
        fixed_now = datetime(2023, 10, 27, 12, 0, 0)
        mock_datetime.utcnow.return_value = fixed_now

        items = [
            Item(id=4, label='Milk', entry_date=fixed_now, image_path='img4.jpg')
        ]

        recommendations = get_recommendations(items)

        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0]['days_remaining'], 7)

    @patch('src.utils.datetime')
    def test_sorting_order(self, mock_datetime):
        fixed_now = datetime(2023, 10, 27, 12, 0, 0)
        mock_datetime.utcnow.return_value = fixed_now

        items = [
            Item(id=5, label='Butter', entry_date=fixed_now - timedelta(days=10), image_path='img5.jpg'),
            Item(id=6, label='Bread', entry_date=fixed_now - timedelta(days=4), image_path='img6.jpg'),
            Item(id=7, label='Apple', entry_date=fixed_now - timedelta(days=13), image_path='img7.jpg')
        ]

        recommendations = get_recommendations(items)

        self.assertEqual(len(recommendations), 3)
        self.assertEqual(recommendations[0]['label'], 'Bread')
        self.assertEqual(recommendations[1]['label'], 'Apple')
        self.assertEqual(recommendations[2]['label'], 'Butter')
        self.assertTrue(recommendations[0]['days_remaining'] <= recommendations[1]['days_remaining'])
        self.assertTrue(recommendations[1]['days_remaining'] <= recommendations[2]['days_remaining'])

    @patch('src.utils.datetime')
    def test_empty_list(self, mock_datetime):
        fixed_now = datetime(2023, 10, 27, 12, 0, 0)
        mock_datetime.utcnow.return_value = fixed_now

        recommendations = get_recommendations([])
        self.assertEqual(recommendations, [])

    @patch('src.utils.datetime')
    def test_critical_status_boundary(self, mock_datetime):
        fixed_now = datetime(2023, 10, 27, 12, 0, 0)
        mock_datetime.utcnow.return_value = fixed_now

        items = [
            Item(id=8, label='Milk', entry_date=fixed_now - timedelta(days=6), image_path='img8.jpg'),
            Item(id=9, label='Milk', entry_date=fixed_now - timedelta(days=5), image_path='img9.jpg')
        ]

        recommendations = get_recommendations(items)

        self.assertEqual(recommendations[0]['days_remaining'], 1)
        self.assertEqual(recommendations[0]['status'], 'Critical')
        self.assertEqual(recommendations[1]['days_remaining'], 2)
        self.assertEqual(recommendations[1]['status'], 'Good')


# =============================================================================
# Tests for get_missing_items (from PR #31)
# =============================================================================

class TestGetMissingItems(unittest.TestCase):

    def setUp(self):
        self.patcher = patch('src.utils.BASIC_ITEMS', ['apple', 'banana', 'milk'])
        self.mock_basic_items = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_empty_inventory(self):
        """Test that an empty inventory returns all basic items."""
        missing = get_missing_items([])
        self.assertEqual(set(missing), {'apple', 'banana', 'milk'})

    def test_full_inventory(self):
        """Test that a full inventory returns no missing items."""
        items = [MockItem('apple'), MockItem('banana'), MockItem('milk')]
        missing = get_missing_items(items)
        self.assertEqual(missing, [])

    def test_partial_inventory(self):
        """Test that a partial inventory returns only the missing items."""
        items = [MockItem('apple')]
        missing = get_missing_items(items)
        self.assertEqual(set(missing), {'banana', 'milk'})

    def test_case_sensitivity(self):
        """Test that item labels are case-insensitive."""
        items = [MockItem('Apple'), MockItem('BANANA')]
        missing = get_missing_items(items)
        self.assertNotIn('apple', missing)
        self.assertNotIn('banana', missing)
        self.assertIn('milk', missing)

    def test_extra_items(self):
        """Test that extra items not in BASIC_ITEMS are ignored."""
        items = [MockItem('dragonfruit'), MockItem('apple')]
        missing = get_missing_items(items)
        self.assertNotIn('apple', missing)
        self.assertIn('banana', missing)

    def test_duplicates(self):
        """Test that duplicate items in inventory don't cause issues."""
        items = [MockItem('apple'), MockItem('apple')]
        missing = get_missing_items(items)
        self.assertNotIn('apple', missing)


if __name__ == '__main__':
    unittest.main()
