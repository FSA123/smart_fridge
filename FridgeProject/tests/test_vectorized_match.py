import sys
import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class TestProductRecognizerVectorized(unittest.TestCase):
    def setUp(self):
        """Set up mocks and create a ProductRecognizer with mocked heavy dependencies."""
        self.mock_torch = MagicMock()
        self.mock_clip = MagicMock()
        self.mock_clip.load.return_value = (MagicMock(), MagicMock())
        self.mock_easyocr = MagicMock()
        self.mock_cv2 = MagicMock()
        self.mock_ultralytics = MagicMock()
        self.mock_pil = MagicMock()
        self.mock_pil_image = MagicMock()

        self.modules_patcher = patch.dict(sys.modules, {
            'torch': self.mock_torch,
            'clip': self.mock_clip,
            'easyocr': self.mock_easyocr,
            'cv2': self.mock_cv2,
            'ultralytics': self.mock_ultralytics,
            'PIL': self.mock_pil,
            'PIL.Image': self.mock_pil_image,
        })
        self.modules_patcher.start()

        # Remove cached module to force re-import with our mocks
        sys.modules.pop('src.product_recognizer', None)

        from src.product_recognizer import ProductRecognizer
        self.recognizer = ProductRecognizer()

        # Override with predictable test data
        self.dim = 4
        self.products = ["Product A", "Product B", "Product C"]
        self.recognizer.product_labels = self.products

        self.embeddings = np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0]
        ], dtype=np.float32)
        self.recognizer.product_embeddings = self.embeddings
        self.recognizer.product_db = {p: e for p, e in zip(self.products, self.embeddings)}

        self.recognizer.device = 'cpu'
        self.recognizer.clip_preprocess = MagicMock()
        self.recognizer.clip_model = MagicMock()

    def tearDown(self):
        self.modules_patcher.stop()
        sys.modules.pop('src.product_recognizer', None)

    def _setup_encode_image_mock(self, result_array):
        """Helper to set up the chain of mocks for clip_model.encode_image."""
        mock1 = MagicMock()
        self.recognizer.clip_model.encode_image.return_value = mock1
        mock3 = MagicMock()
        mock1.__itruediv__.return_value = mock3
        mock4 = MagicMock()
        mock3.cpu.return_value = mock4
        mock4.numpy.return_value = result_array

    def test_get_local_match_vectorized(self):
        """Test that vectorized get_local_match returns the best match."""
        image_feature_numpy = np.array([[0.0, 1.0, 0.0, 0.0]], dtype=np.float32)
        self._setup_encode_image_mock(image_feature_numpy)

        dummy_crop = np.zeros((10, 10, 3), dtype=np.uint8)
        best_match, score = self.recognizer.get_local_match(dummy_crop)

        self.assertEqual(best_match, "Product B")
        self.assertAlmostEqual(score, 1.0)

    def test_get_batch_local_matches(self):
        """Test that batch matching returns correct results for multiple crops."""
        crops = [
            np.zeros((10, 10, 3), dtype=np.uint8),
            np.zeros((10, 10, 3), dtype=np.uint8)
        ]

        batch_features = np.array([
            [1.0, 0.0, 0.0, 0.0],  # matches Product A
            [0.0, 0.0, 1.0, 0.0]   # matches Product C
        ], dtype=np.float32)

        mock_stack = MagicMock()
        self.mock_torch.stack.return_value = mock_stack

        mock_encode = MagicMock()
        self.recognizer.clip_model.encode_image.return_value = mock_encode

        mock_norm_result = MagicMock()
        mock_encode.__itruediv__.return_value = mock_norm_result

        mock_cpu = MagicMock()
        mock_norm_result.cpu.return_value = mock_cpu
        mock_cpu.numpy.return_value = batch_features

        results = self.recognizer.get_batch_local_matches(crops)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0][0], "Product A")
        self.assertAlmostEqual(results[0][1], 1.0)
        self.assertEqual(results[1][0], "Product C")
        self.assertAlmostEqual(results[1][1], 1.0)

    def test_get_batch_local_matches_empty(self):
        """Test that batch matching returns empty list for no crops."""
        results = self.recognizer.get_batch_local_matches([])
        self.assertEqual(results, [])


if __name__ == '__main__':
    unittest.main()
