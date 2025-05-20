# filename: app/processing/image_processor.py
import os
import re
import traceback
from typing import Dict, Any, Optional, List
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import pytesseract  # type: ignore
import cv2  # type: ignore
import numpy as np  # type: ignore
import pandas as pd


# --- Preprocessing Functions ---
def deskew(image_cv: np.ndarray) -> np.ndarray:
    """Corrects minor skew in an OpenCV image. Skips if angle is too large."""
    try:
        gray_for_angle = None
        if len(image_cv.shape) == 3 and image_cv.shape[2] == 3:  # BGR
            gray_for_angle = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
        elif len(image_cv.shape) == 3 and image_cv.shape[2] == 4:  # BGRA
            gray_for_angle = cv2.cvtColor(image_cv, cv2.COLOR_BGRA2GRAY)
        elif len(image_cv.shape) == 2:  # Already grayscale
            gray_for_angle = image_cv.copy()
        else:
            print("Warning: Deskew input image has unexpected shape for angle calculation. Skipping deskew.")
            return image_cv

        gray_inverted_for_coords = cv2.bitwise_not(gray_for_angle)
        thresh = cv2.threshold(gray_inverted_for_coords, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

        coords = np.column_stack(np.where(thresh > 0))
        if coords.size == 0:
            print("Warning: No content found for deskewing after thresholding. Skipping deskew.")
            return image_cv

        angle = cv2.minAreaRect(coords)[-1]

        if angle < -45:
            angle += 90

        MAX_FINE_SKEW_ANGLE = 25.0
        MIN_FINE_SKEW_ANGLE_TO_CORRECT = 0.1

        if abs(angle) < MIN_FINE_SKEW_ANGLE_TO_CORRECT:
            print(f"DEBUG: Fine deskew angle {angle:.2f} is too small. Skipping fine deskew rotation.")
            return image_cv
        elif abs(angle) > MAX_FINE_SKEW_ANGLE:
            print(
                f"DEBUG: Fine deskew angle {angle:.2f} is too large (>{MAX_FINE_SKEW_ANGLE}). Assuming OSD handled major rotation. Skipping fine deskew.")
            return image_cv

        print(f"DEBUG: Applying fine deskewing rotation by angle: {angle:.2f} degrees.")
        (h, w) = image_cv.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image_cv, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated
    except Exception as e:
        print(f"Error during deskewing: {e}. Returning original image.")
        traceback.print_exc()
        return image_cv


def preprocess_image_for_ocr(
        image_path: str,
        apply_preprocessing: bool = True,
        deskew_image_flag: bool = True,
        target_dpi: int = 300
) -> Image.Image:
    try:
        pil_img_original = Image.open(image_path)
        pil_img = pil_img_original.copy()

        # --- OSD and Coarse Rotation ---
        try:
            print(f"DEBUG: Attempting OSD for {image_path}")
            osd_data = pytesseract.image_to_osd(pil_img, config='--psm 0 -c tesseract_char_blacklist=[]', timeout=15)
            rotation_angle_osd = 0
            match = re.search(r"Rotate:\s*(\d+)", osd_data)
            if match: rotation_angle_osd = int(match.group(1))
            print(f"DEBUG: Detected OSD rotation angle: {rotation_angle_osd} for {image_path}")

            if rotation_angle_osd == 90:
                pil_img = pil_img.rotate(270, expand=True)
            elif rotation_angle_osd == 180:
                pil_img = pil_img.rotate(180, expand=True)
            elif rotation_angle_osd == 270:
                pil_img = pil_img.rotate(90, expand=True)
            if rotation_angle_osd != 0 and rotation_angle_osd in [90, 180, 270]:  # Check if actual rotation happened
                print(f"DEBUG: Applied coarse rotation for OSD {rotation_angle_osd} for {image_path}")
        except Exception as osd_error:
            print(
                f"Warning: OSD detection/rotation failed for {image_path}: {osd_error}. Proceeding without OSD-based coarse rotation.")
            pil_img = pil_img_original.copy()

            # --- Convert to OpenCV format (BGR) ---
        if pil_img.mode == 'RGBA':
            pil_img = pil_img.convert('RGB')
        elif pil_img.mode == 'P':
            pil_img = pil_img.convert('RGB')
        elif pil_img.mode == 'L' or pil_img.mode == '1':
            pil_img = pil_img.convert('RGB')

        cv_img_bgr_after_osd = np.array(pil_img)
        cv_img_bgr_after_osd = cv2.cvtColor(cv_img_bgr_after_osd, cv2.COLOR_RGB2BGR)
        processed_cv_img_for_binarization = cv2.cvtColor(cv_img_bgr_after_osd, cv2.COLOR_BGR2GRAY)

        debug_dir = os.path.join(os.path.dirname(image_path), "DEBUG_IMAGES")
        if not os.path.exists(debug_dir): os.makedirs(debug_dir)
        try:
            img_after_osd_path = os.path.join(debug_dir, "OSD_ROTATED_" + os.path.basename(image_path))
            Image.fromarray(cv2.cvtColor(cv_img_bgr_after_osd, cv2.COLOR_BGR2RGB)).save(img_after_osd_path)
            print(f"DEBUG: Saved image AFTER OSD rotation to {img_after_osd_path}")
        except Exception as e_save_osd:
            print(f"DEBUG: Failed to save OSD_ROTATED_ debug image: {e_save_osd}")

        if apply_preprocessing:
            current_img_for_deskew = cv_img_bgr_after_osd.copy()
            if deskew_image_flag:
                print(f"DEBUG: Applying fine deskewing for {image_path}")
                deskewed_cv_img_output = deskew(current_img_for_deskew)
                if len(deskewed_cv_img_output.shape) == 3:
                    processed_cv_img_for_binarization = cv2.cvtColor(deskewed_cv_img_output, cv2.COLOR_BGR2GRAY)
                else:
                    processed_cv_img_for_binarization = deskewed_cv_img_output
            else:
                print(f"DEBUG: Fine deskewing skipped for {image_path}")

            try:
                img_after_deskew_path = os.path.join(debug_dir, "PRE_BINARIZE_" + os.path.basename(image_path))
                Image.fromarray(processed_cv_img_for_binarization).save(img_after_deskew_path)
                print(f"DEBUG: Saved image BEFORE binarization (after deskew) to {img_after_deskew_path}")
            except Exception as e_save_pre_bin:
                print(f"DEBUG: Failed to save PRE_BINARIZE_ debug image: {e_save_pre_bin}")

            # --- MODIFIED: Reverted Binarization to Global Otsu's Thresholding ---
            print(f"DEBUG: Applying Global Otsu's thresholding for {image_path}")
            _, binary_cv_img = cv2.threshold(
                processed_cv_img_for_binarization,
                0,  # Threshold value ignored due to THRESH_OTSU
                255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
            print(f"DEBUG: Global Otsu's thresholding applied for {image_path}")
            # --- End of Binarization Modification ---

            final_pil_img = Image.fromarray(binary_cv_img).convert('L')

            try:
                final_debug_img_path = os.path.join(debug_dir, "FINAL_FOR_TESSERACT_" + os.path.basename(image_path))
                final_pil_img.save(final_debug_img_path)
                print(f"DEBUG: Saved FINAL preprocessed image for Tesseract to {final_debug_img_path}")
            except Exception as e_save_final:
                print(f"DEBUG: Failed to save FINAL_FOR_TESSERACT_ debug image: {e_save_final}")

            return final_pil_img
        else:
            print(
                f"DEBUG: Preprocessing (deskew/binarize) skipped for {image_path}. Returning OSD-rotated grayscale PIL.")
            return Image.fromarray(processed_cv_img_for_binarization).convert('L')

    except Exception as e:
        print(f"FATAL Error during image preprocessing for {image_path}: {e}")
        traceback.print_exc()
        raise ValueError(f"Could not preprocess image '{os.path.basename(image_path)}': {e}")


# --- Main OCR Processing Function (remains the same) ---
def process_image_file(
        file_path: str,
        settings: Dict[str, Any]
) -> Dict[str, Any]:
    ocr_language = settings.get("ocr_language", "eng")
    ocr_psm = settings.get("ocr_page_segmentation_mode", 3)
    ocr_oem = settings.get("ocr_engine_mode", 3)
    apply_preprocessing_setting = settings.get("ocr_apply_preprocessing", True)
    deskew_setting = settings.get("ocr_deskew", True)
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
        ocr_data_df = pytesseract.image_to_data(
            processed_pil_img,
            lang=ocr_language,
            config=tesseract_config,
            output_type=pytesseract.Output.DATAFRAME,
            timeout=30
        )
        ocr_data_df = ocr_data_df[ocr_data_df.conf != -1].copy()

        ocr_data_df['text'] = ocr_data_df['text'].astype(str)
        extracted_text = " ".join(ocr_data_df['text'].tolist()).strip()
        print(f"DEBUG: Tesseract extracted text (first 100 chars): '{extracted_text[:100]}'")

        word_level_details = []
        for _, row in ocr_data_df.iterrows():
            if pd.notna(row['text']) and str(row['text']).strip():
                word_level_details.append({
                    "text": str(row['text']),
                    "confidence": float(row['conf']) if row['conf'] != -1 else 0.0,
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
                "preprocessing_applied": apply_preprocessing_setting,
                "deskew_applied": deskew_setting and apply_preprocessing_setting,
                "char_whitelist": char_whitelist
            }
        }
    except pytesseract.TesseractNotFoundError:
        error_message = "Tesseract OCR engine not found. Please ensure Tesseract is installed and in your PATH."
        print(error_message);
        raise ValueError(error_message)
    except RuntimeError as rterr:
        error_message = f"Tesseract runtime error processing image {os.path.basename(file_path)}: {rterr}"
        print(error_message);
        traceback.print_exc();
        raise ValueError(error_message)
    except Exception as e:
        error_message = f"Error processing image file {os.path.basename(file_path)} with Tesseract: {type(e).__name__} - {str(e)}"
        print(error_message);
        traceback.print_exc();
        raise ValueError(error_message)


# Example usage
if __name__ == '__main__':
    # (main block for local testing - kept for your convenience)
    sample_image_path = "temp_test_ocr_image.png"
    if not os.path.exists(sample_image_path):
        try:
            img = Image.new('RGB', (1700, 2200), color=(230, 230, 230))
            d = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("arial.ttf", 50)
            except IOError:
                font = ImageFont.load_default()
            text_block = ("This is Line 1 at the top.\n"
                          "Line 2, fairly clear.\n"
                          "Line 3 has some minor artifacts.\n"
                          "LINE 4 IS ALL CAPS AND BOLD.\n"
                          "Line 5. line six. line seven.\n"
                          "The quick brown fox jumps over the lazy dog.\n"
                          "0123456789 ABCDEFGHIJKLMNOPQRSTUVWXYZ\n"
                          "abcdefghijklmnopqrstuvwxyz .,!?()[]\n"
                          "This should be an upright image for testing.\n"
                          "And this is the very last line at the bottom.")
            d.text((100, 100), text_block, fill=(20, 20, 20), font=font)
            d.text((100, 2000), "This is the absolute final line near edge.", fill=(30, 30, 30), font=font)
            img.save(sample_image_path)
            print(f"Created dummy '{sample_image_path}' for testing.")
        except Exception as e_create:
            print(f"Could not create dummy image: {e_create}")

    if os.path.exists(sample_image_path):
        test_settings = {"ocr_apply_preprocessing": True, "ocr_deskew": True}
        try:
            print(f"\n--- Testing OCR with: {sample_image_path} ---")
            result = process_image_file(sample_image_path, test_settings)
            print("\n--- OCR Result ---");
            print(f"Extracted Text: '{result['extracted_text']}'")
        except Exception as e_test:
            print(f"Error in example OCR usage: {e_test}"); traceback.print_exc()
    else:
        print(f"'{sample_image_path}' not found. Cannot run example.")