import unittest
import sys
import os
from unittest.mock import patch

# Add the project root to the path so we can import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils import get_missing_items

class MockItem:
    def __init__(self, label):
        self.label = label

class TestGetMissingItems(unittest.TestCase):

    def setUp(self):
        # Patch BASIC_ITEMS for all tests in this class to ensure test stability
        self.patcher = patch('src.utils.BASIC_ITEMS', ['apple', 'banana', 'milk'])
        self.mock_basic_items = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_empty_inventory(self):
        """Test that an empty inventory returns all basic items."""
        missing = get_missing_items([])
        self.assertEqual(set(missing), set(self.mock_basic_items))

    def test_full_inventory(self):
        """Test that a full inventory returns no missing items."""
        items = [MockItem(label) for label in self.mock_basic_items]
        missing = get_missing_items(items)
        self.assertEqual(missing, [])

    def test_partial_inventory(self):
        """Test that a partial inventory returns only the missing items."""
        # Create inventory with first item
        present_labels = [self.mock_basic_items[0]]
        items = [MockItem(label) for label in present_labels]

        expected_missing = self.mock_basic_items[1:]
        missing = get_missing_items(items)

        self.assertEqual(set(missing), set(expected_missing))

    def test_case_sensitivity(self):
        """Test that item labels are case-insensitive."""
        # 'Apple' should match 'apple' in mock list
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
