import unittest
from unittest.mock import MagicMock, patch
import sys
from datetime import datetime, timedelta

class TestCleanupItems(unittest.TestCase):
    def setUp(self):
        # Mock heavy dependencies BEFORE importing src.detector
        # Use patch.dict on sys.modules to avoid side effects on other tests
        self.modules_patcher = patch.dict('sys.modules', {
            'src.product_recognizer': MagicMock(),
            'cv2': MagicMock(),
            'ultralytics': MagicMock(),
            'easyocr': MagicMock(),
            'google.generativeai': MagicMock(),
            'clip': MagicMock()
        })
        self.modules_patcher.start()

        # Import modules inside setUp to ensure they use the mocked dependencies
        # and to avoid top-level import errors if dependencies are missing.
        # Note: We use local imports here.
        try:
            from src.detector import FoodDetector
            from src.models import Item
            from src.database import db_session
        except ImportError as e:
            self.fail(f"Failed to import modules: {e}")

        self.FoodDetector = FoodDetector
        self.Item = Item
        self.db_session = db_session

        # Setup mocks for db_session and Item inside detector
        # We need to patch where they are used, which is src.detector
        self.db_session_patcher = patch('src.detector.db_session')
        self.mock_db_session = self.db_session_patcher.start()

        self.item_patcher = patch('src.detector.Item')
        self.mock_Item = self.item_patcher.start()

        # Configure Item attributes to support comparison operations used in filter()
        # Item.last_confirmed < limit
        column_mock = MagicMock()
        column_mock.__lt__.return_value = MagicMock() # Return a mock expression
        self.mock_Item.last_confirmed = column_mock

        # Set up mock query
        self.mock_item_query = self.mock_Item.query

    def tearDown(self):
        self.db_session_patcher.stop()
        self.item_patcher.stop()
        self.modules_patcher.stop()

    def test_cleanup_removes_expired_items(self):
        """Verify that items older than grace_period are marked as 'history' and committed."""
        # Arrange
        current_time = datetime.utcnow()
        grace_period = 300
        detector = self.FoodDetector(grace_period=grace_period)

        # Create dummy expired items
        expired_item1 = MagicMock()
        expired_item1.status = 'active'
        expired_item1.label = 'ExpiredItem1'
        expired_item1.id = 1

        expired_item2 = MagicMock()
        expired_item2.status = 'active'
        expired_item2.label = 'ExpiredItem2'
        expired_item2.id = 2

        # Mock query return
        self.mock_item_query.filter.return_value.all.return_value = [expired_item1, expired_item2]

        # Act
        detector.cleanup_items(current_time)

        # Assert
        self.mock_item_query.filter.assert_called()
        self.mock_item_query.filter.return_value.all.assert_called_once()

        self.assertEqual(expired_item1.status, 'history')
        self.assertEqual(expired_item2.status, 'history')

        self.mock_db_session.commit.assert_called_once()

    def test_cleanup_keeps_active_items(self):
        """Verify that if no items are expired, no changes are committed."""
        # Arrange
        current_time = datetime.utcnow()
        grace_period = 300
        detector = self.FoodDetector(grace_period=grace_period)

        # Mock query return: empty list
        self.mock_item_query.filter.return_value.all.return_value = []

        # Act
        detector.cleanup_items(current_time)

        # Assert
        self.mock_item_query.filter.assert_called()
        self.mock_item_query.filter.return_value.all.assert_called_once()

        self.mock_db_session.commit.assert_not_called()
