from docx import Document
from docx.document import Document as DocObject  # For type hinting
from docx.table import Table as TableObject
from docx.text.paragraph import Paragraph as ParagraphObject
from typing import Dict, List, Any, Union

# To inspect element types, we can use qn (qualified name) from docx.oxml.ns
from docx.oxml.ns import qn


def process_docx_file(file_path: str) -> Dict[str, Any]:
    """
    Processes a DOCX file to extract text with table placeholders and named table data.

    Args:
        file_path (str): The path to the .docx file.

    Returns:
        Dict[str, Any]: A dictionary containing:
                        - "text_with_placeholders": Extracted text with table placeholders.
                        - "named_tables": A dictionary of tables, e.g., {"table001": [[...], ...]}
    """
    try:
        document: DocObject = Document(file_path)

        text_parts: List[str] = []
        named_tables: Dict[str, List[List[str]]] = {}
        table_count = 0

        # Iterate through elements in the document body (paragraphs and tables in order)
        # doc.element.body contains all block-level content.
        for block_element in document.element.body:
            if block_element.tag == qn('w:p'):  # Paragraph
                para = ParagraphObject(block_element, document)
                text_parts.append(para.text)
            elif block_element.tag == qn('w:tbl'):  # Table
                table_count += 1
                table_id = f"table{table_count:03d}"  # Formats as table001, table002, etc.

                # ---- START DEBUG ----
                generated_placeholder = f"\n[[insert-{table_id}]]\n"
                print(f"DEBUG: Generating placeholder: '{generated_placeholder}' for table_id: {table_id}")  # Temporary debug print
                # ---- END DEBUG ----

                # Add placeholder to the text
                text_parts.append(generated_placeholder)  # Add newlines for better separation

                # Extract table data
                # We need to find the corresponding Table object in document.tables.
                # This is a bit tricky as python-docx doesn't directly link body elements to Table objects easily.
                # A common approach is to re-iterate document.tables and assume order,
                # or use a more complex mapping if available. For simplicity, if we assume
                # the iteration order of document.tables matches the order of w:tbl elements
                # in the body, we can use the current table_count (minus 1 for 0-indexing).
                # This assumption holds true for documents created linearly.
                if table_count <= len(document.tables):
                    table_object: TableObject = document.tables[table_count - 1]
                    current_table_data: List[List[str]] = []
                    for row in table_object.rows:
                        row_data = [cell.text for cell in row.cells]
                        current_table_data.append(row_data)
                    named_tables[table_id] = current_table_data
                else:
                    # This case should ideally not happen if table counting is correct
                    # Or it might indicate a table structure not parsed as expected
                    print(
                        f"Warning: Mismatch found between detected w:tbl elements and document.tables list for {table_id}")

        # Join all text parts, including placeholders
        text_with_placeholders = "\n".join(text_parts)
        # Replace multiple newlines that might have been introduced, with a single one, but keep double newlines for paragraphs
        text_with_placeholders = text_with_placeholders.replace('\n\n\n', '\n\n').strip()

        return {
            "text_with_placeholders": text_with_placeholders,
            "named_tables": named_tables,
            "source_filename": file_path  # Or os.path.basename(file_path)
        }

    except Exception as e:
        # Log the error appropriately in a real application
        error_message = f"Error processing DOCX file {file_path}: {str(e)}"
        print(error_message)  # Keep for now, replace with logging later
        # In a real API, you'd raise a specific HTTPException or return an error structure
        raise ValueError(error_message)


if __name__ == '__main__':
    import os
    # Example usage (for testing this module directly)
    # Create a dummy .docx file named "test_table_placeholders.docx"
    from docx import Document as CreateDoc

    test_doc_path = "test_table_placeholders.docx"
    test_doc = CreateDoc()
    test_doc.add_paragraph("This is the first paragraph.")
    test_doc.add_paragraph("Some text before the first table.")

    table1_data = [["H1T1", "H2T1"], ["R1C1T1", "R1C2T1"]]
    table1 = test_doc.add_table(rows=len(table1_data), cols=len(table1_data[0]))
    for i, row_vals in enumerate(table1_data):
        for j, cell_val in enumerate(row_vals):
            table1.cell(i, j).text = cell_val

    test_doc.add_paragraph("Some text between the two tables. This could be a long paragraph to see how text flows.")

    table2_data = [["Header A", "Header B"], ["Data 1A", "Data 1B"], ["Data 2A", "Data 2B"]]
    table2 = test_doc.add_table(rows=len(table2_data), cols=len(table2_data[0]))
    for i, row_vals in enumerate(table2_data):
        for j, cell_val in enumerate(row_vals):
            table2.cell(i, j).text = cell_val

    test_doc.add_paragraph("This is the last paragraph, after all tables.")
    test_doc.save(test_doc_path)

    try:
        result = process_docx_file(test_doc_path)
        print("\n--- Extracted Text with Placeholders ---")
        print(result["text_with_placeholders"])
        print("\n--- Named Tables ---")
        for table_id, table_content in result["named_tables"].items():
            print(f"\nTable ID: {table_id}")
            for row in table_content:
                print(row)
        os.remove(test_doc_path)  # Clean up test file
    except Exception as e:
        print(f"Error in example usage: {e}")