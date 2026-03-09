import cv2
import numpy as np
from src.product_recognizer import ProductRecognizer

def test_stages2_3():
    # 1. Test OCR with a generated image containing text
    print("Creating image with text 'Pilos'...")
    img = np.zeros((100, 300, 3), dtype=np.uint8)
    cv2.putText(img, "Pilos", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)

    try:
        recognizer = ProductRecognizer()
        print("Testing OCR...")
        label, score = recognizer.perform_ocr(img)
        print(f"OCR Result: {label} (Score: {score})")

        if label and "Pilos" in label:
            print("OCR Test Passed.")
        else:
            print("OCR Test Failed or No Text Detected.")

        # 2. Test VLM Fallback
        print("Testing VLM Fallback...")
        vlm_label, vlm_score = recognizer.call_vlm_fallback()
        print(f"VLM Result: {vlm_label} (Score: {vlm_score})")

        if vlm_label == "Unknown":
            print("VLM Test Passed.")
        else:
            print("VLM Test Failed.")

    except Exception as e:
        print(f"Test failed with error: {e}")
        exit(1)

if __name__ == "__main__":
    test_stages2_3()
