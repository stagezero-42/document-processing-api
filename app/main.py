# filename: app/main.py

import os
import shutil
import traceback
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Literal, Union

from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import fitz  # For PyMuPDF operations

from .core.utils import get_file_extension
from .core.constants import SUPPORTED_IMAGE_EXTENSIONS

from .processing.docx_processor import process_docx_file
from .processing.pdf_processor import process_pdf_file
from .processing.image_processor import process_image_file

from .output_formatters.to_plain_text import format_to_plain_text
from .output_formatters.to_json_output import format_content_for_json_schema

from .models import DocumentJSONResponse, OCRJSONResponse, TextResponseContent, DocumentContent, OCRContent

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT_DIR = os.path.dirname(APP_DIR)

app = FastAPI(
    title="Document Processing API",
    description="API to process PDF, DOCX, and image documents to text and structured data. "
                "<p><strong><a href='/'>Test Page</a></strong> | <strong><a href='/documentation'>API Documentation</a></strong></p>",
    version="0.3.1"
)

static_content_dir = os.path.join(APP_DIR, "static")
if not os.path.exists(static_content_dir):
    os.makedirs(static_content_dir)
app.mount("/static", StaticFiles(directory=static_content_dir), name="static")

templates_dir = os.path.join(APP_DIR, "templates")
templates = Jinja2Templates(directory=templates_dir)

PROJECT_UPLOAD_DIRECTORY = os.path.join(PROJECT_ROOT_DIR, "temp_uploads")
if not os.path.exists(PROJECT_UPLOAD_DIRECTORY):
    os.makedirs(PROJECT_UPLOAD_DIRECTORY)

PDF_OCR_FALLBACK_MIN_TEXT_THRESHOLD = 100


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def read_root(request: Request):
    return templates.TemplateResponse(
        request=request, name="api_test.html", context={"request": request, "page_title": "API Test Page"}
    )


@app.get("/documentation", response_class=HTMLResponse, include_in_schema=False)
async def custom_api_docs_page(request: Request):
    return templates.TemplateResponse(
        request=request, name="api_docs.html", context={"request": request, "page_title": "API Documentation"}
    )


@app.get("/status")
async def get_status():
    return {"status": "ok", "message": "API is running"}


@app.post("/process/document/",
          response_model=Union[DocumentJSONResponse, OCRJSONResponse, TextResponseContent],
          summary="Process DOCX, PDF, or Image files")
