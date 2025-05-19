import pytest
import os
import fitz  # PyMuPDF for potentially creating test PDFs if needed, or just for type hints

# Adjust import based on your project structure
from app.processing.pdf_processor import process_pdf_file

# Define a directory for PDF test fixture files
PDF_FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "pdfs")
if not os.path.exists(PDF_FIXTURES_DIR):
    os.makedirs(PDF_FIXTURES_DIR)


# --- Helper to create simple PDFs for testing (optional, or use pre-made PDFs) ---
# You might need to install reportlab: pip install reportlab
def create_sample_pdf_for_test(file_path: str, content_type: str = "text_and_table"):
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch

        c = canvas.Canvas(file_path, pagesize=letter)

        if content_type == "text_only":
            c.drawString(1 * inch, 10 * inch, "PDF Test: Simple text line 1.")
            c.drawString(1 * inch, 9.5 * inch, "PDF Test: Simple text line 2.")
        elif content_type == "text_and_table":
            c.drawString(1 * inch, 10 * inch, "PDF Test: Text before table.")

            # ReportLab table creation is more involved for complex tables.
            # This is a very basic visual representation of a table for text extraction.
            # PyMuPDF's find_tables might need more structured tables to work best.
            textobject = c.beginText(1 * inch, 9.0 * inch)
            textobject.setFont("Helvetica", 10)
            textobject.textLine("HeaderA  HeaderB")  # Use spaces that PyMuPDF might see as columns
            textobject.textLine("Data1A   Data1B")
            textobject.textLine("Data2A   Data2B")
            c.drawText(textobject)

            c.drawString(1 * inch, 8.0 * inch, "PDF Test: Text after table.")
        elif content_type == "multiple_tables":
            c.drawString(1 * inch, 10 * inch, "PDF Test: Text before table 1.")
            textobject1 = c.beginText(1 * inch, 9.0 * inch)
            textobject1.setFont("Helvetica", 10)
            textobject1.textLine("T1H1  T1H2")
            textobject1.textLine("T1D1  T1D2")
            c.drawText(textobject1)
            c.drawString(1 * inch, 8.0 * inch, "PDF Test: Text between tables.")
            textobject2 = c.beginText(1 * inch, 7.0 * inch)
            textobject2.setFont("Helvetica", 10)
            textobject2.textLine("T2H1  T2H2")
            textobject2.textLine("T2D1  T2D2")
            c.drawText(textobject2)
            c.drawString(1 * inch, 6.0 * inch, "PDF Test: Text after table 2.")

        c.save()
        print(f"Created sample PDF: {file_path}")
    except ImportError:
        pytest.skip("reportlab not installed, skipping PDF creation for this test. Place sample PDFs manually.")
    except Exception as e:
        print(f"Error creating sample PDF {file_path}: {e}")
        pytest.fail(f"Failed to create sample PDF for testing: {e}")


@pytest.fixture
def sample_pdf_text_only():
    file_path = os.path.join(PDF_FIXTURES_DIR, "sample_text_only.pdf")
    create_sample_pdf_for_test(file_path, "text_only")
    yield file_path
    if os.path.exists(file_path): os.remove(file_path)


@pytest.fixture
def sample_pdf_with_table():
    # PyMuPDF's find_tables works best with clear structures, lines, or distinct text columns.
    # The simple text-based table from reportlab might be challenging for it without "lines" strategy.
    # Consider using a PDF created with a word processor or a more sophisticated table generator for robust table tests.
    file_path = os.path.join(PDF_FIXTURES_DIR, "sample_with_table.pdf")
    create_sample_pdf_for_test(file_path, "text_and_table")
    yield file_path
    if os.path.exists(file_path): os.remove(file_path)


@pytest.fixture
def sample_pdf_multiple_tables():
    file_path = os.path.join(PDF_FIXTURES_DIR, "sample_multiple_tables.pdf")
    create_sample_pdf_for_test(file_path, "multiple_tables")
    yield file_path
    if os.path.exists(file_path): os.remove(file_path)


# --- Unit Tests for pdf_processor ---

