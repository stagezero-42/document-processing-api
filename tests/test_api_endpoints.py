import pytest
from fastapi.testclient import TestClient
import os
import sys
from docx import Document as CreateDoc # For DOCX fixtures
from datetime import datetime

# Adjust the import path for your FastAPI app instance
try:
    from app.main import app
except ModuleNotFoundError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from app.main import app

@pytest.fixture(scope="module")
def client():
    """Create a TestClient instance for the FastAPI app."""
    with TestClient(app) as c:
        yield c

# Directory for API test specific temporary fixture files
API_TEMP_FIXTURES_BASE_DIR = os.path.join(os.path.dirname(__file__), "api_temp_fixtures")
DOCX_API_FIXTURES_DIR = os.path.join(API_TEMP_FIXTURES_BASE_DIR, "docx")

if not os.path.exists(DOCX_API_FIXTURES_DIR):
    os.makedirs(DOCX_API_FIXTURES_DIR)

# --- Fixture for DOCX API tests (schema focused) ---
@pytest.fixture
def sample_api_docx_for_schema_tests():
    """Creates a DOCX file with text and tables for API schema testing."""
    file_path = os.path.join(DOCX_API_FIXTURES_DIR, "api_sample_for_schema.docx")
    doc = CreateDoc()
    doc.add_paragraph("API Schema Test: Para 1.")
    table1 = doc.add_table(rows=2, cols=2)
    table1.cell(0,0).text = "Name"
    table1.cell(0,1).text = "Age"
    table1.cell(1,0).text = "Alice"
    table1.cell(1,1).text = "30"
    doc.add_paragraph("API Schema Test: Para 2, between tables.")
    table2 = doc.add_table(rows=1, cols=1)
    table2.cell(0,0).text = "Note"
    doc.add_paragraph("API Schema Test: Para 3.")
    doc.save(file_path)
    yield file_path
    if os.path.exists(file_path):
        os.remove(file_path)

# --- Basic API Endpoint Tests ---
def test_read_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert b"<title>Document Processing API Test</title>" in response.content

def test_get_status(client: TestClient):
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "API is running"}

def test_custom_api_docs(client: TestClient):
    response = client.get("/documentation")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert b"<title>API Documentation</title>" in response.content

def test_fastapi_auto_docs(client: TestClient):
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_fastapi_auto_redoc(client: TestClient):
    response = client.get("/redoc")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

# --- Tests for /process/document/ endpoint (Error Handling & DOCX) ---
def test_process_document_no_file(client: TestClient):
    response = client.post("/process/document/")
    assert response.status_code == 422
    json_response = response.json()
    assert "detail" in json_response
    found_file_error = False
    for error_detail_item in json_response["detail"]:
        is_missing_type = error_detail_item.get("type") == "missing"
        loc_info = error_detail_item.get("loc", [])
        is_file_location = "file" in loc_info or ("body" in loc_info and "file" in loc_info)
        if is_missing_type and is_file_location:
            found_file_error = True
            break
    assert found_file_error, f"Error detail should indicate 'file' field is missing. Actual detail: {json_response['detail']}"

def test_process_document_unsupported_file_type(client: TestClient):
    """Test with a currently unsupported file type (e.g., .png for now)."""
    dummy_file_content = b"This is a dummy image file content (pretend)."
    dummy_file_name = "test_dummy_unsupported.png" # .png is not yet supported
    files = {"file": (dummy_file_name, dummy_file_content, "image/png")}
    response = client.post("/process/document/?output_format=text", files=files)
    assert response.status_code == 400
    json_response = response.json()
    assert "detail" in json_response
    assert "Unsupported file type: 'png'" in json_response["detail"]
    assert "Supported: docx, pdf" in json_response["detail"] # Reflects current known supported types

# --- DOCX API Tests ---
def test_process_document_docx_success_text_output(client: TestClient, sample_api_docx_for_schema_tests: str):
    with open(sample_api_docx_for_schema_tests, "rb") as f:
        files = {"file": (os.path.basename(sample_api_docx_for_schema_tests), f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        response = client.post("/process/document/?output_format=text", files=files)
    assert response.status_code == 200, f"API Error: {response.text}"
    json_response = response.json()
    assert json_response["filename"] == os.path.basename(sample_api_docx_for_schema_tests)
    assert json_response["format"] == "text"
    assert "extraction_date" in json_response
    assert "T" in json_response["extraction_date"] and "+00:00" in json_response["extraction_date"]
    assert json_response["source_type"] == "docx"
    content = json_response["content"]
    assert "API Schema Test: Para 1." in content
    assert "[[INSERT_TABLE:table001]]" in content
    assert "API Schema Test: Para 2, between tables." in content
    assert "[[INSERT_TABLE:table002]]" in content
    assert "API Schema Test: Para 3." in content
    assert "--- Referenced Table Data ---" in content
    assert "--- table001 ---" in content
    assert "Name\tAge" in content
    assert "Alice\t30" in content
    assert "--- table002 ---" in content
    assert "Note" in content

def test_process_document_docx_success_json_output(client: TestClient, sample_api_docx_for_schema_tests: str):
    with open(sample_api_docx_for_schema_tests, "rb") as f:
        files = {"file": (os.path.basename(sample_api_docx_for_schema_tests), f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        response = client.post("/process/document/?output_format=json", files=files)
    assert response.status_code == 200, f"API Error: {response.text}"
    json_response = response.json()
    assert json_response["filename"] == os.path.basename(sample_api_docx_for_schema_tests)
    assert json_response["format"] == "json"
    assert "extraction_date" in json_response
    try: datetime.fromisoformat(json_response["extraction_date"].replace("Z", "+00:00"))
    except ValueError: pytest.fail(f"extraction_date is not valid ISO: {json_response['extraction_date']}")
    assert json_response["source_type"] == "docx"
    content = json_response["content"]
    assert "extracted_text_with_placeholders" in content
    text_with_placeholders = content["extracted_text_with_placeholders"]
    assert "API Schema Test: Para 1." in text_with_placeholders
    assert "[[INSERT_TABLE:table001]]" in text_with_placeholders
    assert "[[INSERT_TABLE:table002]]" in text_with_placeholders
    tables_array = content["tables"]
    assert isinstance(tables_array, list)
    assert len(tables_array) == 2
    table1_data_from_api = tables_array[0]
    assert table1_data_from_api["id"] == "table001"
    assert table1_data_from_api["position"] == 1
    assert table1_data_from_api["caption"] is None
    assert table1_data_from_api["headers"] == ["Name", "Age"]
    assert table1_data_from_api["data"] == [["Alice", "30"]]
    table2_data_from_api = tables_array[1]
    assert table2_data_from_api["id"] == "table002"
    assert table2_data_from_api["headers"] == ["Note"]
    assert table2_data_from_api["data"] == []