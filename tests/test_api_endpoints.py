import pytest
from fastapi.testclient import TestClient
import os  # For creating a dummy file

# Import the FastAPI app instance from your main application file
# Adjust the import path based on your project structure
# Assuming your FastAPI app instance is named 'app' in 'app/main.py'
try:
    from app.main import app
except ModuleNotFoundError:
    # This try-except block can help if you run pytest from different locations
    # or if your PYTHONPATH isn't set up as expected in all environments.
    # For a consistent setup, ensure your project root is in PYTHONPATH or use `python -m pytest`
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from app.main import app


@pytest.fixture(scope="module")
def client():
    """
    Create a TestClient instance for the FastAPI app.
    This fixture will be shared across all tests in this module.
    """
    with TestClient(app) as c:
        yield c


def test_read_root(client: TestClient):
    """Test the root endpoint that serves the HTML test page."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert b"<title>Document Processing API Test</title>" in response.content


def test_get_status(client: TestClient):
    """Test the health check /status endpoint."""
    response = client.get("/status")
    assert response.status_code == 200
    json_response = response.json()
    assert json_response == {"status": "ok", "message": "API is running"}


def test_process_document_placeholder_no_file(client: TestClient):
    """Test the /process/document/ endpoint without providing a file (should fail gracefully)."""
    response = client.post("/process/document/")
    assert response.status_code == 422  # FastAPI's validation error for missing 'file' part
    # Or 400 if you handle it differently before FastAPI's validation kicks in
    # json_response = response.json()
    # assert "No file uploaded" in json_response.get("detail", "") or "field required" in str(response.content).lower()


def test_process_document_placeholder_with_file(client: TestClient):
    """
    Test the /process/document/ placeholder endpoint with a dummy file.
    This test will evolve as processing logic is added.
    """
    # Create a dummy file for testing upload
    dummy_file_content = b"This is a dummy test file content."
    dummy_file_name = "test_dummy.txt"

    # The 'files' parameter for TestClient should be a dictionary where keys are form field names
    # and values are tuples like (filename, file_content, content_type)
    files = {"file": (dummy_file_name, dummy_file_content, "text/plain")}

    response = client.post("/process/document/?output_format=text", files=files)

    assert response.status_code == 200
    json_response = response.json()

    assert json_response["filename"] == dummy_file_name
    assert json_response["content_type"] == "text/plain"
    assert json_response["file_extension"] == "txt"
    assert json_response["requested_output_format"] == "text"
    assert "File uploaded successfully" in json_response["message"]
    assert "Processing not yet implemented" in json_response["processed_content_placeholder"]

    # Basic check for the temp file path (it might vary, so just check existence of key)
    assert "temp_file_path" in json_response
    temp_file_path = json_response["temp_file_path"]

    # Check if the temporary file was created (and then clean it up if your main.py doesn't)
    # This depends on your main.py's cleanup logic.
    # If main.py cleans up immediately, this assertion might fail or need adjustment.
    # For Phase 0, if the file is left for inspection, this is fine.
    assert os.path.exists(temp_file_path)
    if os.path.exists(temp_file_path):
        os.remove(temp_file_path)  # Clean up dummy file from test


def test_custom_api_docs(client: TestClient):
    """Test the custom API documentation placeholder page."""
    response = client.get("/documentation")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert b"<title>API Documentation</title>" in response.content
    assert b"For live, interactive API documentation (Swagger UI)" in response.content


def test_fastapi_auto_docs(client: TestClient):
    """Test that FastAPI's automatic /docs endpoint is available."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_fastapi_auto_redoc(client: TestClient):
    """Test that FastAPI's automatic /redoc endpoint is available."""
    response = client.get("/redoc")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]