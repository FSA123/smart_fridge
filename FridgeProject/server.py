from flask import Flask, request
import os
from datetime import datetime

app = Flask(__name__)
# Define where to save the images
SAVE_PATH = "./images"

@app.route('/upload', methods=['POST'])
def upload():
    # The ESP32 sends the photo in the 'body' of the message
    img_data = request.data
    if img_data:
        # Create a unique name using the current date and time
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"capture_{timestamp}.jpg"
        filepath = os.path.join(SAVE_PATH, filename)
        
        # Write the binary data to a file
        with open(filepath, "wb") as f:
            f.write(img_data)
            
        print(f"Successfully received: {filename}")
        return "SUCCESS", 200
    else:
        print("Received an empty request.")
        return "FAILED", 400

if __name__ == '__main__':
    # '0.0.0.0' allows the ESP32 to find your Mac over Wi-Fi
    app.run(host='0.0.0.0', port=5001)