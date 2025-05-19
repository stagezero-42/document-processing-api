import fitz  # PyMuPDF
import os
from typing import Dict, List, Any, Optional

INTERNAL_DEFAULT_PDF_TABLE_STRATEGY = "lines_strict"
DEFAULT_PDF_TEXT_TOLERANCE = 3


def process_pdf_file(file_path: str, settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if settings is None:
        settings = {}

    # Get settings from API call, or use internal defaults for this processor
    # The API 'main.py' now defaults pdf_table_strategy to "lines_strict"
    # So settings.get("table_strategy") will usually be "lines_strict" if not specified by client
    table_strategy_api_value = settings.get("table_strategy", INTERNAL_DEFAULT_PDF_TABLE_STRATEGY)

    text_tolerance_setting = settings.get("text_tolerance")
    remove_empty_rows_setting = settings.get("remove_empty_rows", False)

    try:
        doc = fitz.open(file_path)
        # ... (tables_data_list, table_count_in_doc, full_page_text_with_placeholders_parts setup) ...
        tables_data_list: List[Dict[str, Any]] = []
        table_count_in_doc = 0
        full_page_text_with_placeholders_parts = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text_blocks = page.get_text("blocks", sort=True)

            find_tables_options = {}

            # Interpret the strategy from API
            if table_strategy_api_value == "pymupdf_default":
                # Don't pass any strategy, let PyMuPDF use its library default
                pass
            elif table_strategy_api_value in ["text", "lines", "lines_strict"]:
                find_tables_options["strategy"] = table_strategy_api_value
            else:  # Fallback to our internal default if an unexpected value somehow gets here
                find_tables_options["strategy"] = INTERNAL_DEFAULT_PDF_TABLE_STRATEGY

            # Apply text_tolerance only if the strategy is 'text' (or if it's generally applicable)
            # PyMuPDF's text_tolerance is mainly for 'text' strategy but might not hurt others if set.
            if text_tolerance_setting is not None:
                # Ensure it's an int for PyMuPDF
                find_tables_options["text_tolerance"] = int(text_tolerance_setting)

            print(f"DEBUG: PyMuPDF find_tables options for page {page_num}: {find_tables_options}")
            table_finder = page.find_tables(**find_tables_options)

            # ... (rest of the PDF processing logic for elements, text, tables, and rows remains the same as before) ...
            # ... (ensure the post-processing for remove_empty_rows is still there) ...
            page_elements = []
            for x0, y0, x1, y1, text_content, block_no, block_type in text_blocks:
                if block_type == 0:
                    page_elements.append({
                        "type": "text", "bbox": (x0, y0, x1, y1),
                        "content": text_content.strip(), "y_start": y0
                    })

            current_page_table_index = 0
            for fitz_table_obj in table_finder:
                table_count_in_doc += 1
                table_id = f"table{table_count_in_doc:03d}"
                page_elements.append({
                    "type": "table_placeholder", "bbox": fitz_table_obj.bbox,
                    "id": table_id, "fitz_table_obj": fitz_table_obj,
                    "y_start": fitz_table_obj.bbox[1], "page_table_index": current_page_table_index
                })
                current_page_table_index += 1

            page_elements.sort(key=lambda el: (el["y_start"], el["bbox"][0]))

            current_page_text_parts = []
            for element in page_elements:
                if element["type"] == "text":
                    if element["content"]:
                        current_page_text_parts.append(element["content"])
                elif element["type"] == "table_placeholder":
                    table_id = element["id"]
                    fitz_table_obj = element["fitz_table_obj"]
                    current_page_text_parts.append(f"\n[[INSERT_TABLE:{table_id}]]\n")

                    raw_extracted_rows: List[List[str | None]] = fitz_table_obj.extract() or []

                    processed_rows = [[str(cell) if cell is not None else "" for cell in r_row] for r_row in
                                      raw_extracted_rows]

                    if remove_empty_rows_setting:
                        processed_rows = [row for row in processed_rows if any(cell.strip() for cell in row)]

                    table_headers: List[str] = []
                    table_actual_data: List[List[str]] = []
                    if processed_rows:
                        table_headers = processed_rows[0]
                        table_actual_data = processed_rows[1:]

                    table_detail = {
                        "id": table_id, "position": len(tables_data_list) + 1,
                        "caption": None, "headers": table_headers, "data": table_actual_data,
                        "page_number": page_num + 1
                    }
                    tables_data_list.append(table_detail)

            if current_page_text_parts:
                full_page_text_with_placeholders_parts.append("\n".join(current_page_text_parts))

        final_text = "\n\n".join(full_page_text_with_placeholders_parts)
        final_text = final_text.replace('\n\n\n', '\n\n').strip()

        return {
            "text_with_placeholders": final_text,
            "tables_data": tables_data_list,
            "source_basename": os.path.basename(file_path)
        }

    # ... (exception handling) ...
    except fitz.fitz.FileNotFoundError as fnfe:
        error_message = f"Error processing PDF file {file_path}: File not found. ({str(fnfe)})"
        print(error_message)
        raise ValueError(error_message)
    except Exception as e:
        error_message = f"Error processing PDF file {file_path}: {type(e).__name__} - {str(e)}"
        print(error_message)
        raise ValueError(error_message)

# Remove or comment out the __main__ block for this file if not being used for direct testing.