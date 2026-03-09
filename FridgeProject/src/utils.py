from datetime import datetime
from functools import lru_cache
from collections import namedtuple
import time
from src.models import Item, ProductType

# Basic items list to check against (also seeded into ProductType table by database.py)
BASIC_ITEMS = [
    'apple', 'banana', 'milk', 'eggs', 'cheese',
    'bread', 'butter', 'carrot', 'tomato', 'potato'
]

# Estimated shelf life in days (also seeded into ProductType table by database.py)
SHELF_LIFE = {
    'milk': 7,
    'eggs': 21,
    'bread': 5,
    'apple': 14,
    'banana': 5,
    'cheese': 30,
    'butter': 60,
    'vegetables': 7,
    'fruit': 7
}

ItemData = namedtuple('ItemData', ['id', 'label', 'entry_date', 'image_path'])

@lru_cache(maxsize=128)
def _calculate_recommendations(items_tuple, time_bucket):
    """
    Cached worker function for recommendations.
    Accepts a tuple of ItemData and an hourly time bucket for cache expiry.
    """
    scored_items = []
    now = datetime.utcnow()

    for item in items_tuple:
        days_in_fridge = (now - item.entry_date).days
        # Default to 7 days if unknown
        shelf_life = SHELF_LIFE.get(item.label.lower(), 7)
        days_remaining = shelf_life - days_in_fridge

        scored_items.append({
            'id': item.id,
            'label': item.label,
            'image_path': item.image_path,
            'days_in_fridge': days_in_fridge,
            'days_remaining': days_remaining,
            'status': 'Critical' if days_remaining < 2 else 'Good'
        })

    # Sort by days remaining (ascending)
    scored_items.sort(key=lambda x: x['days_remaining'])

    return scored_items

def get_recommendations(items):
    """
    Returns a list of items sorted by urgency to consume.
    Urgency is calculated based on time in fridge vs shelf life.
    Returns a list of dictionaries with item details and status.
    """
    if not items:
        return []

    # Convert list of Item objects to tuple of ItemData for caching
    items_tuple = tuple(ItemData(i.id, i.label, i.entry_date, i.image_path) for i in items)

    # Time bucket: every hour (3600 seconds) to allow cache expiry/update
    time_bucket = int(time.time() // 3600)

    return _calculate_recommendations(items_tuple, time_bucket)

def get_missing_items(current_items):
    """
    Returns a list of basic items that are missing from the current inventory.
    """
    current_labels = {item.label.lower() for item in current_items}
    missing = [item for item in BASIC_ITEMS if item not in current_labels]
    return missing
