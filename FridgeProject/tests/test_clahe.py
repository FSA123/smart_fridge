import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add the project root to sys.path so we can import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock dependencies before importing ProductRecognizer
sys.modules['cv2'] = MagicMock()
sys.modules['numpy'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['clip'] = MagicMock()
sys.modules['easyocr'] = MagicMock()
sys.modules['ultralytics'] = MagicMock()
sys.modules['PIL'] = MagicMock()

# Now we can import the module
try:
    from src.product_recognizer import ProductRecognizer
    import cv2 # This will be the mock
except ImportError:
    print("Error: src module not found. Make sure you run this test from the project root or with correct PYTHONPATH.")
    sys.exit(1)

class TestProductRecognizerCLAHE(unittest.TestCase):

    @patch('src.product_recognizer.ProductRecognizer.__init__', return_value=None)
    def setUp(self, mock_init):
        # We patch __init__ so it doesn't run the heavy loading logic
        self.recognizer = ProductRecognizer()

    def test_apply_clahe_logic_and_shape(self):
        """
        Test that apply_clahe calls cv2 functions correctly and maintains image shape.
        """
        # Define constants on the cv2 mock so they are consistent across calls
        cv2.COLOR_BGR2LAB = MagicMock(name='COLOR_BGR2LAB')
        cv2.COLOR_LAB2BGR = MagicMock(name='COLOR_LAB2BGR')

        # Define input shape
        H, W = 100, 100
        input_shape = (H, W, 3)

        # Prepare mock input image with shape
        mock_image = MagicMock(name='input_image')
        mock_image.shape = input_shape

        # Prepare intermediate mock images with shapes
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

        # Configure cv2 mocks to return these mock arrays

        # cvtColor is called twice. We use side_effect to return different values depending on the color code
        def side_effect_cvtColor(src, code):
            if code == cv2.COLOR_BGR2LAB:
                return mock_lab
            elif code == cv2.COLOR_LAB2BGR:
                return mock_enhanced
            # Default return if something else is called (should not happen in this test)
            return MagicMock()

        cv2.cvtColor.side_effect = side_effect_cvtColor

        # split returns a tuple of channels
        cv2.split.return_value = (mock_l, mock_a, mock_b)

        # createCLAHE returns a CLAHE object mock
        mock_clahe = MagicMock()
        cv2.createCLAHE.return_value = mock_clahe
        # clahe.apply returns the enhanced L channel
        mock_clahe.apply.return_value = mock_cl

        # merge returns the merged image
        cv2.merge.return_value = mock_limg

        # Call the method
        result = self.recognizer.apply_clahe(mock_image)

        # --- Logic Verification ---

        # 1. Check if cvtColor was called first with BGR2LAB
        cv2.cvtColor.assert_any_call(mock_image, cv2.COLOR_BGR2LAB)

        # 2. Check split
        cv2.split.assert_called_with(mock_lab)

        # 3. Check createCLAHE parameters
        cv2.createCLAHE.assert_called_with(clipLimit=2.0, tileGridSize=(8, 8))

        # 4. Check clahe.apply on L channel
        mock_clahe.apply.assert_called_with(mock_l)

        # 5. Check merge
        cv2.merge.assert_called_with((mock_cl, mock_a, mock_b))

        # 6. Check cvtColor second call with LAB2BGR
        cv2.cvtColor.assert_any_call(mock_limg, cv2.COLOR_LAB2BGR)

        # --- Shape Verification ---

        # check output is the enhanced image
        self.assertEqual(result, mock_enhanced)

        # verify output shape matches input shape (simulated)
        self.assertEqual(result.shape, input_shape)

if __name__ == '__main__':
    unittest.main()
