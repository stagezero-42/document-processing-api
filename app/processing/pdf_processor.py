import fitz  # PyMuPDF
import os
from typing import Dict, List, Any, Tuple


def process_pdf_file(file_path: str) -> Dict[str, Any]:
    """
    Processes a text-based PDF file to extract text with table placeholders
    and a list of table objects.

    Args:
        file_path (str): The path to the .pdf file.

    Returns:
        Dict[str, Any]: A dictionary containing:
                        - "text_with_placeholders": Extracted text with table placeholders.
                        - "tables_data": A list of table objects, each with id, position,
                                         caption (None for now), headers, and data.
                        - "source_basename": Basename of the source file.
    """
    try:
        doc = fitz.open(file_path)

        text_parts: List[str] = []
        tables_data_list: List[Dict[str, Any]] = []
        table_count = 0

        full_page_text_with_placeholders = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)

            # Get text blocks with coordinates: (x0, y0, x1, y1, "text", block_no, block_type)
            # block_type = 0 for text, 1 for image
            text_blocks = page.get_text("blocks", sort=True)  # Sort by y-coordinate then x

            # Find tables on the page
            # page.find_tables() returns a TableFinder object
            # We can configure strategies, e.g., table_finder.settings.strategy = "lines" or "text"
            table_finder = page.find_tables()  # Default strategy often works for simple tables

            page_elements = []  # To store both text blocks and table references with y-coord

            # Add text blocks to elements list
            for x0, y0, x1, y1, text_content, block_no, block_type in text_blocks:
                if block_type == 0:  # It's a text block
                    page_elements.append({
                        "type": "text",
                        "bbox": (x0, y0, x1, y1),
                        "content": text_content.strip(),  # Strip leading/trailing whitespace from block
                        "y_start": y0
                    })

            # Add table references to elements list
            for i, fitz_table in enumerate(table_finder):
                # fitz_table is a fitz.table.Table object
                table_count += 1  # Global table count across pages
                table_id = f"table{table_count:03d}"
                page_elements.append({
                    "type": "table_placeholder",
                    "bbox": fitz_table.bbox,  # (x0, y0, x1, y1) tuple
                    "id": table_id,
                    "fitz_table_obj": fitz_table,  # Store the object for later extraction
                    "y_start": fitz_table.bbox[1]
                })

            # Sort all elements on the page by their starting y-coordinate, then x-coordinate
            # (though get_text("blocks", sort=True) already sorts text blocks)
            # This interleaving is crucial.
            page_elements.sort(key=lambda el: (el["y_start"], el["bbox"][0]))

            current_page_text_parts = []
            for element in page_elements:
                if element["type"] == "text":
                    if element["content"]:  # Add non-empty text blocks
                        current_page_text_parts.append(element["content"])
                elif element["type"] == "table_placeholder":
                    table_id = element["id"]
                    fitz_table_obj = element["fitz_table_obj"]

                    current_page_text_parts.append(f"\n[[INSERT_TABLE:{table_id}]]\n")

                    # Extract table data from the fitz.table.Table object
                    # fitz_table_obj.extract() gives list of lists (all rows)
                    extracted_rows: List[List[str]] = fitz_table_obj.extract() or []

                    table_headers: List[str] = []
                    table_actual_data: List[List[Any]] = []  # Allow for numbers if detected

                    if extracted_rows:
                        # Assume first row is headers, convert all to string for consistency
                        table_headers = [str(cell) if cell is not None else "" for cell in extracted_rows[0]]
                        # Remaining rows are data, convert all to string
                        table_actual_data = [
                            [str(cell) if cell is not None else "" for cell in row]
                            for row in extracted_rows[1:]
                        ]

                    table_detail = {
                        "id": table_id,
                        "position": table_count,  # Overall position in document
                        "caption": None,  # PDF table captions are harder to detect reliably
                        "headers": table_headers,
                        "data": table_actual_data,
                        "page_number": page_num + 1  # Optional: add page number for table
                    }
                    tables_data_list.append(table_detail)

            if current_page_text_parts:
                full_page_text_with_placeholders.append("\n".join(current_page_text_parts))

        final_text = "\n\n".join(full_page_text_with_placeholders)  # Join pages with double newline
        final_text = final_text.replace('\n\n\n', '\n\n').strip()

        return {
            "text_with_placeholders": final_text,
            "tables_data": tables_data_list,
            "source_basename": os.path.basename(file_path)
        }

    except Exception as e:
        error_message = f"Error processing PDF file {file_path}: {str(e)}"
        print(error_message)  # Replace with logging
        raise ValueError(error_message)


if __name__ == '__main__':
    # Create a dummy PDF for testing (requires reportlab or similar, or use an existing PDF)
    # This is a placeholder for how you might test this module directly.
    # For actual testing, you'll use pytest with sample PDF files.
    print("pdf_processor.py - For direct testing, please use pytest with sample PDF files.")
    print("Example of creating a simple PDF with reportlab (if installed):")
    print("pip install reportlab")
    print("""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
    
        c = canvas.Canvas("test_pdf_processor.pdf", pagesize=letter)
        c.drawString(1*inch, 10*inch, "Page 1: Some text before a table.")
    
        # Simple table drawing (reportlab is more complex for full table structures)
        textobject = c.beginText(1*inch, 9.5*inch)
        textobject.textLine("Header A | Header B")
        textobject.textLine("Data 1A  | Data 1B")
        c.drawText(textobject)
    
        c.drawString(1*inch, 9*inch, "Some text after the table.")
        c.showPage()
        c.save()
        print("Created test_pdf_processor.pdf")
    
        results = process_pdf_file("test_pdf_processor.pdf")
        print("\\n--- TEXT ---")
        print(results['text_with_placeholders'])
        print("\\n--- TABLES ---")
        for tbl in results['tables_data']:
            print(tbl)
        if os.path.exists("test_pdf_processor.pdf"):
            os.remove("test_pdf_processor.pdf")
    except ImportError:
        print("reportlab not installed. Skipping direct PDF creation test.")
    except Exception as e:
        print(f"Error in __main__: {e}")
        """)