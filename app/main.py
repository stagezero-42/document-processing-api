from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse  # Keep JSONResponse
from fastapi.templating import Jinja2Templates
import shutil
import os
from typing import Optional, Dict, Any
from datetime import datetime, timezone  # Import datetime and timezone

from .core.utils import get_file_extension, UPLOAD_DIRECTORY

from .processing.docx_processor import process_docx_file
from .processing.pdf_processor import process_pdf_file # For later
# from .processing.image_processor import process_image_file # For later

from .output_formatters.to_plain_text import format_to_plain_text
# Updated import for the JSON content formatter:
from .output_formatters.to_json_output import format_content_for_json_schema

app = FastAPI(
    title="Document Processing API",
    description="API to process PDF, DOCX, and scanned documents to text and structured data.",
    version="0.2.0"  # Incremented version - docx done, now PDF
)

# ... (templates, UPLOAD_DIRECTORY check - remains the same) ...
templates = Jinja2Templates(directory="templates")

if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)


@app.get("/", response_class=HTMLResponse)
# ... (read_root remains the same) ...
async def read_root(request: Request):
    context = {"request": request}
    return templates.TemplateResponse(request=request, name="api_test.html", context=context)


@app.get("/status")
# ... (get_status remains the same) ...
async def get_status():
    return {"status": "ok", "message": "API is running"}


@app.post("/process/document/")
async def process_document_endpoint(
        request: Request,
        file: UploadFile = File(...),
        output_format: str = "text"
):
    # ... (filename, file_extension, file_path setup remains the same) ...
    original_filename = file.filename if file.filename else "unknown_file"
    file_extension = get_file_extension(original_filename)

    temp_safe_filename = os.path.basename(original_filename)
    file_path = os.path.join(UPLOAD_DIRECTORY, temp_safe_filename)

    processed_data: Optional[Dict[str, Any]] = None
    source_type = ""  # Initialize source_type

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # --- Document Processing Logic ---
        if file_extension == "docx":
            processed_data = process_docx_file(file_path)
            source_type = "docx"
        elif file_extension == "pdf":  # <--- Add PDF handling
            processed_data = process_pdf_file(file_path)
            source_type = "pdf"
        # elif file_extension in ["png", "jpg", "jpeg", "tiff"]:
        #     processed_data = process_image_file(file_path) # For Phase 3
        #     source_type = "ocr"
        else:
            # Updated error message to include PDF
            raise HTTPException(status_code=400,
                                detail=f"Unsupported file type: '{file_extension}'. Supported: docx, pdf.")

        if not processed_data:
            raise HTTPException(status_code=500, detail="Processing failed to return data.")

        # --- Output Formatting --- (This section remains largely the same as it uses processed_data)
        if output_format == "text":
            plain_text_content = format_to_plain_text(processed_data)
            return JSONResponse(content={
                "filename": original_filename,
                "format": "text",
                "extraction_date": datetime.now(timezone.utc).isoformat(),
                "source_type": source_type,  # source_type is now set
                "content": plain_text_content
            })
        elif output_format == "json":
            content_object = format_content_for_json_schema(processed_data)
            final_json_response = {
                "filename": original_filename,
                "format": "json",
                "extraction_date": datetime.now(timezone.utc).isoformat(),
                "source_type": source_type,  # source_type is now set
                "content": content_object
            }
            return JSONResponse(content=final_json_response)
        else:
            raise HTTPException(status_code=400,
                                detail=f"Unsupported output format: '{output_format}'. Supported: text, json.")
    # ... (exception handling and finally block remain the same) ...
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=f"Processing error: {str(ve)}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in process_document_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during processing.")
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as e:
                print(f"Error deleting temporary file {file_path}: {e}")


@app.get("/documentation", response_class=HTMLResponse)
# ... (custom_api_docs remains the same) ...
async def custom_api_docs(request: Request):
    context = {
        "request": request,
        "api_docs_url": app.docs_url,
        "api_redoc_url": app.redoc_url
    }
    return templates.TemplateResponse(request=request, name="api_docs.html", context=context)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)