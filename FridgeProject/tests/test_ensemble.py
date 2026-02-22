from src.product_recognizer import ProductRecognizer
import numpy as np
from unittest.mock import MagicMock
import cv2

def test_ensemble():
    recognizer = ProductRecognizer()

    # Mock detect_objects to return a dummy detection
    dummy_crop = np.zeros((100, 100, 3), dtype=np.uint8)
    dummy_detections = [{
        'bbox': [0, 0, 100, 100],
        'crop': dummy_crop,
        'yolo_label': 'bottle',
        'yolo_conf': 0.8
    }]
    recognizer.detect_objects = MagicMock(return_value=dummy_detections)

    # Mock Stage 1 to return a medium score (to trigger Stage 2)
    recognizer.get_local_match = MagicMock(return_value=("Possible Milk", 0.7))

    # Mock Stage 2 to return a match (to boost score)
    recognizer.perform_ocr = MagicMock(return_value=("Confirmed Milk", 0.95))

    # Run recognition
    print("Running Ensemble Recognition Test...")
    results = recognizer.recognize("dummy_path.jpg")

    print("Results:", results)

    # Verification
    if len(results) == 1:
        res = results[0]
        if res['label'] == "Confirmed Milk" and res['confidence'] == 0.95:
            print("Ensemble Test Passed (Stage 1 -> Stage 2 Success).")
        else:
            print(f"Ensemble Test Failed: Unexpected result {res}")
    else:
        print("Ensemble Test Failed: No results.")

    # Test Fallback Logic (Low S1, No S2 match -> S3)
    recognizer.get_local_match = MagicMock(return_value=("Unknown Blob", 0.4))
    recognizer.perform_ocr = MagicMock(return_value=(None, 0.0))
    recognizer.call_vlm_fallback = MagicMock(return_value=("VLM Apple", 0.88))

    print("\nRunning Ensemble Fallback Test...")
    results_fb = recognizer.recognize("dummy_path.jpg")
    print("Results:", results_fb)

    if len(results_fb) == 1:
        res = results_fb[0]
        if res['label'] == "VLM Apple":
             print("Ensemble Fallback Test Passed (Low S1 -> S3 Success).")
        else:
             print(f"Ensemble Fallback Test Failed: {res}")

    # Test Active Learning Logging
    recognizer.get_local_match = MagicMock(return_value=("Unknown Blob", 0.4))
    recognizer.perform_ocr = MagicMock(return_value=(None, 0.0))
    recognizer.call_vlm_fallback = MagicMock(return_value=("Unknown", 0.0))

    print("\nRunning Active Learning Logging Test...")
    recognizer.recognize("dummy_path.jpg")

    import os
    if os.path.exists("active_learning_candidates.log"):
        print("Active Learning Log created.")
        with open("active_learning_candidates.log", "r") as f:
            print("Log content:", f.read())
        os.remove("active_learning_candidates.log")
    else:
        print("Active Learning Logging Failed: File not found.")

if __name__ == "__main__":
    test_ensemble()
