import os
import io
import hmac
from functools import wraps
from flask import Blueprint, render_template, request, jsonify, send_from_directory, session, redirect, url_for, flash
from PIL import Image
from datetime import datetime
from src.models import Item
from src.database import db_session
from src.utils import get_recommendations, get_missing_items
from src.config import IMAGES_DIR

main = Blueprint('main', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            # Return 401 for API calls
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Unauthorized'}), 401
            # Redirect to login for page loads
            return redirect(url_for('main.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == os.environ.get('ADMIN_PASSWORD', 'admin'):
            session['logged_in'] = True
            next_url = request.args.get('next')
            return redirect(next_url or url_for('main.dashboard'))
        else:
            flash('Invalid password')
    return render_template('login.html')

@main.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('main.login'))

@main.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')

@main.route('/upload', methods=['POST'])
def upload():
    # Security: Verify API Key
    api_key = os.environ.get('FRIDGE_API_KEY')
    if not api_key:
        print("Security Error: FRIDGE_API_KEY environment variable not set. Refusing upload.")
        return "Server misconfiguration", 500

    request_key = request.headers.get('X-API-Key')
    if not request_key or not hmac.compare_digest(request_key, api_key):
        print("Security Warning: Unauthorized upload attempt.")
        return "Unauthorized", 401

    # The ESP32 sends the photo in the 'body' of the message
    img_data = request.data
    if img_data:
        # Validate that the data is a valid JPEG image
        try:
            image = Image.open(io.BytesIO(img_data))
            image.verify()
            if image.format != 'JPEG':
                print(f"Invalid image format: {image.format}")
                return "FAILED: Only JPEG images are supported", 400
        except Exception as e:
            print(f"Invalid image data: {e}")
            return "FAILED: Invalid image data", 400

        # Create a unique name using the current date and time
        # This format MUST match src/detector.py expectations
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"capture_{timestamp}.jpg"

        # Ensure directory exists
        if not os.path.exists(IMAGES_DIR):
            os.makedirs(IMAGES_DIR)

        filepath = os.path.join(IMAGES_DIR, filename)

        # Write the binary data to a file
        with open(filepath, "wb") as f:
            f.write(img_data)

        print(f"Successfully received: {filename}")
        return "SUCCESS", 200
    else:
        print("Received an empty request.")
        return "FAILED", 400

@main.route('/api/data')
@login_required
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
@login_required
def serve_image(filename):
    return send_from_directory(os.path.abspath(IMAGES_DIR), filename)
