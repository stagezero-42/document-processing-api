# filename: app/processing/image_processor.py
import os
import re  # ADDED for parsing OSD output
from typing import Dict, Any, Optional, List
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import pytesseract  # type: ignore
import cv2  # type: ignore
import numpy as np  # type: ignore
import pandas as pd


# --- Preprocessing Functions ---
def deskew(image_cv: np.ndarray) -> np.ndarray:
    """Corrects minor skew in an OpenCV image."""
    try:
        # Ensure input is grayscale for angle calculation logic
        if len(image_cv.shape) == 3 and image_cv.shape[2] == 3:
            gray_for_angle = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
        elif len(image_cv.shape) == 3 and image_cv.shape[2] == 4:
            gray_for_angle = cv2.cvtColor(image_cv, cv2.COLOR_BGRA2GRAY)
        elif len(image_cv.shape) == 2:
            gray_for_angle = image_cv.copy()  # Work on a copy if already gray
        else:
            print("Warning: Deskew input image has unexpected shape for angle calculation. Attempting to proceed.")
            gray_for_angle = image_cv  # Or raise an error if not 2D/3D

        # Invert colors for edge detection; this helps find text contours
        # For Otsu's, often the original gray works well too.
        # This inversion is for the coordinate finding part.
        gray_inverted_for_coords = cv2.bitwise_not(gray_for_angle)
        thresh = cv2.threshold(gray_inverted_for_coords, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

        coords = np.column_stack(np.where(thresh > 0))
        if coords.size == 0:
            print("Warning: No content found for deskewing after thresholding. Skipping deskew.")
            return image_cv

        angle = cv2.minAreaRect(coords)[-1]

        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        # If angle is very close to 0, skip rotation to save processing and avoid minor artifacts
        if abs(angle) < 0.1:  # Tolerance for "no skew"
            print(f"DEBUG: Deskew angle {angle:.2f} is close to 0. Skipping rotation.")
            return image_cv

        print(f"DEBUG: Deskewing by angle: {angle:.2f}")
        (h, w) = image_cv.shape[:2]  # Use original image shape for rotation center and output size
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        # Rotate the original input image_cv (which could be color or gray)
        rotated = cv2.warpAffine(image_cv, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated
    except Exception as e:
        print(f"Error during deskewing: {e}. Returning original image.")
        traceback.print_exc()  # ADDED: print full traceback for deskew errors
        return image_cv


def preprocess_image_for_ocr(
        image_path: str,
        apply_preprocessing: bool = True,
        deskew_image_flag: bool = True,
        target_dpi: int = 300  # target_dpi not fully implemented for resizing yet
) -> Image.Image:
    """
    Loads an image, attempts to correct major orientation issues (90/180/270 deg rotations),
    then applies optional standard preprocessing steps like deskewing and binarization.
    Returns a Pillow Image optimized for OCR.
    """
    try:
        pil_img = Image.open(image_path)

        # --- ADDED: Coarse Orientation Detection and Correction using Tesseract OSD ---
        try:
            print(f"DEBUG: Attempting OSD for {image_path}")
            # PSM 0 is for OSD only, should be relatively fast. Timeout to prevent indefinite hang.
            osd_data = pytesseract.image_to_osd(pil_img, config='--psm 0 -c tesseract_char_blacklist=[]', timeout=15)
            rotation_angle_osd = 0

            # Example OSD output: "Rotate: 90"
            match = re.search(r"Rotate:\s*(\d+)", osd_data)  # Handle potential space after Rotate:
            if match:
                rotation_angle_osd = int(match.group(1))

            print(f"DEBUG: Detected OSD rotation angle: {rotation_angle_osd} for {image_path}")

            if rotation_angle_osd == 90:
                pil_img = pil_img.rotate(270, expand=True)  # Pillow rotates counter-clockwise
                print(f"DEBUG: Applied 270-degree rotation to correct OSD 90 for {image_path}")
            elif rotation_angle_osd == 180:
                pil_img = pil_img.rotate(180, expand=True)
                print(f"DEBUG: Applied 180-degree rotation to correct OSD 180 for {image_path}")
            elif rotation_angle_osd == 270:
                pil_img = pil_img.rotate(90, expand=True)  # Pillow rotates counter-clockwise
                print(f"DEBUG: Applied 90-degree rotation to correct OSD 270 for {image_path}")
            # Else (rotation_angle_osd is 0 or not found), no coarse rotation needed from OSD.

        except RuntimeError as rterr:  # Catch Tesseract-specific runtime errors (e.g. not initialized)
            print(
                f"Warning: Tesseract OSD Runtime error for {image_path}: {rterr}. Proceeding without OSD-based rotation.")
        except Exception as osd_error:  # Catch other potential errors during OSD
            print(
                f"Warning: OSD detection failed or timed out for {image_path}: {osd_error}. Proceeding without OSD-based rotation.")
        # --- END: Coarse Orientation Detection and Correction ---

        # Convert (potentially rotated) Pillow image to OpenCV format
        # Always convert to RGB first, then to BGR for OpenCV consistency
        if pil_img.mode == 'RGBA':  # Handle RGBA images by converting to RGB (discard alpha)
            pil_img = pil_img.convert('RGB')
        elif pil_img.mode == 'P':  # Handle palette images by converting to RGB
            pil_img = pil_img.convert('RGB')
        elif pil_img.mode == 'L' or pil_img.mode == '1':  # If grayscale or binary, convert to RGB for consistent cv_img_bgr
            pil_img = pil_img.convert('RGB')

        cv_img_bgr = np.array(pil_img)  # Default conversion from RGB Pillow to NumPy is RGB
        cv_img_bgr = cv2.cvtColor(cv_img_bgr, cv2.COLOR_RGB2BGR)  # Explicitly convert to BGR

        # Initial conversion to grayscale for further operations if needed by them
        cv_img_gray = cv2.cvtColor(cv_img_bgr, cv2.COLOR_BGR2GRAY)

        # Start with a copy of the grayscale image for conditional preprocessing
        processed_cv_img = cv_img_gray.copy()

        if apply_preprocessing:
            # Fine Deskewing (operates on the potentially OSD-corrected image)
            if deskew_image_flag:
                print(f"DEBUG: Applying fine deskewing for {image_path}")
                # Pass the BGR image to deskew, let deskew handle its internal grayscale conversion for angle calculation
                # but it will rotate the original BGR image.
                deskewed_cv_img_output = deskew(cv_img_bgr.copy())  # deskew takes and returns same type (color or gray)

                # Ensure processed_cv_img is grayscale for subsequent binarization
                if len(deskewed_cv_img_output.shape) == 3:  # if deskew returned color
                    processed_cv_img = cv2.cvtColor(deskewed_cv_img_output, cv2.COLOR_BGR2GRAY)
                else:  # deskew returned grayscale
                    processed_cv_img = deskewed_cv_img_output
            else:
                print(f"DEBUG: Fine deskewing skipped for {image_path}")
                # If not deskewing, processed_cv_img is still the cv_img_gray from after OSD

            # Binarization (Otsu's method) - applied on the (potentially OSD-corrected AND deskewed) grayscale image
            print(f"DEBUG: Applying binarization for {image_path}")
            _, binary_cv_img = cv2.threshold(processed_cv_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Convert the final processed OpenCV image (binary) back to Pillow Image
            final_pil_img = Image.fromarray(binary_cv_img).convert(
                'L')  # Tesseract prefers L (grayscale) or RGB. '1' can work but L is safer.
            # final_pil_img.save(os.path.join(os.path.dirname(image_path), "DEBUG_" + os.path.basename(image_path))) # Optional: for debugging preprocessed image
            return final_pil_img
        else:
            # If not applying any preprocessing (after OSD), return Pillow image in grayscale mode
            print(f"DEBUG: All preprocessing skipped for {image_path} (after OSD attempt). Returning as grayscale PIL.")
            return Image.fromarray(cv_img_gray).convert('L')

    except Exception as e:
        print(f"FATAL Error during image preprocessing for {image_path}: {e}")
        import traceback
        traceback.print_exc()
        raise ValueError(f"Could not preprocess image '{os.path.basename(image_path)}': {e}")


# --- Main OCR Processing Function ---
def process_image_file(
        file_path: str,
        settings: Dict[str, Any]
) -> Dict[str, Any]:
    ocr_language = settings.get("ocr_language", "eng")
    # MODIFIED: Default PSM to 1 for OSD and auto-seg, if OSD in preprocess_image_for_ocr is not enough
    # Or keep 3 if preprocess_image_for_ocr is expected to handle orientation.
    # Let's stick to user-provided or default 3 for now, assuming preprocess handles coarse rotation.
    ocr_psm = settings.get("ocr_page_segmentation_mode", 3)
    ocr_oem = settings.get("ocr_engine_mode", 3)
    apply_preprocessing_setting = settings.get("ocr_apply_preprocessing", True)
    deskew_setting = settings.get("ocr_deskew", True)  # This controls the fine deskew, not coarse OSD rotation
    char_whitelist = settings.get("ocr_char_whitelist")

    try:
        print(f"DEBUG: Starting image processing for: {file_path} with settings: {settings}")
        processed_pil_img = preprocess_image_for_ocr(
            file_path,
            apply_preprocessing=apply_preprocessing_setting,
            deskew_image_flag=deskew_setting
        )

        tesseract_config = f"--oem {ocr_oem} --psm {ocr_psm}"
        if char_whitelist:
            tesseract_config += f" -c tessedit_char_whitelist={char_whitelist}"

        print(f"DEBUG: Running Tesseract on processed image with config: '{tesseract_config}'")
        # Timeout for Tesseract data processing
        ocr_data_df = pytesseract.image_to_data(
            processed_pil_img,
            lang=ocr_language,
            config=tesseract_config,
            output_type=pytesseract.Output.DATAFRAME,  # type: ignore
            timeout=30  # Added timeout for image_to_data
        )
        ocr_data_df = ocr_data_df[ocr_data_df.conf != -1].copy()

        ocr_data_df['text'] = ocr_data_df['text'].astype(str)
        extracted_text = " ".join(ocr_data_df['text'].tolist()).strip()
        print(f"DEBUG: Tesseract extracted text (first 100 chars): '{extracted_text[:100]}'")

        word_level_details = []
        for _, row in ocr_data_df.iterrows():
            if pd.notna(row['text']) and str(row['text']).strip():  # Ensure text is not NaN and not just whitespace
                word_level_details.append({
                    "text": str(row['text']),
                    "confidence": float(row['conf']) if row['conf'] != -1 else 0.0,  # Handle -1 confidence
                    "left": int(row['left']),
                    "top": int(row['top']),
                    "width": int(row['width']),
                    "height": int(row['height'])
                })

        return {
            "extracted_text": extracted_text,
            "word_level_details": word_level_details,
            "tables_data": [],  # tables_data is the expected key for format_content_for_json_schema
            "source_basename": os.path.basename(file_path),
            "ocr_settings_used": {
                "language": ocr_language,
                "page_segmentation_mode": ocr_psm,
                "engine_mode": ocr_oem,
                "preprocessing_applied": apply_preprocessing_setting,
                "deskew_applied": deskew_setting and apply_preprocessing_setting,
                "char_whitelist": char_whitelist
            }
        }

    except pytesseract.TesseractNotFoundError:
        error_message = "Tesseract OCR engine not found. Please ensure Tesseract is installed and in your PATH."
        print(error_message)
        raise ValueError(error_message)  # Re-raise as ValueError for main.py to catch
    except RuntimeError as rterr:  # Catch other Tesseract runtime errors
        error_message = f"Tesseract runtime error processing image {os.path.basename(file_path)}: {rterr}"
        print(error_message)
        import traceback
        traceback.print_exc()
        raise ValueError(error_message)  # Re-raise as ValueError
    except Exception as e:
        error_message = f"Error processing image file {os.path.basename(file_path)} with Tesseract: {type(e).__name__} - {str(e)}"
        print(error_message)
        import traceback
        traceback.print_exc()
        raise ValueError(error_message)  # Re-raise as ValueError


# Example usage (for direct testing)
if __name__ == '__main__':
    # Create a dummy image for testing if it doesn't exist
    sample_image_path = "temp_test_ocr_image.png"  # Ensure this path is writable
    if not os.path.exists(sample_image_path):
        try:
            img = Image.new('RGB', (1200, 1800), color=(230, 230, 230))
            d = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("arial.ttf", 50)  # Check if arial.ttf is available or use default
            except IOError:
                font = ImageFont.load_default()

            text_to_draw = "This is a test sentence.\nAnother line for OCR.\nPage is upright."
            d.text((50, 100), text_to_draw, fill=(20, 20, 20), font=font)

            # For upside-down test:
            # img = img.rotate(180, expand=True)
            # d_rotated = ImageDraw.Draw(img)
            # d_rotated.text((50, 100), "This text is upside down.", fill=(20,20,20), font=font)

            img.save(sample_image_path)
            print(f"Created dummy '{sample_image_path}' for testing.")
        except Exception as e_create:
            print(f"Could not create dummy image: {e_create}")

    if os.path.exists(sample_image_path):
        test_settings = {
            "ocr_language": "eng",
            "ocr_page_segmentation_mode": 3,  # Try 1 if OSD is primarily desired at tesseract level
            "ocr_engine_mode": 3,
            "ocr_apply_preprocessing": True,
            "ocr_deskew": True,
            "ocr_char_whitelist": None,
        }
        try:
            print(f"\n--- Testing OCR with: {sample_image_path} ---")
            result = process_image_file(sample_image_path, test_settings)
            print("\n--- OCR Result ---")
            print(f"Extracted Text: '{result['extracted_text']}'")
            # if result.get('word_level_details'):
            #     print(f"Word Count: {len(result['word_level_details'])}")
            #     print("First 5 Word Details:")
            #     for item in result['word_level_details'][:5]:
            #         print(item)
            # os.remove(sample_image_path) # Clean up temp test image
        except Exception as e_test:
            print(f"Error in example OCR usage: {e_test}")
            import traceback

            traceback.print_exc()
    else:
        print(f"'{sample_image_path}' not found. Cannot run example.")