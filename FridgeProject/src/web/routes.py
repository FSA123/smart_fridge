import os
from functools import wraps
from flask import Blueprint, render_template, request, jsonify, send_from_directory, current_app, session, redirect, url_for, flash
from datetime import datetime
from src.models import Item
from src.database import db_session
from src.utils import get_recommendations, get_missing_items

main = Blueprint('main', __name__)
SAVE_PATH = "images"

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
        # Simple password check against environment variable or default
        if password == os.environ.get('ADMIN_PASSWORD', 'admin'):
            session['logged_in'] = True
            # Redirect to 'next' if it exists, otherwise dashboard
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
    return send_from_directory(os.path.abspath(SAVE_PATH), filename)
