import torch
import clip
import easyocr
import cv2
import numpy as np
from datetime import datetime
from ultralytics import YOLO
from PIL import Image

class ProductRecognizer:
    def __init__(self, model_path="yolov8n.pt"):
        print("Initializing ProductRecognizer...")

        # 1. Load YOLO
        print(f"Loading YOLO from {model_path}...")
        self.yolo = YOLO(model_path)

        # 2. Load CLIP
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading CLIP (ViT-L/14) on {self.device}...")
        self.clip_model, self.clip_preprocess = clip.load("ViT-L/14", device=self.device)

        # 3. Load EasyOCR
        print("Loading EasyOCR...")
        # gpu=True if self.device == 'cuda' else False
        use_gpu = self.device == 'cuda'
        self.reader = easyocr.Reader(['en'], gpu=use_gpu)

        # 4. Initialize Mock Database (Lidl Products)
        print("Initializing Mock Vector Database...")
        self.product_db = self._init_mock_db()

        print("ProductRecognizer initialized.")

    def _init_mock_db(self):
        """
        Creates a mock database of embeddings for Lidl products.
        In a real scenario, this would load from FAISS or ChromaDB.
        """
        products = [
            "Pilos Milk 1L",
            "Pilos Gouda Cheese",
            "Freeway Cola",
            "Lidl Greek Yogurt",
            "Solevita Orange Juice",
            "Alesto Mixed Nuts",
            "Fin Carré Chocolate",
            "W5 Dish Soap",
            "Cien Hand Soap",
            "Dulano Ham"
        ]

        db = {}
        with torch.no_grad():
            text_inputs = clip.tokenize(products).to(self.device)
            text_features = self.clip_model.encode_text(text_inputs)
            text_features /= text_features.norm(dim=-1, keepdim=True)

            for i, product in enumerate(products):
                db[product] = text_features[i].cpu().numpy()

        return db

    def apply_clahe(self, image):
        """
        Applies Contrast Limited Adaptive Histogram Equalization (CLAHE) to normalize lighting.
        """
        # Convert to LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # Apply CLAHE to L-channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)

        # Merge channels and convert back to BGR
        limg = cv2.merge((cl, a, b))
        enhanced_img = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

        return enhanced_img

    def detect_objects(self, image_path):
        """
        Runs YOLOv8 detection on the image.
        Returns a list of detected objects with bounding boxes and crops.
        """
        # Load image
        original_img = cv2.imread(image_path)
        if original_img is None:
            print(f"Error: Could not read image at {image_path}")
            return []

        # Apply CLAHE
        enhanced_img = self.apply_clahe(original_img)

        # Run Inference
        results = self.yolo.predict(source=enhanced_img, conf=0.25, verbose=False)

        detections = []
        for result in results:
            for box in result.boxes:
                # Extract coordinates
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                label = self.yolo.names[cls]

                # Crop the object (handle boundaries)
                h, w, _ = enhanced_img.shape
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)

                if x2 > x1 and y2 > y1:
                    crop = enhanced_img[y1:y2, x1:x2]
                    detections.append({
                        'bbox': [x1, y1, x2, y2],
                        'crop': crop,
                        'yolo_label': label,
                        'yolo_conf': conf
                    })

        return detections

    def get_batch_local_matches(self, crops):
        """
        Batch version of get_local_match.
        Returns a list of tuples: (best_match_label, similarity_score)
        """
        if not crops:
            return []

        # Preprocess all crops
        inputs = []
        for c in crops:
            rgb_image = cv2.cvtColor(c, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_image)
            inputs.append(self.clip_preprocess(pil_image))

        # Stack into batch
        image_input = torch.stack(inputs).to(self.device)

        with torch.no_grad():
            image_features = self.clip_model.encode_image(image_input)
            image_features /= image_features.norm(dim=-1, keepdim=True)
            image_features = image_features.cpu().numpy()

        # Compute similarities against DB
        labels = list(self.product_db.keys())
        # self.product_db values are numpy arrays of shape (1, D)
        # We need to stack them into (M, D)
        db_matrix = np.vstack(list(self.product_db.values()))

        # Compute cosine similarity matrix: (N, D) @ (M, D).T -> (N, M)
        sim_matrix = np.dot(image_features, db_matrix.T)

        results = []
        for i in range(len(crops)):
            scores = sim_matrix[i]
            best_idx = np.argmax(scores)
            max_score = float(scores[best_idx])
            best_label = labels[best_idx]
            results.append((best_label, max_score))

        return results

    def get_local_match(self, crop_image):
        """
        Stage 1: Local Embedding Match using CLIP.
        Compares the crop embedding with the mock Lidl database.
        Returns (best_match_label, similarity_score).
        """
        # Convert BGR (OpenCV) to RGB (PIL)
        rgb_image = cv2.cvtColor(crop_image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_image)

        # Preprocess and Encode
        image_input = self.clip_preprocess(pil_image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            image_features = self.clip_model.encode_image(image_input)
            image_features /= image_features.norm(dim=-1, keepdim=True)
            image_features = image_features.cpu().numpy()

        # Calculate Similarity
        best_match = None
        max_similarity = -1.0

        for label, db_embedding in self.product_db.items():
            # Cosine similarity: dot product of normalized vectors
            similarity = np.dot(image_features, db_embedding.T).item()
            if similarity > max_similarity:
                max_similarity = similarity
                best_match = label

        return best_match, max_similarity

    def perform_ocr(self, crop_image):
        """
        Stage 2: OCR Refinement using EasyOCR.
        Extracts text and checks for brand/product names.
        Returns (refined_label, confidence_boost) or (None, 0.0).
        """
        try:
            results = self.reader.readtext(crop_image)
            detected_text = [text for (_, text, conf) in results if conf > 0.4]
            full_text = " ".join(detected_text).lower()

            # Simple keyword matching against DB keys
            best_match = None
            max_len = 0

            for product in self.product_db.keys():
                # Check if significant part of product name is in detected text
                # e.g. "Pilos" in "Pilos Milk"
                parts = product.lower().split()
                matches = sum(1 for part in parts if part in full_text)

                if matches > 0:
                    # simplistic scoring: more matching words = better
                    if matches > max_len:
                        max_len = matches
                        best_match = product

            if best_match:
                # If we found text evidence, return high confidence
                return best_match, 0.95

        except Exception as e:
            print(f"OCR Error: {e}")

        return None, 0.0

    def call_vlm_fallback(self, crop_image):
        """
        Stage 3: Vision-Language Model Fallback (Mock).
        Simulates calling Gemini/Google Vision API.
        """
        print("Triggering VLM Fallback (Mock)...")
        # In a real implementation, we would encode the image and send to API
        # response = model.generate_content(["Identify this product", crop_image])

        # specific logic: if we are here, previous stages failed.
        # We'll just return None to indicate failure to identify high confidence,
        # or we could return a "General Food" label.

        return "Unknown", 0.0

    def recognize(self, image_path):
        """
        Ensemble Recognition Pipeline.
        Orchestrates Detection -> Stage 1 -> Stage 2 -> Stage 3.
        Returns a list of dicts with keys: 'label', 'confidence', 'bbox'.
        """
        detections = self.detect_objects(image_path)
        results = []

        if not detections:
            return []

        # Collect crops for batch processing
        crops = [d['crop'] for d in detections]

        # --- Stage 1: Batch Local Embedding Match ---
        s1_results = self.get_batch_local_matches(crops)

        for i, det in enumerate(detections):
            crop = det['crop']
            bbox = det['bbox']

            s1_label, s1_score = s1_results[i]
            print(f"Stage 1: {s1_label} ({s1_score:.2f})")

            final_label = s1_label
            final_score = s1_score

            # Decision Logic
            if s1_score > 0.85:
                # High confidence match
                pass

            elif 0.6 < s1_score <= 0.85:
                # --- Stage 2: OCR Refinement ---
                print("Stage 2: OCR Refinement...")
                s2_label, s2_score = self.perform_ocr(crop)

                if s2_label:
                    print(f"Stage 2 Match: {s2_label}")
                    final_label = s2_label
                    final_score = s2_score # Boosted to ~0.95
                else:
                    print("Stage 2: No text match.")

            else:
                # s1_score <= 0.6 -> Low confidence
                print("Stage 1 score too low. Skipping Stage 2, going to Stage 3.")

            # Check if we need Stage 3
            if final_score < 0.9:
                # --- Stage 3: VLM Fallback ---
                # Only if cumulative score is low
                s3_label, s3_score = self.call_vlm_fallback(crop)
                if s3_label != "Unknown":
                    final_label = s3_label
                    final_score = s3_score
                else:
                    # Log low confidence detection for Active Learning
                    self._log_low_confidence(image_path, crop, s1_label, s1_score)

            results.append({
                'label': final_label if final_label else "Unknown",
                'confidence': final_score,
                'bbox': bbox
            })

        return results

    def _log_low_confidence(self, image_path, crop, s1_label, s1_score):
        """
        Logs low confidence detections to a file for Active Learning.
        """
        log_file = "active_learning_candidates.log"
        timestamp = datetime.now().isoformat()

        # In a real system, we might save the crop to a folder
        # crop_filename = f"low_conf_{timestamp}.jpg"
        # cv2.imwrite(crop_filename, crop)

        with open(log_file, "a") as f:
            f.write(f"[{timestamp}] Low confidence detection in {image_path}. "
                    f"Stage 1 match: {s1_label} ({s1_score:.2f})\n")

if __name__ == "__main__":
    recognizer = ProductRecognizer()
    print("DB Keys:", list(recognizer.product_db.keys()))
    # Test detection (requires an image 'test_image.jpg')
    # detections = recognizer.detect_objects("test_image.jpg")
    # print(f"Detections: {len(detections)}")
