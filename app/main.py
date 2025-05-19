import os
import shutil
import traceback  # For more detailed error logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Literal

from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Assuming core.utils contains get_file_extension
from .core.utils import get_file_extension
# from .core.config import settings # If you have a config file

# Import processors
from .processing.docx_processor import process_docx_file
from .processing.pdf_processor import process_pdf_file
# from .processing.image_processor import process_image_file # For future Phase 3

# Import output formatters
from .output_formatters.to_plain_text import format_to_plain_text
from .output_formatters.to_json_output import format_content_for_json_schema

# --- Path Definitions ---
# APP_DIR is the directory where this main.py file is located (i.e., the 'app' folder)
APP_DIR = os.path.dirname(os.path.abspath(__file__))
# PROJECT_ROOT_DIR is one level up from the 'app' folder
PROJECT_ROOT_DIR = os.path.dirname(APP_DIR)  # Still useful for other project root relative paths if needed

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Document Processing API",
    description="API to process PDF, DOCX, and (eventually) scanned documents to text and structured data. "
                "<p><strong><a href='/'>Test Page</a></strong> | <strong><a href='/documentation'>API Documentation</a></strong></p>",
    version="0.1.4"  # Update version as you add features
)

# --- Static Files Configuration ---
# Serves files from 'app/static/' directory under the '/static' URL path
static_content_dir = os.path.join(APP_DIR, "static")
if not os.path.exists(static_content_dir):
    os.makedirs(static_content_dir)
app.mount("/static", StaticFiles(directory=static_content_dir), name="static")

# --- Templates Configuration ---
# CORRECTED: Serves HTML templates from 'app/templates/'
templates_dir = os.path.join(APP_DIR, "templates")  # <--- CORRECTED LINE
templates = Jinja2Templates(directory=templates_dir)

# --- Upload Directory Configuration ---
# Temporary files will be stored in 'project_root/temp_uploads/'
PROJECT_UPLOAD_DIRECTORY = os.path.join(PROJECT_ROOT_DIR, "temp_uploads")
if not os.path.exists(PROJECT_UPLOAD_DIRECTORY):
    os.makedirs(PROJECT_UPLOAD_DIRECTORY)


# --- HTML Serving Endpoints ---
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def read_root(request: Request):
    """Serves the main API testing page."""
    return templates.TemplateResponse(
        request=request, name="api_test.html", context={"request": request, "page_title": "API Test Page"}
    )


@app.get("/documentation", response_class=HTMLResponse, include_in_schema=False)
async def custom_api_docs_page(request: Request):
    """Serves the custom API documentation page."""
    return templates.TemplateResponse(
        request=request, name="api_docs.html", context={"request": request, "page_title": "API Documentation"}
    )


# --- API Endpoints ---
@app.get("/status")
async def get_status():
    """Health check endpoint."""
    return {"status": "ok", "message": "API is running"}


@app.post("/process/document/")
async def process_document_endpoint(
        request: Request,
        file: UploadFile = File(..., description="The document file to process (.docx or .pdf)"),
        output_format: str = Query("json", enum=["json", "text"], description="Desired output format"),

        pdf_table_strategy: Optional[Literal["lines_strict", "text", "lines", "pymupdf_default"]] = Query(
            "lines_strict",
            description="Strategy for PyMuPDF table finding. 'lines_strict' is API default."
        ),
        pdf_text_tolerance: Optional[int] = Query(
            None,
            ge=0,
            le=50,
            description="Text tolerance for 'text' strategy (e.g., 3-10). Higher values group more aggressively."
        ),
        pdf_remove_empty_rows: bool = Query(
            False,
            description="If true, remove table rows where all cells are empty after initial processing."
        )
):
    """
    Uploads a document file (DOCX or PDF) for text and table extraction.
    Returns extracted content based on the specified output format and PDF processing settings.
    """
    original_filename = file.filename if file.filename else "unknown_file.tmp"
    file_extension = get_file_extension(original_filename)

    temp_safe_filename = os.path.basename(original_filename)
    file_path = os.path.join(PROJECT_UPLOAD_DIRECTORY, temp_safe_filename)

    processed_data: Optional[Dict[str, Any]] = None
    source_type = ""

    pdf_extraction_settings = {
        "table_strategy": pdf_table_strategy,
        "text_tolerance": pdf_text_tolerance,
        "remove_empty_rows": pdf_remove_empty_rows,
    }

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if file_extension == "docx":
            processed_data = process_docx_file(file_path)
            source_type = "docx"
        elif file_extension == "pdf":
            processed_data = process_pdf_file(file_path, settings=pdf_extraction_settings)
            source_type = "pdf"
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: '{file_extension}'. Supported types: docx, pdf."
            )

        if not processed_data:
            raise HTTPException(status_code=500, detail="Processing failed to return data from the processor.")

        current_time_utc = datetime.now(timezone.utc).isoformat()

        if output_format == "text":
            plain_text_content = format_to_plain_text(processed_data)
            return JSONResponse(content={
                "filename": original_filename,
                "format": "text",
                "extraction_date": current_time_utc,
                "source_type": source_type,
                "content": plain_text_content
            })
        elif output_format == "json":
            content_object = format_content_for_json_schema(processed_data)
            final_json_response = {
                "filename": original_filename,
                "format": "json",
                "extraction_date": current_time_utc,
                "source_type": source_type,
                "content": content_object
            }
            return JSONResponse(content=final_json_response)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported output_format: '{output_format}'. Supported: json, text."
            )

    except ValueError as ve:
        print(f"Processing ValueError: {str(ve)}")
        raise HTTPException(status_code=422, detail=f"Processing error: {str(ve)}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in process_document_endpoint: {type(e).__name__} - {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="An unexpected error occurred during document processing.")
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as e_os:
                print(f"Error deleting temporary file {file_path}: {str(e_os)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
