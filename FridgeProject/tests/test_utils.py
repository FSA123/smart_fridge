import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
from src.models import Item
from src.utils import get_recommendations

class TestGetRecommendations(unittest.TestCase):

    @patch('src.utils.datetime')
    def test_basic_recommendations(self, mock_datetime):
        # Set a fixed "now" time
        fixed_now = datetime(2023, 10, 27, 12, 0, 0)
        mock_datetime.utcnow.return_value = fixed_now

        # Milk: shelf life 7 days. Entered 2 days ago. Remaining: 5. Status: Good.
        # Eggs: shelf life 21 days. Entered 20 days ago. Remaining: 1. Status: Critical.
        items = [
            Item(id=1, label='Milk', entry_date=fixed_now - timedelta(days=2), image_path='img1.jpg'),
            Item(id=2, label='Eggs', entry_date=fixed_now - timedelta(days=20), image_path='img2.jpg')
        ]

        recommendations = get_recommendations(items)

        # Verify number of recommendations
        self.assertEqual(len(recommendations), 2)

        # Verify content of first recommendation (Eggs should be first due to urgency)
        self.assertEqual(recommendations[0]['label'], 'Eggs')
        self.assertEqual(recommendations[0]['days_remaining'], 1)
        self.assertEqual(recommendations[0]['status'], 'Critical')

        # Verify content of second recommendation
        self.assertEqual(recommendations[1]['label'], 'Milk')
        self.assertEqual(recommendations[1]['days_remaining'], 5)
        self.assertEqual(recommendations[1]['status'], 'Good')

    @patch('src.utils.datetime')
    def test_unknown_item_default(self, mock_datetime):
        fixed_now = datetime(2023, 10, 27, 12, 0, 0)
        mock_datetime.utcnow.return_value = fixed_now

        # 'UnknownFood' not in SHELF_LIFE. Should default to 7 days.
        # Entered 1 day ago. Remaining: 6.
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

        # 'milk' is in SHELF_LIFE (7 days). Testing 'Milk' (mixed case).
        # Entered 0 days ago. Remaining: 7.
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

        # Create items with different urgencies
        # Bread (5 days shelf life): entered 4 days ago -> 1 day remaining
        # Butter (60 days shelf life): entered 10 days ago -> 50 days remaining
        # Apple (14 days shelf life): entered 13 days ago -> 1 day remaining

        items = [
            Item(id=5, label='Butter', entry_date=fixed_now - timedelta(days=10), image_path='img5.jpg'),
            Item(id=6, label='Bread', entry_date=fixed_now - timedelta(days=4), image_path='img6.jpg'),
            Item(id=7, label='Apple', entry_date=fixed_now - timedelta(days=13), image_path='img7.jpg')
        ]

        recommendations = get_recommendations(items)

        # Expected order: Bread (1), Apple (1), Butter (50)
        # Note: Order for same remaining days is stable (insertion order) or undefined depending on sort implementation.
        # Python's sort is stable.

        self.assertEqual(len(recommendations), 3)
        self.assertEqual(recommendations[0]['label'], 'Bread')
        self.assertEqual(recommendations[1]['label'], 'Apple')
        self.assertEqual(recommendations[2]['label'], 'Butter')

        # Verify sorting
        self.assertTrue(recommendations[0]['days_remaining'] <= recommendations[1]['days_remaining'])
        self.assertTrue(recommendations[1]['days_remaining'] <= recommendations[2]['days_remaining'])

    @patch('src.utils.datetime')
    def test_empty_list(self, mock_datetime):
        fixed_now = datetime(2023, 10, 27, 12, 0, 0)
        mock_datetime.utcnow.return_value = fixed_now

        items = []
        recommendations = get_recommendations(items)

        self.assertEqual(recommendations, [])

    @patch('src.utils.datetime')
    def test_critical_status_boundary(self, mock_datetime):
        fixed_now = datetime(2023, 10, 27, 12, 0, 0)
        mock_datetime.utcnow.return_value = fixed_now

        # Boundary is < 2 days remaining -> Critical.
        # Milk (7 days shelf life).
        # 1 day remaining: 7 - 6 = 1 -> Critical
        # 2 days remaining: 7 - 5 = 2 -> Good

        items = [
            Item(id=8, label='Milk', entry_date=fixed_now - timedelta(days=6), image_path='img8.jpg'), # 1 day left
            Item(id=9, label='Milk', entry_date=fixed_now - timedelta(days=5), image_path='img9.jpg')  # 2 days left
        ]

        recommendations = get_recommendations(items)

        # Sorted by urgency, so 1 day left comes first
        self.assertEqual(recommendations[0]['days_remaining'], 1)
        self.assertEqual(recommendations[0]['status'], 'Critical')

        self.assertEqual(recommendations[1]['days_remaining'], 2)
        self.assertEqual(recommendations[1]['status'], 'Good')

if __name__ == '__main__':
    unittest.main()
