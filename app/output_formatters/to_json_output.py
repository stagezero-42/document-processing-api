# filename: app/output_formatters/to_json_output.py
from typing import Dict, Any
from app.core.constants import SUPPORTED_IMAGE_EXTENSIONS # <-- IMPORT THE CONSTANT

def format_content_for_json_schema(processed_data: Dict[str, Any], source_type_hint: str) -> Dict[str, Any]:
    # REMOVE the local definition:
    # SUPPORTED_IMAGE_TYPES = ["png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp"]

    if source_type_hint.lower() in SUPPORTED_IMAGE_EXTENSIONS: # <-- USE THE IMPORTED CONSTANT
        # Structure for OCR content
        content_object = {
            "extracted_text": processed_data.get("extracted_text", ""),
            "ocr_settings_used": processed_data.get("ocr_settings_used", {}),
            "word_level_details": processed_data.get("word_level_details", []),
            "tables": processed_data.get("tables_data", [])
        }
    else:
        # Original structure for DOCX/PDF content
        content_object = {
            "extracted_text_with_placeholders": processed_data.get("text_with_placeholders", ""),
            "tables": processed_data.get("tables_data", [])
        }
    return content_object