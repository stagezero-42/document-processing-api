import pytest
from fastapi.testclient import TestClient
import os  # For creating dummy files and paths
import sys
from docx import Document as CreateDoc  # To create dummy docx files for testing

# Adjust the import path for your FastAPI app instance
# This assumes your FastAPI app instance is named 'app' in 'app/main.py'
# and that pytest is run from the root of your project.
try:
    from app.main import app
except ModuleNotFoundError:
    # Add project root to Python path if running tests from a different working directory
    # or if the app module isn't directly discoverable.
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


# --- Directory for API test specific fixtures ---
# This helps keep fixtures created by API tests separate from unit test fixtures if needed.
TEST_API_FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "api_test_fixtures")
if not os.path.exists(TEST_API_FIXTURES_DIR):
    os.makedirs(TEST_API_FIXTURES_DIR)


# --- Fixture for creating a sample DOCX file for API tests ---
@pytest.fixture
def sample_api_docx_for_placeholder_tests():
    """Creates a DOCX file with text and tables for API placeholder testing."""
    file_path = os.path.join(TEST_API_FIXTURES_DIR, "api_sample_placeholders.docx")
    doc = CreateDoc()
    doc.add_paragraph("API Test: Paragraph 1, before any table.")

    table1 = doc.add_table(rows=2, cols=2)
    table1.cell(0, 0).text = "T1Header1"  # Table 1 Content
    table1.cell(0, 1).text = "T1Header2"
    table1.cell(1, 0).text = "T1Data1"
    table1.cell(1, 1).text = "T1Data2"

    doc.add_paragraph("API Test: Paragraph 2, between tables.")

    table2 = doc.add_table(rows=1, cols=1)
    table2.cell(0, 0).text = "T2SingleCell"  # Table 2 Content

    doc.add_paragraph("API Test: Paragraph 3, after all tables.")
    doc.save(file_path)
    yield file_path  # Provide the path to the test
    # Teardown: remove the file after the test
    if os.path.exists(file_path):
        os.remove(file_path)


# --- Basic API Endpoint Tests (from Phase 0, still valid) ---

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


# --- Tests for /process/document/ endpoint ---

def test_process_document_no_file(client: TestClient):
    """Test the /process/document/ endpoint without providing a file."""
    response = client.post("/process/document/")  # No files sent
    assert response.status_code == 422
    json_response = response.json()

    assert "detail" in json_response
    found_file_error = False
    for error_detail_item in json_response["detail"]:
        is_missing_type = error_detail_item.get("type") == "missing"
        loc_info = error_detail_item.get("loc", [])
        is_file_location = "file" in loc_info or (
                    "body" in loc_info and "file" in loc_info)  # More robust check for 'file' in loc

        if is_missing_type and is_file_location:
            found_file_error = True
            break

    assert found_file_error, f"Error detail should indicate 'file' field is missing. Actual detail: {json_response['detail']}"


def test_process_document_unsupported_file_type(client: TestClient):
    """
    Test the /process/document/ endpoint with an unsupported file type (e.g., .txt).
    It should return a 400 error.
    """
    dummy_file_content = b"This is a dummy text file content for unsupported type test."
    dummy_file_name = "test_dummy_unsupported.txt"  # Using .txt

    files = {"file": (dummy_file_name, dummy_file_content, "text/plain")}

    response = client.post("/process/document/?output_format=text", files=files)

    assert response.status_code == 400  # Expecting Bad Request
    json_response = response.json()
    assert "detail" in json_response
    assert "Unsupported file type: 'txt'" in json_response["detail"]
    assert "Supported types: docx" in json_response["detail"]


def test_process_document_docx_success_text_output(client: TestClient, sample_api_docx_for_placeholder_tests: str):
    """
    Test successful processing of a DOCX file through the API, requesting plain text output,
    checking for placeholders and appended table data.
    """
    with open(sample_api_docx_for_placeholder_tests, "rb") as f:
        files = {"file": (os.path.basename(sample_api_docx_for_placeholder_tests), f,
                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        response = client.post("/process/document/?output_format=text", files=files)

    assert response.status_code == 200, f"API Error: {response.text}"
    json_response = response.json()  # API returns JSON even for text output type

    assert json_response["filename"] == os.path.basename(sample_api_docx_for_placeholder_tests)
    assert json_response["format"] == "text"

    content = json_response["content"]  # This is the plain text string from format_to_plain_text
    assert "API Test: Paragraph 1, before any table." in content
    assert "[[insert-table001]]" in content
    assert "API Test: Paragraph 2, between tables." in content
    assert "[[insert-table002]]" in content
    assert "API Test: Paragraph 3, after all tables." in content

    # Check that the appended table data is present (as per format_to_plain_text.py)
    assert "--- Referenced Table Data ---" in content
    assert "--- table001 ---" in content
    assert "T1Header1\tT1Header2" in content
    assert "T1Data1\tT1Data2" in content
    assert "--- table002 ---" in content
    assert "T2SingleCell" in content


def test_process_document_docx_success_json_output(client: TestClient, sample_api_docx_for_placeholder_tests: str):
    """
    Test successful processing of a DOCX file through the API, requesting JSON output,
    checking for placeholders and named tables.
    """
    with open(sample_api_docx_for_placeholder_tests, "rb") as f:
        files = {"file": (os.path.basename(sample_api_docx_for_placeholder_tests), f,
                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        response = client.post("/process/document/?output_format=json", files=files)

    assert response.status_code == 200, f"API Error: {response.text}"
    json_response = response.json()

    assert json_response["filename"] == os.path.basename(sample_api_docx_for_placeholder_tests)
    assert json_response["format"] == "json"

    content = json_response["content"]  # This is the structured JSON content from format_to_json_structure
    assert "extracted_text_with_placeholders" in content
    assert "tables" in content  # This should now be the named_tables dictionary

    text_with_placeholders = content["extracted_text_with_placeholders"]
    named_tables_output = content["tables"]

    assert "API Test: Paragraph 1, before any table." in text_with_placeholders
    assert "[[insert-table001]]" in text_with_placeholders
    assert "API Test: Paragraph 2, between tables." in text_with_placeholders
    assert "[[insert-table002]]" in text_with_placeholders
    assert "API Test: Paragraph 3, after all tables." in text_with_placeholders

    assert isinstance(named_tables_output, dict)
    assert "table001" in named_tables_output
    assert "table002" in named_tables_output

    assert named_tables_output["table001"] == [["T1Header1", "T1Header2"], ["T1Data1", "T1Data2"]]
    assert named_tables_output["table002"] == [["T2SingleCell"]]