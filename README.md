# Document Processing API

A self-hosted Python API to ingest PDF, DOCX, and scanned image documents, extract their textual content and table data.

## Project Phase 0: Foundation & API Scaffolding

This phase sets up the basic project structure, API framework, core utilities, and initial HTML pages for testing and documentation.

### Setup

1.  **Clone the repository (if applicable):**
    ```bash
    git clone <your-repo-url>
    cd document_processing_api
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3. **System Dependencies (Linux - Debian/Ubuntu based)**

This project uses Python packages that rely on certain system-level libraries being installed. For the OCR and document processing functionalities to work correctly, please install the following:

* **Tesseract OCR Engine & Language Packs:** Essential for performing Optical Character Recognition (OCR) on images.

```Bash

sudo apt-get update
sudo apt-get install -y tesseract-ocr
```
Install the English language pack (and any other languages you need):

```Bash

sudo apt-get install -y tesseract-ocr-eng
# Example for French: sudo apt-get install -y tesseract-ocr-fra
```

* **Image Format Libraries (for Pillow & OpenCV):**
Needed to load and process various image formats like PNG, JPEG, and TIFF.

```Bash

sudo apt-get install -y libjpeg-dev libpng-dev libtiff-dev zlib1g-dev
```
* **OpenCV Core System Libraries (Recommended):**
While `opencv-python` is a wheel, ensuring these base libraries are present can help.

```Bash

sudo apt-get install -y libgl1-mesa-glx libglib2.0-0
```
* **lxml Dependencies:**
Required by `python-docx `for processing DOCX files.

```
sudo apt-get install -y libxml2-dev libxslt1-dev
```
**Summary of Essential Installation Commands:**

```sudo apt-get update
sudo apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    zlib1g-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libxml2-dev \
    libxslt1-dev
# Add other tesseract language packs if needed
```
**Python Dependencies**
4. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Running the Application (Development)

To run the development server:
```bash
# On the same machine such as dev server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# On a production server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
