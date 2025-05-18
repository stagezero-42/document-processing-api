import pytest
import os
from docx import Document as CreateDoc

from app.processing.docx_processor import process_docx_file  # Ensure this import is correct

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
if not os.path.exists(FIXTURES_DIR):
    os.makedirs(FIXTURES_DIR)


@pytest.fixture
def sample_docx_with_text_and_tables():
    file_path = os.path.join(FIXTURES_DIR, "test_text_and_tables_fixture.docx")
    doc = CreateDoc()
    doc.add_paragraph("First paragraph.")
    doc.add_paragraph("Text before table 1.")

    table1_data = [["ID", "Value"], ["1", "Alpha"]]
    t1 = doc.add_table(rows=len(table1_data), cols=len(table1_data[0]))
    for i, row_d in enumerate(table1_data):
        for j, cell_d in enumerate(row_d):
            t1.cell(i, j).text = cell_d

    doc.add_paragraph("Text between tables.")

    table2_data = [["Fruit", "Color"], ["Apple", "Red"], ["Banana", "Yellow"]]
    t2 = doc.add_table(rows=len(table2_data), cols=len(table2_data[0]))
    for i, row_d in enumerate(table2_data):
        for j, cell_d in enumerate(row_d):
            t2.cell(i, j).text = cell_d

    doc.add_paragraph("Text after table 2.")
    doc.save(file_path)
    yield file_path
    os.remove(file_path)


@pytest.fixture
def sample_docx_simple_text_only():
    file_path = os.path.join(FIXTURES_DIR, "test_simple_text_only_fixture.docx")
    doc = CreateDoc()
    doc.add_paragraph("Hello world.")
    doc.add_paragraph("This is a test document with basic text and no tables.")
    doc.save(file_path)
    yield file_path
    os.remove(file_path)


def test_process_docx_simple_text_only(sample_docx_simple_text_only):
    result = process_docx_file(sample_docx_simple_text_only)

    assert "text_with_placeholders" in result
    assert "named_tables" in result
    assert "Hello world." in result["text_with_placeholders"]
    assert "no tables" in result["text_with_placeholders"]
    assert "<<insert-table" not in result["text_with_placeholders"]  # No placeholders
    assert len(result["named_tables"]) == 0


def test_process_docx_with_text_and_tables(sample_docx_with_text_and_tables):
    result = process_docx_file(sample_docx_with_text_and_tables)

    assert "text_with_placeholders" in result
    assert "named_tables" in result

    text = result["text_with_placeholders"]
    tables = result["named_tables"]

    assert "First paragraph." in text
    assert "Text before table 1." in text
    assert "[[insert-table001]]" in text
    assert "Text between tables." in text
    assert "[[insert-table002]]" in text
    assert "Text after table 2." in text

    assert len(tables) == 2
    assert "table001" in tables
    assert "table002" in tables

    assert tables["table001"] == [["ID", "Value"], ["1", "Alpha"]]
    assert tables["table002"] == [["Fruit", "Color"], ["Apple", "Red"], ["Banana", "Yellow"]]


def test_process_non_existent_file():
    with pytest.raises(ValueError) as excinfo:
        process_docx_file("non_existent_document.docx")
    # Verify the components of the actual error message
    actual_error_message = str(excinfo.value)
    assert "Error processing DOCX file" in actual_error_message # Check for the new prefix
    assert "non_existent_document.docx" in actual_error_message # Check for the filename
    assert "Package not found" in actual_error_message         # Check for the specific error from python-docx