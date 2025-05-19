from typing import Dict, Any

def format_content_for_json_schema(processed_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formats the processed document data into the 'content' part of the target JSON schema.

    Args:
        processed_data (Dict[str, Any]): The dictionary from the document processor.
                                         Expected keys: "text_with_placeholders", "tables_data".
                                         "tables_data" is a list of table objects.

    Returns:
        Dict[str, Any]: A dictionary representing the 'content' object.
    """
    content_object = {
        "extracted_text_with_placeholders": processed_data.get("text_with_placeholders", ""),
        "tables": processed_data.get("tables_data", []) # This is now the list of table objects
    }
    return content_object