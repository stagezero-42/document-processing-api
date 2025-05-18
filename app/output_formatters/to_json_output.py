from typing import Dict, Any

def format_to_json_structure(processed_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formats the processed document data (text with placeholders and named tables)
    into a structured JSON-friendly dictionary.

    Args:
        processed_data (Dict[str, Any]): The dictionary from the document processor.
                                         Expected keys: "text_with_placeholders", "named_tables".

    Returns:
        Dict[str, Any]: A dictionary suitable for JSON serialization.
    """
    output = {
        "extracted_text_with_placeholders": processed_data.get("text_with_placeholders", ""),
        "tables": processed_data.get("named_tables", {}) # Key changed to "tables" for the output JSON
        # You can add other metadata here if needed
        # "metadata": {
        #     "source_filename": processed_data.get("source_filename", "unknown")
        # }
    }
    return output