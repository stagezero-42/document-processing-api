# filename: app/output_formatters/to_json_output.py
from typing import Dict, Any
from app.core.constants import SUPPORTED_IMAGE_EXTENSIONS


def format_content_for_json_schema(processed_data: Dict[str, Any], source_type_hint: str) -> Dict[str, Any]:
    # MODIFIED condition to correctly identify if an OCR-like structure is needed
    is_ocr_structure_needed = source_type_hint.lower() in SUPPORTED_IMAGE_EXTENSIONS \
                              or source_type_hint.lower() == "image"

    if is_ocr_structure_needed:
        # This structure is for OCRContent
        content_object = {
            "extracted_text": processed_data.get("extracted_text", ""),
            "ocr_settings_used": processed_data.get("ocr_settings_used", {}),
            "word_level_details": processed_data.get("word_level_details", []),
            "tables": processed_data.get("tables_data", [])  # 'tables_data' from processor, 'tables' in Pydantic model
        }
    else:
        # This structure is for DocumentContent (e.g., direct PDF, DOCX)
        content_object = {
            "extracted_text_with_placeholders": processed_data.get("text_with_placeholders", ""),
            "tables": processed_data.get("tables_data", [])  # 'tables_data' from processor, 'tables' in Pydantic model
        }
    return content_object