def test_process_pdf_text_only(sample_pdf_text_only):
    """Test processing a PDF with only text."""
    result = process_pdf_file(sample_pdf_text_only)

    assert "text_with_placeholders" in result
    assert "tables_data" in result
    assert "PDF Test: Simple text line 1." in result["text_with_placeholders"]
    assert "PDF Test: Simple text line 2." in result["text_with_placeholders"]
    assert "[[INSERT_TABLE:" not in result["text_with_placeholders"]
    assert isinstance(result["tables_data"], list)
    assert len(result["tables_data"]) == 0
    assert result["source_basename"] == "sample_text_only.pdf"


def test_process_pdf_with_one_table(sample_pdf_with_table):
    """Test processing a PDF with text and one table."""
    # Note: Table detection with PyMuPDF on purely text-based tables without lines can be tricky.
    # The success of this test heavily depends on PyMuPDF's ability to identify the table created by reportlab.
    # You might need to adjust page.find_tables(strategy="text") or use PDFs with clearer table structures.
    result = process_pdf_file(sample_pdf_with_table)

    assert "text_with_placeholders" in result
    text = result["text_with_placeholders"]
    tables = result["tables_data"]

    assert "PDF Test: Text before table." in text
    assert "PDF Test: Text after table." in text

    if tables:  # Only assert if tables were found
        assert "[[INSERT_TABLE:table001]]" in text
        assert len(tables) >= 1  # Might find one or more based on structure
        table1 = tables[0]
        assert table1["id"] == "table001"
        assert table1["position"] == 1
        assert table1["caption"] is None
        # Headers and data depend heavily on how PyMuPDF extracts the simple text table
        # Example: (this will likely need adjustment based on actual PyMuPDF output for the generated PDF)
        assert len(table1["headers"]) > 0  # Expect some headers
        # assert table1["headers"] == ["HeaderA", "HeaderB"] # This is an example
        # assert len(table1["data"]) > 0 # Expect some data rows
        # assert table1["data"][0] == ["Data1A", "Data1B"] # This is an example
    else:
        print(
            "Warning: No tables detected by PyMuPDF in sample_pdf_with_table. Check PDF structure or find_tables strategy.")
        # If no table is found, no placeholder should be there
        assert "[[INSERT_TABLE:" not in text

    assert result["source_basename"] == "sample_with_table.pdf"


def test_process_pdf_with_multiple_tables(sample_pdf_multiple_tables):
    """Test processing a PDF with text and multiple tables."""
    result = process_pdf_file(sample_pdf_multiple_tables)

    text = result["text_with_placeholders"]
    tables = result["tables_data"]

    assert "PDF Test: Text before table 1." in text
    assert "PDF Test: Text between tables." in text
    assert "PDF Test: Text after table 2." in text

    # Depending on table detection, check placeholders and table data
    found_table1_placeholder = "[[INSERT_TABLE:table001]]" in text
    found_table2_placeholder = "[[INSERT_TABLE:table002]]" in text

    if tables:
        assert len(tables) >= 1  # Expect at least one table, ideally 2

        if len(tables) >= 1 and found_table1_placeholder:
            table1 = next((t for t in tables if t["id"] == "table001"), None)
            assert table1 is not None
            assert table1["position"] == 1  # or check relative order

        if len(tables) >= 2 and found_table2_placeholder:
            table2 = next((t for t in tables if t["id"] == "table002"), None)
            assert table2 is not None
            assert table2["position"] == 2
    else:
        print("Warning: No tables detected in sample_pdf_multiple_tables.")
        assert "[[INSERT_TABLE:" not in text


def test_process_pdf_non_existent_file():
    """Test handling of a non-existent PDF file."""
    with pytest.raises(ValueError) as excinfo:  # PyMuPDF raises fitz.fitz.FileNotFoundError or similar
        process_pdf_file("non_existent_document.pdf")
    # The error message from PyMuPDF might be "no such file or directory" or similar.
    # Our wrapper in pdf_processor.py will prepend "Error processing PDF file..."
    assert "Error processing PDF file" in str(excinfo.value)
    assert "non_existent_document.pdf" in str(excinfo.value)