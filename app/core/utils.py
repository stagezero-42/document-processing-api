import os

# Define a directory to store uploaded files temporarily
# In a production environment, you might want this to be configurable
# and ensure proper permissions and cleanup strategies.
UPLOAD_DIRECTORY = "temp_uploads"

def get_file_extension(filename: str) -> str:
    """
    Extracts the file extension from a filename.
    Returns an empty string if no extension is found.
    """
    if "." in filename:
        return filename.rsplit('.', 1)[1].lower()
    return ""

# You can add more utility functions here as the project grows, for example:
# - More robust file type detection (e.g., using `python-magic`)
# - Filename sanitization functions
# - Common data transformation utilities