import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from dateutil.parser import parse, ParserError
from model import PromptChat
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), "secrets", ".env"))

# PDF Support for text extraction
try:
    from PyPDF2 import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("Warning: PyPDF2 not installed. PDF text extraction will be limited.")

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

# Gemini API Configuration
GEMINI_API_KEY= os.getenv("GEMINI_API_KEY")
GEMINI_URL= os.getenv("GEMINI_MODEL_URL")

# Initialize PromptChat if API key is available
gemini_chat = None
if GEMINI_API_KEY:
    gemini_chat = PromptChat(api_key=GEMINI_API_KEY, url_endpoint=GEMINI_URL)
    print("Gemini AI Model initialized successfully!")
else:
    print("Warning: GEMINI_API_KEY not found. AI extraction will not be available.")


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


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using PyPDF2."""
    if not PDF_SUPPORT:
        raise ValueError("PDF support not enabled. Install PyPDF2.")

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
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")

    return text


def extract_text_from_image(image_path: str) -> str:
    """
    For images, we rely on the AI model's vision capabilities.
    Return the image path so it can be processed by the AI model.
    """
    # The AI model will handle image processing directly
    return f"[Image file: {image_path}]"


def filter_events_by_criteria(events: List[Dict[str, Any]], major_level: Optional[str], offered_to: Optional[str]) -> List[Dict[str, Any]]:
    """
    Filter extracted events based on client criteria.
    Args:
        events: List of all extracted events.
        major_level: Student's major level (e.g., "1", "2", "3", "4").
        offered_to: Student's major (e.g., "CS", "SE", "AI", "CIS", "CYS").
    Returns:
        Filtered list of events matching the criteria.
    """
    if not major_level and not offered_to:
        # No filters, return all events
        logger.info("No filters applied, returning all events")
        return events

    filtered_events = []

    for event in events:
        event_level = str(event.get("major_level", "")).strip()
        event_offered_to = str(event.get("offered_to", "")).strip().upper()

        # Normalize inputs
        filter_level = str(major_level).strip() if major_level else None
        filter_major = str(offered_to).strip().upper() if offered_to else None

        # Apply filtering logic
        level_match = True
        major_match = True

        # Check major level
        if filter_level:
            level_match = (event_level == filter_level)

        # Check offered to (major)
        if filter_major:
            # "All" means it applies to all majors
            if event_offered_to == "ALL":
                major_match = True
            # Check if the event's offered_to matches the filter
            elif filter_major in event_offered_to or event_offered_to in filter_major:
                major_match = True
            # Check for multi-major entries (e.g., "CS, SE")
            elif "," in event_offered_to:
                # Split and check if filter_major is in the list
                offered_list = [m.strip() for m in event_offered_to.split(",")]
                major_match = filter_major in offered_list
            else:
                major_match = False

        # Include event only if both conditions match
        if level_match and major_match:
            filtered_events.append(event)

    logger.info(f"Filtered {len(events)} events down to {len(filtered_events)} events")
    return filtered_events


def extract_events_with_ai(text: str, is_image: bool = False, image_path: str = None) -> List[Dict[str, Any]]:
    """
    Extract ALL events using AI model (Gemini).
    Returns structured JSON with ALL course information (no filtering).
    Args:
        text (str): The text content from PDF or placeholder for image.
        is_image (bool): Whether the input is an image file.
        image_path (str): Path to the image file if is_image is True.
    Returns:
        List of ALL events extracted from the content.
    """
    if not gemini_chat:
        raise ValueError("AI model not initialized. Please set GEMINI_API_KEY environment variable.")

    try:
        # Get AI response (extract everything)
        response = gemini_chat.get_content(
            page=text,
            is_image=is_image,
            image_path=image_path
        )

        # Parse JSON response from AI
        # Remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        # Parse JSON
        data = json.loads(response)

        # Convert to event format
        events = []

        # Handle different JSON structures
        if isinstance(data, list):
            exam_list = data
        elif isinstance(data, dict) and "exams" in data:
            exam_list = data["exams"]
        elif isinstance(data, dict) and "events" in data:
            exam_list = data["events"]
        else:
            # Try to extract any array from the dict
            for key, value in data.items():
                if isinstance(value, list):
                    exam_list = value
                    break
            else:
                exam_list = [data] if data else []

        for exam in exam_list:
            # Extract fields from the exam
            course_code = exam.get("Course Code", exam.get("course_code", ""))
            course_name = exam.get("Course Name", exam.get("course_name", ""))
            date_str = exam.get("Date", exam.get("date", ""))
            time_str = exam.get("Time", exam.get("time", ""))
            major_level_str = exam.get("Major-Level", exam.get("major_level", ""))
            offered_to_str = exam.get("Offered To", exam.get("offered_to", ""))

            # Create title from course code and name
            title = f"{course_code}: {course_name}" if course_code and course_name else course_name or course_code or "Event"

            # Create description with all details
            description_parts = []
            if date_str:
                description_parts.append(f"Date: {date_str}")
            if time_str:
                description_parts.append(f"Time: {time_str}")
            if major_level_str:
                description_parts.append(f"Major-Level: {major_level_str}")
            if offered_to_str:
                description_parts.append(f"Offered To: {offered_to_str}")

            description = "\n".join(description_parts)

            # Parse date to ISO format
            iso_date = date_str
            if date_str:
                try:
                    parsed_date = parse(date_str, fuzzy=True)
                    iso_date = parsed_date.date().isoformat()
                except (ParserError, ValueError):
                    # Keep original date string if parsing fails
                    pass

            events.append({
                "date": iso_date,
                "time": time_str,
                "title": title,
                "description": description,
                "course_code": course_code,
                "course_name": course_name,
                "major_level": major_level_str,
                "offered_to": offered_to_str,
                "confidence": 0.95  # High confidence for AI extraction
            })

        return events

    except json.JSONDecodeError as e:
        print(f"Error parsing AI response as JSON: {e}")
        print(f"Response was: {response}")
        raise ValueError(f"AI returned invalid JSON: {str(e)}")
    except Exception as e:
        print(f"Error in AI extraction: {e}")
        raise


def extract_events_from_file(file_path: str, filename: str, major_level: Optional[str] = None, offered_to: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Main function to extract events from uploaded file using AI model.
    Uses a two-stage approach:
    1. Extract ALL events from the file using AI
    2. Filter events based on client criteria

    Args:
        file_path (str): Path to the uploaded file.
        filename (str): Name of the uploaded file.
        major_level (Optional[str]): Student's major level (e.g., "1", "2", "3", "4").
        offered_to (Optional[str]): Student's major (e.g., "CS", "SE", "AI").
    Returns:
        List of extracted and filtered events.
    """

    # Check if AI model is available
    if not gemini_chat:
        raise ValueError("AI model not initialized. Please set GEMINI_API_KEY environment variable.")

    # STAGE 1: Extract ALL events from the file
    logger.info("Stage 1: Extracting all events from file")

    # Determine file type and process accordingly
    is_image = not filename.lower().endswith('.pdf')

    if is_image:
        # For images, pass the file path to the model for vision processing
        logger.info(f"Processing image file: {filename}")
        text = f"[Image file: {file_path}]"
        all_events = extract_events_with_ai(
            text=text,
            is_image=True,
            image_path=file_path
        )
    else:
        # For PDFs, extract text first
        logger.info(f"Processing PDF file: {filename}")
        text = extract_text_from_pdf(file_path)

        if not text.strip():
            raise ValueError("No text could be extracted from the PDF file.")

        all_events = extract_events_with_ai(
            text=text,
            is_image=False,
            image_path=None
        )

    logger.info(f"Extracted {len(all_events)} total events from file")

    # STAGE 2: Filter events based on client criteria
    logger.info("Stage 2: Filtering events based on client criteria")
    filtered_events = filter_events_by_criteria(all_events, major_level, offered_to)

    logger.info(f"Returning {len(filtered_events)} events after filtering")
    return filtered_events


# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy" if gemini_chat else "degraded",
        "ai_enabled": gemini_chat is not None,
        "pdf_support": PDF_SUPPORT,
        "timestamp": datetime.now().isoformat(),
        "framework": "FastAPI",
        "message": "AI model is required for event extraction" if not gemini_chat else "Ready"
    }


@app.post("/extract-events")
async def extract_events(
    file: UploadFile = File(...),
    major_level: Optional[str] = Form(None),
    offered_to: Optional[str] = Form(None)
):
    """
    Extract events from uploaded image or PDF file using AI model.

    Args:
        file: Image or PDF file to process
        major_level: Student's major level (e.g., "1", "2", "3", "4")
        offered_to: Student's major (e.g., "Computer Science", "Software Engineering")

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

        # Extract events from file (major_level is kept as string)
        events = extract_events_from_file(file_path, file.filename, major_level, offered_to)

        # Clean up uploaded file
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Error removing file: {e}")

        return {
            "success": True,
            "events": events,
            "total_events": len(events),
            "ai_enabled": gemini_chat is not None
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