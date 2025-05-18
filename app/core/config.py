import os

class Settings:
    PROJECT_NAME: str = "Document Processing API"
    PROJECT_VERSION: str = "0.1.0"
    # Add other configurations here as needed
    # Example: UPLOAD_DIRECTORY = "uploads" (defined in utils.py for now, can be moved here)

settings = Settings()

# Example of how you might load from environment variables:
# API_KEY: str = os.getenv("API_KEY", "default_api_key_for_dev")