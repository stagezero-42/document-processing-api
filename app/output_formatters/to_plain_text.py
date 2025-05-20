# filename: app/output_formatters/to_plain_text.py
from typing import Dict, Any
from app.core.constants import SUPPORTED_IMAGE_EXTENSIONS # <-- IMPORT THE CONSTANT

def format_to_plain_text(processed_data: Dict[str, Any], source_type_hint: str) -> str:
    text_parts = []

    # REMOVE the local definition:
    # SUPPORTED_IMAGE_TYPES = ["png", "jpg", "jpeg", "tiff", "bmp", "webp"]

    if source_type_hint.lower() in SUPPORTED_IMAGE_EXTENSIONS: # <-- USE THE IMPORTED CONSTANT
        if "extracted_text" in processed_data:
            text_parts.append(processed_data["extracted_text"])
    else:
        # Original logic for DOCX/PDF
        # ... (rest of the logic remains the same) ...
        if "text_with_placeholders" in processed_data:
            text_parts.append(processed_data["text_with_placeholders"])

        tables_list = processed_data.get("tables_data", [])
        if tables_list:
            text_parts.append("\n\n--- Referenced Table Data ---")
            for table_obj in sorted(tables_list, key=lambda x: x.get('position', x.get('id', ''))):
                table_id = table_obj.get('id', 'UnknownTable')
                headers = table_obj.get('headers', [])
                data_rows = table_obj.get('data', [])

                text_parts.append(f"\n--- {table_id} ---")
                if headers:
                    text_parts.append("\t".join(str(cell).strip() for cell in headers))
                for row in data_rows:
                    text_parts.append("\t".join(str(cell).strip() for cell in row))
                text_parts.append("")
    return "\n".join(text_parts).strip()