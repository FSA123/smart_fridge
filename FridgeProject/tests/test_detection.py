import cv2
import numpy as np
from src.product_recognizer import ProductRecognizer
import os

def test_detection():
    # Create a dummy image (random noise)
    img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    cv2.imwrite("test_detection.jpg", img)

    try:
        recognizer = ProductRecognizer()
        print("Running detection on dummy image...")
        detections = recognizer.detect_objects("test_detection.jpg")
        print(f"Detection successful. Found {len(detections)} objects (expected 0 on noise).")

        # Clean up
        os.remove("test_detection.jpg")
    except Exception as e:
        print(f"Test failed with error: {e}")
        if os.path.exists("test_detection.jpg"):
            os.remove("test_detection.jpg")
        exit(1)

if __name__ == "__main__":
    test_detection()
