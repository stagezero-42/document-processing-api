from typing import Dict, Any


def format_to_plain_text(processed_data: Dict[str, Any]) -> str:
    """
    Formats the processed document data into a single plain text string.
    This will primarily be the text with placeholders. Table data can be appended.

    Args:
        processed_data (Dict[str, Any]): The dictionary from the document processor.
                                         Expected keys: "text_with_placeholders", "named_tables".

    Returns:
        str: A plain text representation.
    """
    text_parts = []

    if "text_with_placeholders" in processed_data:
        text_parts.append(processed_data["text_with_placeholders"])

    named_tables = processed_data.get("named_tables", {})
    if named_tables:
        text_parts.append("\n\n--- Referenced Table Data ---")
        for table_id, table_data in sorted(named_tables.items()):  # Sort for consistent output
            text_parts.append(f"\n--- {table_id} ---")
            for row in table_data:
                text_parts.append("\t".join(str(cell).strip() for cell in row))  # .strip() cell text
            text_parts.append("")  # Empty line after each table

    return "\n".join(text_parts).strip()