async def process_document_endpoint(
        request: Request,
        file: UploadFile = File(...,
                                description="The document file to process (.docx, .pdf, .png, .jpg, .jpeg, .tif, .tiff, .bmp, .webp)"),
        output_format: str = Query("json", enum=["json", "text"], description="Desired output format"),

        pdf_table_strategy: Optional[Literal["lines_strict", "text", "lines", "pymupdf_default"]] = Query(
            "lines_strict",
            description="Strategy for PyMuPDF table finding for PDFs. 'lines_strict' is API default."
        ),
        pdf_text_tolerance: Optional[int] = Query(
            None, ge=0, le=50,
            description="Text tolerance for PDF 'text' table strategy (e.g., 3-10)."
        ),
        pdf_remove_empty_rows: bool = Query(
            False,
            description="If true, remove empty table rows from PDF table extraction."
        ),

        ocr_language: Optional[str] = Query(
            "eng",
            description="OCR Language(s) for Tesseract (e.g., 'eng', 'fra', 'eng+fra')."
        ),
        ocr_page_segmentation_mode: Optional[int] = Query(
            3, ge=0, le=13,
            description="Tesseract Page Segmentation Mode (PSM, 0-13). Default: 3."
        ),
        ocr_engine_mode: Optional[int] = Query(
            3, ge=0, le=4,
            description="Tesseract OCR Engine Mode (OEM, 0-4). Default: 3 (LSTM)."
        ),
        ocr_apply_preprocessing: bool = Query(
            True,
            description="Enable standard image preprocessing for OCR. Default: true."
        ),
        ocr_deskew: bool = Query(
            True,
            description="Enable image deskewing as part of preprocessing for OCR. Default: true."
        ),
        ocr_char_whitelist: Optional[str] = Query(
            None,
            description="Tesseract character whitelist (e.g., '0123456789')."
        )
):
    original_filename = file.filename if file.filename else "unknown_file.tmp"
    file_extension = get_file_extension(original_filename)
    temp_safe_filename = os.path.basename(original_filename)
    file_path = os.path.join(PROJECT_UPLOAD_DIRECTORY, temp_safe_filename)

    processed_data: Optional[Dict[str, Any]] = None
    pdf_processing_method_indication: Optional[Literal["direct_text_extraction", "ocr_extraction"]] = None
    pdf_processed_via_ocr = False

    ocr_extraction_settings = {
        "ocr_language": ocr_language,
        "ocr_page_segmentation_mode": ocr_page_segmentation_mode,
        "ocr_engine_mode": ocr_engine_mode,
        "ocr_apply_preprocessing": ocr_apply_preprocessing,
        "ocr_deskew": ocr_deskew,
        "ocr_char_whitelist": ocr_char_whitelist,
    }

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if file_extension == "docx":
            processed_data = process_docx_file(file_path)
        elif file_extension == "pdf":
            pdf_extraction_settings = {
                "table_strategy": pdf_table_strategy,
                "text_tolerance": pdf_text_tolerance,
                "remove_empty_rows": pdf_remove_empty_rows,
            }
            direct_pdf_data = process_pdf_file(file_path, settings=pdf_extraction_settings)
            extracted_text_direct = direct_pdf_data.get("text_with_placeholders", "")

            processed_data = direct_pdf_data
            pdf_processing_method_indication = "direct_text_extraction"

            if len(extracted_text_direct.strip()) < PDF_OCR_FALLBACK_MIN_TEXT_THRESHOLD:
                print(
                    f"Direct text extraction for PDF '{original_filename}' yielded less than {PDF_OCR_FALLBACK_MIN_TEXT_THRESHOLD} chars. Attempting OCR fallback for first page.")
                temp_ocr_image_path = None
                try:
                    pdf_doc_fitz = fitz.open(file_path)
                    if len(pdf_doc_fitz) > 0:
                        page_to_ocr_idx = 0
                        page_to_ocr = pdf_doc_fitz.load_page(page_to_ocr_idx)

                        base_fn, _ = os.path.splitext(temp_safe_filename)
                        temp_ocr_image_filename = f"{base_fn}_ocr_page_{page_to_ocr_idx}.png"
                        temp_ocr_image_path = os.path.join(PROJECT_UPLOAD_DIRECTORY, temp_ocr_image_filename)

                        pix = page_to_ocr.get_pixmap(dpi=300)
                        pix.save(temp_ocr_image_path)
                        pdf_doc_fitz.close()

                        print(
                            f"Performing OCR on page {page_to_ocr_idx} of '{original_filename}' saved as '{temp_ocr_image_path}'.")
                        ocr_result_data = process_image_file(temp_ocr_image_path, settings=ocr_extraction_settings)

                        if ocr_result_data.get("extracted_text", "").strip():
                            print(f"OCR fallback successful for '{original_filename}', page {page_to_ocr_idx}.")
                            processed_data = ocr_result_data
                            pdf_processing_method_indication = "ocr_extraction"
                            pdf_processed_via_ocr = True
                        else:
                            print(
                                f"PDF OCR fallback for '{original_filename}' (page {page_to_ocr_idx}) yielded no text. Using direct extraction results.")
                    else:
                        print(f"PDF OCR fallback skipped for '{original_filename}' as it has no pages.")
                except Exception as ocr_err:
                    print(
                        f"PDF OCR fallback attempt failed for '{original_filename}': {type(ocr_err).__name__} - {str(ocr_err)}. Using direct PDF extraction results.")
                    traceback.print_exc()
                finally:
                    if temp_ocr_image_path and os.path.exists(temp_ocr_image_path):
                        try:
                            os.remove(temp_ocr_image_path)
                        except Exception as e_remove:
                            print(f"Error removing temp OCR image {temp_ocr_image_path}: {e_remove}")
            else:
                print(
                    f"Direct text extraction for PDF '{original_filename}' yielded sufficient text. Skipping OCR fallback.")

        elif file_extension in SUPPORTED_IMAGE_EXTENSIONS:
            processed_data = process_image_file(file_path, settings=ocr_extraction_settings)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: '{file_extension}'. Supported: docx, pdf, {', '.join(sorted(list(SUPPORTED_IMAGE_EXTENSIONS)))}."
            )

        if not processed_data:
            raise HTTPException(status_code=500, detail="Processing failed to return data from the processor.")

        current_time_utc_iso = datetime.now(timezone.utc).isoformat()

        base_response_data = {
            "filename": original_filename,
            "format": output_format,
            "extraction_date": current_time_utc_iso,
            "source_type": file_extension,
            "pdf_processing_method": pdf_processing_method_indication
        }

        if output_format == "text":
            hint_for_text_format = file_extension
            if file_extension == "pdf" and pdf_processed_via_ocr:
                hint_for_text_format = "image"

            plain_text_content = format_to_plain_text(processed_data, source_type_hint=hint_for_text_format)
            text_response_payload = {**base_response_data, "content": plain_text_content}
            return TextResponseContent(**text_response_payload)

        elif output_format == "json":
            if file_extension == "pdf" and pdf_processed_via_ocr:
                content_object_data = format_content_for_json_schema(processed_data, source_type_hint="image")
                ocr_content_validated = OCRContent(**content_object_data)
                return OCRJSONResponse(**base_response_data, content=ocr_content_validated)
            elif file_extension in SUPPORTED_IMAGE_EXTENSIONS:
                content_object_data = format_content_for_json_schema(processed_data, source_type_hint=file_extension)
                ocr_content_validated = OCRContent(**content_object_data)
                return OCRJSONResponse(**base_response_data, content=ocr_content_validated)
            else:
                content_object_data = format_content_for_json_schema(processed_data, source_type_hint=file_extension)
                doc_content_validated = DocumentContent(**content_object_data)
                return DocumentJSONResponse(**base_response_data, content=doc_content_validated)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported output_format: '{output_format}'. Supported: json, text."
            )

    except ValueError as ve:
        print(f"ValueError during processing: {str(ve)}")
        if "Tesseract OCR engine not found" in str(ve):
            raise HTTPException(status_code=501, detail=f"OCR Engine not available: {str(ve)}")
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
                print(f"Error deleting main temporary file {file_path}: {str(e_os)}")


if __name__ == "__main__":
    import uvicorn

    try:
        import pandas as pd
    except ImportError:
        print("WARNING: pandas library not found. OCR with detailed output might fail. "
              "Please install it: pip install pandas")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)