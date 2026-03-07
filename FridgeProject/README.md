# Smart Fridge Monitor

This project extends a food recognition model to identify food in a fridge, track its freshness, and provide recommendations and shopping lists.

## Features
- **Food Recognition**: Uses YOLOv8 to identify food items from images.
- **Freshness Tracking**: Tracks how long items have been in the fridge.
- **Recommendations**: Suggests what to consume first based on shelf life.
- **Shopping List**: Automatically generates a list of missing basic items.
- **Dashboard**: A beautiful web interface to view inventory and recommendations.
- **ESP32 Integration**: Supports image upload from an ESP32-CAM module.

## Project Structure
- `src/`: Source code.
  - `detector.py`: Background process for image analysis.
  - `web/`: Flask web application.
  - `database.py`: Database setup (SQLite).
  - `models.py`: Database models.
  - `utils.py`: Utility functions.
- `firmware/`: ESP32-CAM firmware.
- `images/`: Directory where captured images are stored.
- `main.py`: Main entry point.

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. (Optional) Setup ESP32-CAM:
   - Go to `firmware/` directory.
   - Copy `secrets_example.h` to `secrets.h`.
   - Update `secrets.h` with your WiFi credentials, Server IP, and API key.
   - Flash `firmware/esp32cam.ino` to your ESP32-CAM.

## Usage

1. Run the main application:
   ```bash
   python3 main.py
   ```
   This will start the web server on port 5001 (bound to localhost by default) and the background detector.

   **Note on Remote Access / ESP32 Integration:**
   By default, the server only accepts connections from the local machine (`127.0.0.1`). If you need to allow access from other devices (like the ESP32-CAM), set the `FLASK_HOST` environment variable:
   ```bash
   export FLASK_HOST=0.0.0.0
   python3 main.py
   ```
   **Security Warning:** This exposes the application to the entire network. Ensure you are on a trusted network.

2. Open the dashboard:
   - Go to `http://localhost:5001` in your browser.

3. Upload images:
   - The system automatically monitors the `images/` directory.
   - You can manually add images there or use the ESP32-CAM to upload them automatically.
   - Images should be named `capture_YYYYMMDD_HHMMSS.jpg` for accurate timestamping. If not, the current time is used.

## Configuration
- **Secret Key**: Set `SECRET_KEY` environment variable for Flask session security (defaults to `dev_key` in development).
- **Admin Password**: Set `ADMIN_PASSWORD` environment variable for dashboard login (defaults to `admin`).
- **API Key**: Set `FRIDGE_API_KEY` environment variable on the server; add the same key to `firmware/secrets.h` as `apiKey`.
- **Basic Items**: You can configure the list of basic items in `src/utils.py`.
- **Shelf Life**: Adjust shelf life estimates in `src/utils.py`.

## License
MIT
