import os
import threading
from src.database import init_db
from src.detector import FoodDetector
from src.web import create_app

def main():
    # 1. Initialize Database
    print("Initializing database...")
    init_db()

    # 2. Start Food Detector (Background Thread)
    # Detects objects in 'images/' folder every 5 seconds
    # Ensure yolov8s-world.pt exists or let it download
    detector = FoodDetector(image_folder="images", model_path="yolov8s-world.pt", interval=5)
    detector.start()

    # 3. Start Web Server
    # Host 0.0.0.0 allows access from other devices (like ESP32)
    print("Starting Web Server on port 5001...")
    app = create_app()
    app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)
    # use_reloader=False prevents double initialization in debug mode

if __name__ == "__main__":
    main()
