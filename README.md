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

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Running the Application (Development)

To run the development server:
```bash
uvicorn app.main:app --reload