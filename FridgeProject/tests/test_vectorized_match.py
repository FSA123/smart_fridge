import sys
import unittest
from unittest.mock import MagicMock
import numpy as np
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

# Mock dependencies
sys.modules['torch'] = MagicMock()
clip_mock = MagicMock()
# clip.load must return (model, preprocess)
clip_mock.load.return_value = (MagicMock(), MagicMock())
sys.modules['clip'] = clip_mock
sys.modules['easyocr'] = MagicMock()
sys.modules['cv2'] = MagicMock()
sys.modules['ultralytics'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()

# Now import the class to be tested
# We need to handle the import inside a try block or just assume it works due to mocks
try:
    from product_recognizer import ProductRecognizer
except ImportError:
    # If run from root, src.product_recognizer
    try:
        from src.product_recognizer import ProductRecognizer
    except ImportError:
        print("Could not import ProductRecognizer")
        sys.exit(1)

class TestProductRecognizerOptimization(unittest.TestCase):
    def setUp(self):
        # Mock __init__ components to avoid heavy lifting during init
        # We need to manually set up the recognizer since we are mocking everything
        # ProductRecognizer.__init__ calls _init_mock_db which uses clip

        # We need to mock _init_mock_db behavior or let it run with mocks
        # If we let it run, clip.tokenize returns a mock, encode_text returns a mock...
        # It sets self.product_embeddings to a mock.
        # So we should overwrite it in setUp.

        self.recognizer = ProductRecognizer()

        # Setup mock embeddings
        self.dim = 4
        self.num_products = 3
        self.products = ["Product A", "Product B", "Product C"]
        self.recognizer.product_labels = self.products

        # Create normalized embeddings
        # A: [1, 0, 0, 0]
        # B: [0, 1, 0, 0]
        # C: [0, 0, 1, 0]
        self.embeddings = np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0]
        ], dtype=np.float32)
        self.recognizer.product_embeddings = self.embeddings
        self.recognizer.product_db = {p: e for p, e in zip(self.products, self.embeddings)}

        # Mock clip related stuff for get_local_match
        self.recognizer.device = 'cpu'
        self.recognizer.clip_preprocess = MagicMock()
        self.recognizer.clip_model = MagicMock()

    def test_get_local_match_vectorized(self):
        # Create a mock image feature that should match Product B
        # Image feature: [0, 1, 0, 0]
        image_feature_numpy = np.array([[0.0, 1.0, 0.0, 0.0]], dtype=np.float32)

        # Mock the clip model encoding sequence
        mock_encoded_tensor = MagicMock()
        self.recognizer.clip_model.encode_image.return_value = mock_encoded_tensor

        # Mock the division: image_features /= ...
        # This is in-place division.
        # tensor.__itruediv__
        # But wait, the code is:
        # image_features = self.clip_model.encode_image(image_input)
        # image_features /= image_features.norm(dim=-1, keepdim=True)
        # image_features = image_features.cpu().numpy()

        # If image_features is a MagicMock, /= modifies it in place or returns new one?
        # Typically it calls __itruediv__.

        # Let's mock the final result of .cpu().numpy() on the object returned by encode_image
        # Assuming the code flow doesn't break on mocks.

        # The chain:
        # 1. encode_image -> mock1
        # 2. mock1.norm -> mock2
        # 3. mock1 /= mock2 -> calls mock1.__itruediv__(mock2) -> returns mock3 (or modifies mock1)
        # 4. mock3.cpu() -> mock4
        # 5. mock4.numpy() -> FINAL_RESULT

        mock1 = MagicMock()
        self.recognizer.clip_model.encode_image.return_value = mock1

        mock3 = MagicMock()
        mock1.__itruediv__.return_value = mock3

        mock4 = MagicMock()
        mock3.cpu.return_value = mock4

        mock4.numpy.return_value = image_feature_numpy

        # Call get_local_match
        dummy_crop = np.zeros((10, 10, 3), dtype=np.uint8)
        best_match, score = self.recognizer.get_local_match(dummy_crop)

        print(f"Test Result: Match={best_match}, Score={score}")

        self.assertEqual(best_match, "Product B")
        self.assertAlmostEqual(score, 1.0)

    def test_get_local_match_complex(self):
        # Test with a mix
        # Image: [0.5, 0.5, 0, 0] -> normalized: [0.707, 0.707, 0, 0]
        val = 1.0 / np.sqrt(2)
        image_feature_numpy = np.array([[val, val, 0.0, 0.0]], dtype=np.float32)

        mock1 = MagicMock()
        self.recognizer.clip_model.encode_image.return_value = mock1
        mock3 = MagicMock()
        mock1.__itruediv__.return_value = mock3
        mock4 = MagicMock()
        mock3.cpu.return_value = mock4
        mock4.numpy.return_value = image_feature_numpy

        dummy_crop = np.zeros((10, 10, 3), dtype=np.uint8)
        best_match, score = self.recognizer.get_local_match(dummy_crop)

        print(f"Test Result (Complex): Match={best_match}, Score={score}")

        # Both A and B have score 0.707. argmax returns first occurrence (A) usually.
        # But floating point might vary slightly.
        # Let's assume A (index 0).
        self.assertTrue(best_match in ["Product A", "Product B"])
        self.assertAlmostEqual(score, val, places=5)

if __name__ == '__main__':
    unittest.main()
