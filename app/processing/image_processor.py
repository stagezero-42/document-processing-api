# filename: app/processing/image_processor.py
import os
from typing import Dict, Any, Optional, List
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import pytesseract  # type: ignore
import cv2  # type: ignore
import numpy as np  # type: ignore
import pandas as pd  # OCR CHANGE: Added pandas for DataFrame output


# --- Preprocessing Functions ---
def deskew(image_cv: np.ndarray) -> np.ndarray:  # MODIFIED: Takes OpenCV image
    """Corrects skew in an OpenCV image (expects grayscale)."""
    try:
        # Ensure input is grayscale for deskewing logic
        if len(image_cv.shape) == 3 and image_cv.shape[2] == 3:  # Check if it's BGR
            gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
        elif len(image_cv.shape) == 3 and image_cv.shape[2] == 4:  # Check if it's BGRA
            gray = cv2.cvtColor(image_cv, cv2.COLOR_BGRA2GRAY)
        elif len(image_cv.shape) == 2:  # Already grayscale
            gray = image_cv
        else:
            print("Warning: Deskew input image has unexpected shape. Attempting to proceed.")
            gray = image_cv  # Or raise an error

        # Invert colors for better edge detection on dark text if necessary
        # Otsu's method usually works well on non-inverted images too.
        # Consider if this inversion is always optimal.
        # gray_inverted = cv2.bitwise_not(gray)

        # Threshold to get rid of extraneous noise
        # Using inverted gray for coords as per original logic
        thresh = cv2.threshold(cv2.bitwise_not(gray), 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

        coords = np.column_stack(np.where(thresh > 0))
        if coords.size == 0:  # No content found after thresholding
            print("Warning: No content found for deskewing after thresholding. Skipping deskew.")
            return image_cv  # Return original if no points found

        angle = cv2.minAreaRect(coords)[-1]

        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        (h, w) = gray.shape[:2]  # Use gray image shape
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        # Rotate the original image_cv (which might be color or gray)
        rotated = cv2.warpAffine(image_cv, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

        return rotated
    except Exception as e:
        print(f"Error during deskewing: {e}. Returning original image.")
        return image_cv


def preprocess_image_for_ocr(
        image_path: str,
        apply_preprocessing: bool = True,
        deskew_image_flag: bool = True,  # Renamed to avoid conflict
        target_dpi: int = 300  # target_dpi not fully implemented yet
) -> Image.Image:
    """
    Loads an image and applies a standard set of preprocessing steps.
    Returns a Pillow Image in 'L' (grayscale) or '1' (binary) mode.
    """
    try:
        pil_img = Image.open(image_path)

        # Convert to OpenCV format (BGR by default from Pillow RGB)
        cv_img_bgr = np.array(pil_img.convert('RGB'))
        cv_img_bgr = cv2.cvtColor(cv_img_bgr, cv2.COLOR_RGB2BGR)

        # Initial conversion to grayscale for most operations
        cv_img_gray = cv2.cvtColor(cv_img_bgr, cv2.COLOR_BGR2GRAY)

        processed_cv_img = cv_img_gray.copy()  # Work on a copy

        if apply_preprocessing:
            # Deskew (operates on grayscale, returns potentially color or gray)
            if deskew_image_flag:
                # Pass the BGR image to deskew, let deskew handle grayscale conversion for its logic
                # but it will rotate the original BGR image.
                deskewed_cv_img_bgr = deskew(cv_img_bgr.copy())
                # After deskewing, convert back to gray for further processing if it returned color
                if len(deskewed_cv_img_bgr.shape) == 3:
                    processed_cv_img = cv2.cvtColor(deskewed_cv_img_bgr, cv2.COLOR_BGR2GRAY)
                else:
                    processed_cv_img = deskewed_cv_img_bgr

            # Binarization (Otsu's method) - applied on the (potentially deskewed) grayscale image
            # cv2.threshold requires an 8-bit single-channel image. processed_cv_img is now definitely grayscale.
            _, binary_cv_img = cv2.threshold(processed_cv_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Convert the final processed OpenCV image (binary) back to Pillow Image
            final_pil_img = Image.fromarray(binary_cv_img).convert('L')  # Convert binary to L for tesseract
            # Tesseract can handle L mode well
            return final_pil_img
        else:
            # If not applying preprocessing, still ensure it's grayscale for Tesseract
            return Image.fromarray(cv_img_gray).convert('L')

    except Exception as e:
        print(f"Error during image preprocessing for {image_path}: {e}")
        raise ValueError(f"Could not preprocess image: {e}")


# --- Main OCR Processing Function ---
def process_image_file(
        file_path: str,
        settings: Dict[str, Any]
) -> Dict[str, Any]:
    ocr_language = settings.get("ocr_language", "eng")
    ocr_psm = settings.get("ocr_page_segmentation_mode", 3)
    ocr_oem = settings.get("ocr_engine_mode", 3)
    apply_preprocessing_setting = settings.get("ocr_apply_preprocessing", True)  # Corrected variable name
    deskew_setting = settings.get("ocr_deskew", True)
    char_whitelist = settings.get("ocr_char_whitelist")

    try:
        processed_pil_img = preprocess_image_for_ocr(  # Returns a Pillow image
            file_path,
            apply_preprocessing=apply_preprocessing_setting,  # Use the correct variable
            deskew_image_flag=deskew_setting  # Use the correct variable
        )

        tesseract_config = f"--oem {ocr_oem} --psm {ocr_psm}"
        if char_whitelist:
            tesseract_config += f" -c tessedit_char_whitelist={char_whitelist}"

        ocr_data_df = pytesseract.image_to_data(
            processed_pil_img,  # Pass the Pillow image
            lang=ocr_language,
            config=tesseract_config,
            output_type=pytesseract.Output.DATAFRAME  # type: ignore
        )
        ocr_data_df = ocr_data_df[ocr_data_df.conf != -1].copy()  # Use .copy() to avoid SettingWithCopyWarning

        # Ensure 'text' column is string type before attempting to join
        ocr_data_df['text'] = ocr_data_df['text'].astype(str)
        extracted_text = " ".join(ocr_data_df['text'].tolist()).strip()

        word_level_details = []
        for _, row in ocr_data_df.iterrows():  # Iterate rows correctly
            if pd.notna(row['text']) and str(row['text']).strip():
                word_level_details.append({
                    "text": str(row['text']),
                    "confidence": float(row['conf']),
                    "left": int(row['left']),
                    "top": int(row['top']),
                    "width": int(row['width']),
                    "height": int(row['height'])
                })

        return {
            "extracted_text": extracted_text,
            "word_level_details": word_level_details,
            "tables_data": [],
            "source_basename": os.path.basename(file_path),
            "ocr_settings_used": {
                "language": ocr_language,
                "page_segmentation_mode": ocr_psm,
                "engine_mode": ocr_oem,
                "preprocessing_applied": apply_preprocessing_setting,  # Corrected variable
                "deskew_applied": deskew_setting and apply_preprocessing_setting,  # Corrected variable
                "char_whitelist": char_whitelist
            }
        }

    except pytesseract.TesseractNotFoundError:
        error_message = "Tesseract OCR engine not found. Please ensure Tesseract is installed and in your PATH."
        print(error_message)
        raise ValueError(error_message)
    except Exception as e:
        error_message = f"Error processing image file {file_path} with Tesseract: {type(e).__name__} - {str(e)}"
        print(error_message)
        # Reraise the original exception to get full traceback if needed, or keep ValueError
        # raise # Reraises the caught exception e
        raise ValueError(error_message)  # Wrap in ValueError as per existing code


# Example usage (for direct testing)
if __name__ == '__main__':
    sample_image_path = "sample_image.png"
    if not os.path.exists(sample_image_path):
        try:
            from PIL import Image, ImageDraw, ImageFont

            img = Image.new('RGB', (800, 300), color=(220, 220, 220))
            d = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("arial.ttf", 30)
            except IOError:
                font = ImageFont.load_default()
            d.text((20, 20), "Hello World from Pillow!\nThis is line two.\nAnd a third line for Tesseract.",
                   fill=(30, 30, 30), font=font)
            # Add a slight skew for testing deskew
            img = img.rotate(2, expand=True, fillcolor=(220, 220, 220))
            img.save(sample_image_path)
            print(f"Created dummy '{sample_image_path}' for testing.")
        except Exception as e:
            print(f"Could not create dummy image: {e}")

    if os.path.exists(sample_image_path):
        test_settings = {
            "ocr_language": "eng",
            "ocr_page_segmentation_mode": 3,
            "ocr_engine_mode": 3,
            "ocr_apply_preprocessing": True,
            "ocr_deskew": True,
            "ocr_char_whitelist": None,
        }
        try:
            result = process_image_file(sample_image_path, test_settings)
            print("\n--- OCR Result ---")
            print(f"Extracted Text: '{result['extracted_text']}'")
            if result.get('word_level_details'):
                print(f"Word Count: {len(result['word_level_details'])}")
                print("First 5 Word Details:")
                for item in result['word_level_details'][:5]:
                    print(item)
            # os.remove(sample_image_path) # Clean up
        except Exception as e:
            print(f"Error in example usage: {e}")
            import traceback

            traceback.print_exc()
    else:
        print(f"'{sample_image_path}' not found. Cannot run example.")