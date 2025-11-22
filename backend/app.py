import os
import re
from datetime import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import easyocr
from dateutil.parser import parse, ParserError

# Initialize EasyOCR
print("Initializing EasyOCR reader...")
reader = easyocr.Reader(["en", "ar"], gpu= False)
print("EasyOCR reader initialized successfully!")

# PDF Support
try:
    from PyPDF2 import PdfReader
    from pdf2image import convert_from_path
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("Warning: PyPDF2 and pdf2image not installed. PDF support disabled.")

# Initialize FastAPI app
app = FastAPI(
    title="Calendar Event Extractor API",
    description="Extract dates and events from images and PDF files using OCR",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16 megabytes

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename: str, file_type: str = 'image') -> bool:
    """Check if the file extension is allowed."""
    if '.' not in filename:
        return False

    ext = filename.rsplit('.', 1)[1].lower()

    if file_type == 'image':
        return ext in ALLOWED_IMAGE_EXTENSIONS
    elif file_type == 'document':
        return ext in ALLOWED_IMAGE_EXTENSIONS or ext in ALLOWED_DOCUMENT_EXTENSIONS

    return False


def extract_text_from_image(image_path: str) -> str:
    """Extract text from image using EasyOCR."""
    try:
        # EasyOCR returns a list of (bbox, text, confidence) tuples
        result = reader.readtext(image_path)

        text = " ".join([detection[1] for detection in result])

        return text
    except Exception as e:
        print(f"Error extracting text from image: {e}")
        return ""


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF, with EasyOCR fallback."""
    if not PDF_SUPPORT:
        raise ValueError("PDF support not enabled. Install PyPDF2 and pdf2image.")

    text = ""

    try:
        # Extracting text directly from PDF
        pdf_reader = PdfReader(pdf_path)
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        print(f"Error reading PDF text: {e}")

    # If no text found, use EasyOCR on PDF pages
    if not text.strip():
        try:
            import numpy as np
            images = convert_from_path(pdf_path)
            for img in images:
                # Convert PIL image to numpy array for EasyOCR
                img_array = np.array(img)
                result = reader.readtext(img_array)
                page_text = ' '.join([detection[1] for detection in result])
                text += page_text + "\n"
        except Exception as e:
            print(f"Error performing OCR on PDF: {e}")

    return text


def extract_dates_from_text(text: str) -> List[str]:
    """Extract date strings from text using regex patterns."""
    # Common date patterns
    date_patterns = [
        r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',  # MM/DD/YYYY or DD/MM/YYYY
        r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b',    # YYYY-MM-DD
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b',  # Month DD, YYYY
        r'\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b',    # DD Month YYYY
        r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2},? \d{4}\b',  # Full month name
    ]

    raw_dates = []
    for pattern in date_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        raw_dates.extend(matches)

    # Parse and normalize dates
    parsed_dates = []
    for date_str in raw_dates:
        try:
            parsed = parse(date_str, fuzzy=True)
            iso_date = parsed.date().isoformat()
            if iso_date not in parsed_dates:  # Try to avoid duplicates
                parsed_dates.append(iso_date)
        except (ParserError, ValueError):
            continue

    return parsed_dates


def extract_eventsRegex(text: str, dates: List[str]) -> List[Dict[str, Any]]:
    """
    Use AI to extract event information from text.
    This is a placeholder - you can integrate OpenAI or another LLM here.
    """
    # Create simple events from dates
    events = []

    # Split text into sentences
    sentences = re.split(r'[.!?\n]+', text)

    for date in dates:
        # Find context around the date
        event_title = "Event"
        event_description = ""
        confidence = 0.7

        # Look for sentences containing date-related keywords
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Sentence contains time-related words
            keywords = ['meeting', 'appointment', 'conference', 'deadline',
                       'event', 'party', 'celebration', 'visit', 'trip',
                       'class', 'lesson', 'session', 'workshop']

            if any(keyword in sentence.lower() for keyword in keywords):
                event_title = sentence[:50]  # Use first 50 chars as title
                event_description = sentence
                confidence = 0.85
                break

        events.append({
            "date": date,
            "title": event_title,
            "description": event_description,
            "confidence": confidence
        })

    return events


def extract_events_from_file(file_path: str, filename: str) -> List[Dict[str, Any]]:
    """Main function to extract events from uploaded file."""
    text = ""

    # Determine file type and extract text
    if filename.lower().endswith('.pdf'):
        text = extract_text_from_pdf(file_path)
    else:
        text = extract_text_from_image(file_path)

    if not text.strip():
        return []

    # Extract dates from text
    dates = extract_dates_from_text(text)

    if not dates:
        return []

    # Extract events with context
    events = extract_eventsRegex(text, dates)

    return events


# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "pdf_support": PDF_SUPPORT,
        "timestamp": datetime.now().isoformat(),
        "framework": "FastAPI"
    }


@app.post("/extract-events")
async def extract_events(file: UploadFile = File(...)):
    """
    Extract events from uploaded image or PDF file.

    Args:
        file: Image or PDF file to process

    Returns:
        JSON response with extracted events
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    if not allowed_file(file.filename, 'document'):
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Supported formats: {ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DOCUMENT_EXTENSIONS}"
        )

    # Check file size
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB"
        )

    try:
        # Save uploaded file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)

        # Write file to disk
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)

        # Extract events from file
        events = extract_events_from_file(file_path, file.filename)

        # Clean up uploaded file
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Error removing file: {e}")

        return {
            "success": True,
            "events": events,
            "total_events": len(events)
        }

    except Exception as e:
        print(f"Error processing file: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )


@app.post("/extract-events-from-image")
async def extract_events_from_image_endpoint(file: UploadFile = File(...)):
    """
    Extract events from uploaded image (photos from camera).
    Alias for /extract-events endpoint.
    """
    return await extract_events(file)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Calendar Event Extractor API",
        "version": "1.0.0",
        "framework": "FastAPI",
        "endpoints": {
            "health": "/health",
            "extract_events": "/extract-events",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }


if __name__ == '__main__':
    import uvicorn

    print("Starting FastAPI server...")
    print(f"PDF Support: {PDF_SUPPORT}")
    print(f"Upload folder: {UPLOAD_FOLDER}")
    print(f"API Documentation: http://localhost:5000/docs")

    uvicorn.run(
        app,
        host="localhost",
        port=5000,
        log_level="info"
    )