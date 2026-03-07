import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add the project root to sys.path so we can import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestProductRecognizerCLAHE(unittest.TestCase):

    def setUp(self):
        """Set up mocks and create a ProductRecognizer with patched __init__."""
        self.mock_cv2 = MagicMock()
        self.mock_torch = MagicMock()
        self.mock_clip = MagicMock()
        self.mock_easyocr = MagicMock()
        self.mock_ultralytics = MagicMock()
        self.mock_pil = MagicMock()
        self.mock_numpy = MagicMock()

        self.modules_patcher = patch.dict(sys.modules, {
            'cv2': self.mock_cv2,
            'torch': self.mock_torch,
            'clip': self.mock_clip,
            'easyocr': self.mock_easyocr,
            'ultralytics': self.mock_ultralytics,
            'PIL': self.mock_pil,
            'numpy': self.mock_numpy
        })
        self.modules_patcher.start()

        # Remove cached module to force re-import with our mocks
        sys.modules.pop('src.product_recognizer', None)

        from src.product_recognizer import ProductRecognizer

        with patch.object(ProductRecognizer, '__init__', return_value=None):
            self.recognizer = ProductRecognizer()

        # Import cv2 as the mock
        import cv2
        self.cv2 = cv2

    def tearDown(self):
        self.modules_patcher.stop()
        sys.modules.pop('src.product_recognizer', None)

    def test_apply_clahe_logic_and_shape(self):
        """Test that apply_clahe calls cv2 functions correctly and maintains image shape."""
        cv2 = self.cv2
        cv2.COLOR_BGR2LAB = MagicMock(name='COLOR_BGR2LAB')
        cv2.COLOR_LAB2BGR = MagicMock(name='COLOR_LAB2BGR')

        H, W = 100, 100
        input_shape = (H, W, 3)

        mock_image = MagicMock(name='input_image')
        mock_image.shape = input_shape

        mock_lab = MagicMock(name='lab_image')
        mock_lab.shape = input_shape

        mock_l = MagicMock(name='l_channel')
        mock_l.shape = (H, W)

        mock_a = MagicMock(name='a_channel')
        mock_a.shape = (H, W)

        mock_b = MagicMock(name='b_channel')
        mock_b.shape = (H, W)

        mock_cl = MagicMock(name='clahe_l_channel')
        mock_cl.shape = (H, W)

        mock_limg = MagicMock(name='merged_lab')
        mock_limg.shape = input_shape

        mock_enhanced = MagicMock(name='enhanced_image')
        mock_enhanced.shape = input_shape

        def side_effect_cvtColor(src, code):
            if code == cv2.COLOR_BGR2LAB:
                return mock_lab
            elif code == cv2.COLOR_LAB2BGR:
                return mock_enhanced
            return MagicMock()

        cv2.cvtColor.side_effect = side_effect_cvtColor
        cv2.split.return_value = (mock_l, mock_a, mock_b)

        mock_clahe = MagicMock()
        cv2.createCLAHE.return_value = mock_clahe
        mock_clahe.apply.return_value = mock_cl
        cv2.merge.return_value = mock_limg

        result = self.recognizer.apply_clahe(mock_image)

        cv2.cvtColor.assert_any_call(mock_image, cv2.COLOR_BGR2LAB)
        cv2.split.assert_called_with(mock_lab)
        cv2.createCLAHE.assert_called_with(clipLimit=2.0, tileGridSize=(8, 8))
        mock_clahe.apply.assert_called_with(mock_l)
        cv2.merge.assert_called_with((mock_cl, mock_a, mock_b))
        cv2.cvtColor.assert_any_call(mock_limg, cv2.COLOR_LAB2BGR)

        self.assertEqual(result, mock_enhanced)
        self.assertEqual(result.shape, input_shape)

if __name__ == '__main__':
    unittest.main()
