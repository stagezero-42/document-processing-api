from typing import Dict, Any


def format_to_plain_text(processed_data: Dict[str, Any]) -> str:
    """
    Formats the processed document data into a single plain text string.
    This will primarily be the text with placeholders. Table data is appended.

    Args:
        processed_data (Dict[str, Any]): The dictionary from the document processor.
                                         Expected keys: "text_with_placeholders", "tables_data".
                                         "tables_data" is a list of table objects, where each
                                         object has "id", "headers", and "data".

    Returns:
        str: A plain text representation.
    """
    text_parts = []

    # Append the main text with placeholders
    if "text_with_placeholders" in processed_data:
        text_parts.append(processed_data["text_with_placeholders"])

    # Get the list of table objects from the processed_data
    # The key from docx_processor is "tables_data"
    tables_list = processed_data.get("tables_data", [])

    # Check if there are any tables to append
    if tables_list:  # This condition checks if the list is not empty
        text_parts.append("\n\n--- Referenced Table Data ---")  # This is the missing string

        # Sort by table position or ID for consistent output order in the text file
        # Assuming 'position' key exists as per the schema, otherwise sort by 'id'
        for table_obj in sorted(tables_list, key=lambda x: x.get('position', x.get('id', ''))):
            table_id = table_obj.get('id', 'UnknownTable')
            headers = table_obj.get('headers', [])
            data_rows = table_obj.get('data', [])

            text_parts.append(f"\n--- {table_id} ---")  # Append table ID header

            if headers:  # Append headers if they exist
                text_parts.append("\t".join(str(cell).strip() for cell in headers))

            for row in data_rows:  # Append data rows
                text_parts.append("\t".join(str(cell).strip() for cell in row))

            text_parts.append("")  # Add an empty line after each table's data for readability

    return "\n".join(text_parts).strip()