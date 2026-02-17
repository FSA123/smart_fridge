import os
from flask import Blueprint, render_template, request, jsonify, send_from_directory, current_app
from datetime import datetime
from src.models import Item
from src.database import db_session
from src.utils import get_recommendations, get_missing_items

main = Blueprint('main', __name__)
SAVE_PATH = "images"

@main.route('/')
def dashboard():
    return render_template('dashboard.html')

@main.route('/upload', methods=['POST'])
def upload():
    # The ESP32 sends the photo in the 'body' of the message
    img_data = request.data
    if img_data:
        # Create a unique name using the current date and time
        # This format MUST match src/detector.py expectations
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"capture_{timestamp}.jpg"

        # Ensure directory exists
        if not os.path.exists(SAVE_PATH):
            os.makedirs(SAVE_PATH)

        filepath = os.path.join(SAVE_PATH, filename)

        # Write the binary data to a file
        with open(filepath, "wb") as f:
            f.write(img_data)

        print(f"Successfully received: {filename}")
        return "SUCCESS", 200
    else:
        print("Received an empty request.")
        return "FAILED", 400

@main.route('/api/data')
def api_data():
    active_items = Item.query.filter_by(status='active').all()
    recommendations = get_recommendations(active_items)
    missing = get_missing_items(active_items)

    # Format for JSON
    data = {
        'inventory': recommendations, # Already formatted dicts by get_recommendations
        'missing': missing,
        'count': len(active_items)
    }
    return jsonify(data)

@main.route('/images/<path:filename>')
def serve_image(filename):
    return send_from_directory(os.path.abspath(SAVE_PATH), filename)
