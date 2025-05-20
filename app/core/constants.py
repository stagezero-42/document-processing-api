# filename: app/core/constants.py

# Define supported image types for OCR and general image processing
# This list should be the single source of truth for supported image extensions.
SUPPORTED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp"}
# Using a set for efficient "in" checks. Extensions are lowercased.

# You can add other constants here as your project grows.
# Example:
# SUPPORTED_DOCUMENT_EXTENSIONS = {"pdf", "docx"}
# ALL_SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS.union(SUPPORTED_DOCUMENT_EXTENSIONS)