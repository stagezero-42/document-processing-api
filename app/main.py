from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
# from fastapi.staticfiles import StaticFiles # Only if you create app/static
import shutil
import os
from typing import Optional, Dict, Any

from .core.utils import get_file_extension, UPLOAD_DIRECTORY
# from .core.config import settings
from .processing.docx_processor import process_docx_file
from .output_formatters.to_plain_text import format_to_plain_text
from .output_formatters.to_json_output import format_to_json_structure

# Initialize FastAPI app
app = FastAPI(
    title="Document Processing API",
    description="API to process PDF, DOCX, and scanned documents to text and structured data.",
    version="0.2.0"
)

# Configure templates
templates = Jinja2Templates(directory="templates")

# Ensure upload directory exists
if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """
    Serves the main API testing page.
    """
    context = {"request": request} # Define context
    return templates.TemplateResponse(request=request, name="api_test.html", context=context) # Pass defined context

@app.get("/status")
async def get_status():
    """
    Health check endpoint.
    """
    return {"status": "ok", "message": "API is running"}

@app.post("/process/document/")
async def process_document_endpoint( # Renamed from process_document to avoid conflict with any potential local var
    request: Request,
    file: UploadFile = File(...),
    output_format: str = "text" # Default to text, can be "json", "markdown" etc.
    ):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    file_extension = get_file_extension(file.filename)
    safe_filename = os.path.basename(file.filename)
    file_path = os.path.join(UPLOAD_DIRECTORY, safe_filename)

    processed_data: Optional[Dict[str, Any]] = None
    final_output: Any = None

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # --- Document Processing Logic ---
        if file_extension == "docx":
            processed_data = process_docx_file(file_path)
        # elif file_extension == "pdf":
            # processed_data = process_pdf_file(file_path) # For Phase 2
        # elif file_extension in ["png", "jpg", "jpeg", "tiff"]:
            # processed_data = process_image_file(file_path) # For Phase 3
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: '{file_extension}'. Supported types: docx.")

        if not processed_data:
             raise HTTPException(status_code=500, detail="Processing failed to return data.")

        # --- Output Formatting ---
        if output_format == "text":
            final_output = format_to_plain_text(processed_data)
            # For plain text, it's usually returned directly, not as JSON
            # Consider how you want to return plain text (e.g., PlainTextResponse)
            # For now, wrapping it in a JSON for consistency with the example
            return JSONResponse(content={"filename": safe_filename, "format": "text", "content": final_output})
        elif output_format == "json":
            final_output = format_to_json_structure(processed_data)
            return JSONResponse(content={"filename": safe_filename, "format": "json", "content": final_output})
        # elif output_format == "markdown":
        #     final_output = format_to_markdown(processed_data) # For future phase
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported output format: '{output_format}'. Supported: text, json.")

    except ValueError as ve: # Catch specific errors from processors
        raise HTTPException(status_code=422, detail=f"Processing error: {str(ve)}")
    except HTTPException: # Re-raise HTTPExceptions
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
    finally:
        # Clean up the uploaded file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as e:
                # Log this error, as failure to delete a temp file can be an issue
                print(f"Error deleting temporary file {file_path}: {e}")


@app.get("/documentation", response_class=HTMLResponse)
async def custom_api_docs(request: Request):
    """
    Serves a custom API documentation page (placeholder).
    FastAPI's /docs and /redoc are generally preferred for live API docs.
    """
    context = { # Context defined here
        "request": request,
        "api_docs_url": app.docs_url,
        "api_redoc_url": app.redoc_url
    }
    return templates.TemplateResponse(request=request, name="api_docs.html", context=context) # Correctly passing context

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9090, reload=True)
