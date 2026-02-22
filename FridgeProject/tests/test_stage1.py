import cv2
import numpy as np
from src.product_recognizer import ProductRecognizer

def test_stage1():
    # Create a dummy crop (e.g., solid red)
    crop = np.zeros((224, 224, 3), dtype=np.uint8)
    crop[:] = (0, 0, 255) # BGR: Red

    try:
        recognizer = ProductRecognizer()
        print("Running Stage 1 on dummy crop...")
        label, score = recognizer.get_local_match(crop)
        print(f"Stage 1 Result: {label} (Score: {score:.4f})")

        if label is None or score < -1.0 or score > 1.0:
            print("Test failed: Invalid result.")
            exit(1)

    except Exception as e:
        print(f"Test failed with error: {e}")
        exit(1)

if __name__ == "__main__":
    test_stage1()
