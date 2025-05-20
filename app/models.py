# filename: app/models.py
# (Create this new file for Pydantic models if it doesn't exist,
# or add to an existing models.py)

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union, Literal

class TableContent(BaseModel):
    id: str
    position: int
    caption: Optional[str] = None
    headers: List[str]
    # Allow mixed types in table data, ensure None is also possible for cells
    data: List[List[Union[str, int, float, None]]]
    page_number: Optional[int] = None

class DocumentContent(BaseModel):
    extracted_text_with_placeholders: str
    tables: List[TableContent]

class OCRWordDetail(BaseModel):
    text: str
    confidence: float
    left: int
    top: int
    width: int
    height: int

class OCRSettingsUsed(BaseModel):
    language: str
    page_segmentation_mode: int
    engine_mode: int
    preprocessing_applied: bool
    deskew_applied: bool
    char_whitelist: Optional[str] = None

class OCRContent(BaseModel):
    extracted_text: str
    ocr_settings_used: OCRSettingsUsed
    word_level_details: Optional[List[OCRWordDetail]] = None
    tables: List[TableContent] = Field(default_factory=list) # Usually empty for OCR

class BaseAPIResponse(BaseModel):
    filename: str
    format: str # "json" or "text"
    extraction_date: str # ISO 8601
    source_type: str # e.g., "docx", "pdf", "png", "jpeg"
    # New field to indicate how a PDF was processed
    pdf_processing_method: Optional[Literal["direct_text_extraction", "ocr_extraction"]] = None

class DocumentJSONResponse(BaseAPIResponse):
    content: DocumentContent

class OCRJSONResponse(BaseAPIResponse):
    content: OCRContent

class TextResponseContent(BaseModel): # This model is simpler and might not include pdf_processing_method directly unless modified too.
                                     # For now, focusing on JSON output.
    filename: str
    format: Literal["text"] # type: ignore
    extraction_date: str
    source_type: str
    content: str # The plain text content
    pdf_processing_method: Optional[Literal["direct_text_extraction", "ocr_extraction"]] = None