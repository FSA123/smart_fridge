import os
import time
from ultralytics import YOLO

# 1. Load a pre-trained "Nano" model (Fastest for Mac/Raspberry Pi)
# This will download 'yolov8n.pt' automatically the first time you run it.
model = YOLO('yolov8n.pt')

IMAGE_FOLDER = "./images"
# This set keeps track of images we have already analyzed so we don't repeat work
processed_images = set()

print("AI Processor started. Waiting for fridge photos...")

while True:
    # Get list of all .jpg files in the folder
    current_files = [f for f in os.listdir(IMAGE_FOLDER) if f.endswith(".jpg")]
    
    for file in current_files:
        if file not in processed_images:
            print(f"\n[AI] New image detected: {file}")
            img_path = os.path.join(IMAGE_FOLDER, file)
            
            # 2. Run the AI on the image
            # 'conf=0.25' means only report items it's at least 25% sure about
            results = model.predict(source=img_path, conf=0.25, save=False)
            
            # 3. Parse the results
            inventory = []
            for result in results:
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    label = model.names[class_id]
                    inventory.append(label)
            
            if inventory:
                print(f"Detected Items: {inventory}")
                # Logic: In the next step, we would save this to a database
            else:
                print("No recognizable food items found.")

            processed_images.add(file)
            
    time.sleep(2) # Wait 2 seconds before checking the folder again