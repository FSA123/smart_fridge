import os
import threading
from src.database import init_db
from src.detector import FoodDetector
from src.web import create_app
from src.config import IMAGES_DIR

def main():
    # 1. Initialize Database
    print("Initializing database...")
    init_db()

    # 2. Start Food Detector (Background Thread)
    # Detects objects in 'images/' folder every 5 seconds
    # Ensure yolov8n.pt exists or let it download
    detector = FoodDetector(image_folder=IMAGES_DIR, model_path="yolov8n.pt", interval=5)
    detector.start()

    # 3. Start Web Server
    # Host defaults to 127.0.0.1 for security.
    # Set FLASK_HOST=0.0.0.0 to allow access from other devices (like ESP32)
    host = os.getenv('FLASK_HOST', '127.0.0.1')
    print(f"Starting Web Server on {host}:5001...")
    app = create_app()
    app.run(host=host, port=5001, debug=False, use_reloader=False)
    # use_reloader=False prevents double initialization in debug mode

if __name__ == "__main__":
    main()
