from datetime import datetime
from src.models import Item, ProductType

def get_recommendations(items):
    """
    Returns a list of items sorted by urgency to consume.
    Urgency is calculated based on time in fridge vs shelf life.
    Returns a list of dictionaries with item details and status.
    """
    if not items:
        return []

    # Calculate days in fridge and estimated days remaining
    scored_items = []
    now = datetime.utcnow()

    # Pre-fetch shelf life for all relevant items to avoid N+1 queries
    labels = list({item.label.lower() for item in items})

    # Query database for product types
    product_types = ProductType.query.filter(ProductType.name.in_(labels)).all()
    shelf_life_map = {pt.name: pt.shelf_life_days for pt in product_types}

    for item in items:
        days_in_fridge = (now - item.entry_date).days
        # Default to 7 days if unknown
        shelf_life = shelf_life_map.get(item.label.lower(), 7)
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

def get_missing_items(current_items):
    """
    Returns a list of basic items that are missing from the current inventory.
    """
    current_labels = {item.label.lower() for item in current_items}

    # Query basic items from database
    basic_product_types = ProductType.query.filter_by(is_basic=True).all()

    missing = [pt.name for pt in basic_product_types if pt.name not in current_labels]

    return missing
