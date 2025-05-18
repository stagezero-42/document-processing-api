from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
# from fastapi.staticfiles import StaticFiles # Only if you create app/static
import shutil
import os
from typing import Optional

from .core.utils import get_file_extension, UPLOAD_DIRECTORY
# from .core.config import settings # Assuming you might add settings later

# Initialize FastAPI app
app = FastAPI(
    title="Document Processing API",
    description="API to process PDF, DOCX, and scanned documents to text and structured data.",
    version="0.1.0"
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
async def process_document(
    request: Request,
    file: UploadFile = File(...),
    output_format: Optional[str] = "text"
    ):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    file_extension = get_file_extension(file.filename)
    safe_filename = os.path.basename(file.filename)
    file_path = os.path.join(UPLOAD_DIRECTORY, safe_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        processed_content = f"File '{safe_filename}' received. Type: '{file_extension}'. Output format: '{output_format}'. Processing not yet implemented."

        return JSONResponse(content={
            "filename": safe_filename,
            "content_type": file.content_type,
            "file_extension": file_extension,
            "requested_output_format": output_format,
            "message": "File uploaded successfully. Processing logic to be implemented in later phases.",
            "temp_file_path": file_path,
            "processed_content_placeholder": processed_content
        })

    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    finally:
        pass


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
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)