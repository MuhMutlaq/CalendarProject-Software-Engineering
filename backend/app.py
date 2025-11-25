import os
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from dateutil.parser import parse, ParserError

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "secrets", ".env"))

# Setup logging for debugging
import logging
logging.basicConfig(level= logging.INFO)
logger= logging.getLogger(__name__)

# Import our enhanced modules
from model import PromptChat, ExtractionModel, FilterModel
from image_preprocessor import ImagePreprocessor, CV2_AVAILABLE

# PDF Support for text extraction
try:
    from PyPDF2 import PdfReader
    PDF_TEXT_SUPPORT= True
except ImportError:
    PDF_TEXT_SUPPORT= False
    logger.warning("PyPDF2 not installed. PDF text extraction will be limited.")

# PDF to Image support ("poppler" is REQUIRED)
try:
    from pdf2image import convert_from_path
    PDF_IMAGE_SUPPORT= True
except ImportError:
    PDF_IMAGE_SUPPORT= False
    logger.warning("pdf2image not installed. PDF image conversion not available.")

# Initialize FastAPI app
app = FastAPI(
    title= "Enhanced Calendar Event Extractor API",
    description= "Extract dates and events from images and PDFs with AI-powered OCR",
    version= "2.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins= ["*"], # For more security specify the origin domains
    allow_credentials= True,
    allow_methods= ["*"],
    allow_headers= ["*"],
)

# Configuration
UPLOAD_FOLDER= 'uploads'
PROCESSED_FOLDER= 'processed_images'
PDF_PAGES_FOLDER= 'pdf_pages'
ALLOWED_IMAGE_EXTENSIONS= {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}
ALLOWED_DOCUMENT_EXTENSIONS= {'pdf'}
MAX_FILE_SIZE= 50 * 1024 * 1024  # 50 MB for larger documents

# Ensure folders exist
for folder in [UPLOAD_FOLDER, PROCESSED_FOLDER, PDF_PAGES_FOLDER]:
    os.makedirs(folder, exist_ok= True)

# Gemini API Configuration
GEMINI_API_KEY= os.getenv("GEMINI_API_KEY")
GEMINI_URL= os.getenv("GEMINI_MODEL_URL")

# Initialize models
extraction_model= None
filter_model= None
gemini_chat= None

if GEMINI_API_KEY and GEMINI_URL:
    extraction_model= ExtractionModel(api_key= GEMINI_API_KEY, url_endpoint= GEMINI_URL)
    filter_model= FilterModel(api_key= GEMINI_API_KEY, url_endpoint= GEMINI_URL)
    gemini_chat= PromptChat(api_key= GEMINI_API_KEY, url_endpoint= GEMINI_URL)
    logger.info("✅ Gemini AI Models initialized successfully!")
else:
    logger.error("❌ GEMINI_API_KEY or GEMINI_MODEL_URL not found. AI extraction will not work.")


def allowed_file(filename: str, file_type: str= 'image') -> bool:
    """Check if the file extension is allowed."""
    
    if '.' not in filename:
        return False
    
    ext= filename.rsplit('.', 1)[1].lower()
    
    if file_type == 'image':
        return ext in ALLOWED_IMAGE_EXTENSIONS
    elif file_type == 'document':
        return ext in ALLOWED_IMAGE_EXTENSIONS or ext in ALLOWED_DOCUMENT_EXTENSIONS
    
    return False


def get_file_extension(filename: str) -> str:
    """Get file extension in lowercase."""
    
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using PyPDF2."""
    if not PDF_TEXT_SUPPORT:
        return ""
    
    text= ""
    try:
        pdf_reader= PdfReader(pdf_path)
        for page in pdf_reader.pages:
            page_text= page.extract_text()
            if page_text:
                text+= page_text + "\n"
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
    
    return text.strip()


def convert_pdf_to_images(pdf_path: str) -> List[str]:
    """Convert PDF pages to high-resolution images for OCR."""
    
    if not PDF_IMAGE_SUPPORT:
        logger.warning("pdf2image not available")
        return []
    
    image_paths= []
    try:
        # Use higher DPI (400) for maximum text clarity and table line visibility
        images= convert_from_path(pdf_path, dpi= 400)
        
        for i, image in enumerate(images):
            output_path= os.path.join(PDF_PAGES_FOLDER, f"page_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i + 1}.png")
            image.save(output_path, 'PNG')
            image_paths.append(output_path)
            logger.info(f"Converted PDF page {i + 1} to high-res image (400 DPI)")
    
    except Exception as e:
        logger.error(f"Error converting PDF to images: {e}")
    
    return image_paths


def preprocess_image(image_path: str) -> str:
    """Apply minimal preprocessing to preserve table structure for AI vision."""
    
    if not CV2_AVAILABLE:
        logger.warning("OpenCV not available, skipping preprocessing")
        return image_path
    
    try:
        preprocessor= ImagePreprocessor(output_dir= PROCESSED_FOLDER)
        # MINIMAL preprocessing to preserve original table structure because Heavy binarization can destroy session boundary information
        processed_path= preprocessor.preprocess_minimal(image_path)
        return processed_path
    except Exception as e:
        logger.error(f"Image preprocessing failed: {e}")
        return image_path


def parse_ai_response(response: str) -> List[Dict[str, Any]]:
    """Parse JSON response from AI model."""
    
    # Clean up response
    response= response.strip()
    
    # Remove markdown code blocks
    if response.startswith("```json"):
        response= response[7:]
    elif response.startswith("```"):
        response= response[3:]
    if response.endswith("```"):
        response= response[:-3]
    response= response.strip()
    
    try:
        data= json.loads(response)
        
        # Handle different response structures
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # Try common keys
            for key in ["exams", "events", "data", "results"]:
                if key in data and isinstance(data[key], list):
                    return data[key]
            # Return single item as list
            return [data]
        
        return []
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        logger.error(f"Response: {response[:500]}...")
        return []


def normalize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize event data to standard format."""
    
    # Map different key formats to standard format
    date_keys= ["Date", "date", "exam_date", "Exam Date"]
    time_keys= ["Time", "time", "exam_time", "Exam Time"]
    level_keys= ["Major-Level", "major_level", "Major Level", "level", "Level", "Year", "Level-Major"]
    major_keys= ["Offered To", "offered_to", "Offered_To", "major", "Major", "Program"]
    code_keys= ["Course Code", "course_code", "Course_Code", "code", "Code"]
    name_keys= ["Course Name", "course_name", "Course_Name", "name", "Name", "Title"]
    
    def get_value(keys):
        for key in keys:
            if key in event and event[key]:
                return str(event[key]).strip()
        return ""
    
    # Extract fields
    date_str= get_value(date_keys)
    time_str= get_value(time_keys)
    level_str= get_value(level_keys)
    major_str= get_value(major_keys)
    code_str= get_value(code_keys)
    name_str= get_value(name_keys)
    
    # Clean up time format - remove extra spaces like "9 : 0 0" -> "9:00"
    if time_str:
        # Remove spaces around colons: "9 : 00" -> "9:00"
        time_str= re.sub(r'\s*:\s*', ':', time_str)
        # Remove spaces in numbers: "9 0 0" -> "900" (unlikely but handle)
        time_str= re.sub(r'(\d)\s+(\d)', r'\1\2', time_str)
        # Normalize "to" spacing
        time_str= re.sub(r'\s+to\s+', ' to ', time_str)
    
    # Clean up level - extract just the number(s)
    if level_str:
        # Handle formats like "Level 5", "5", "5,7", "5+7"
        level_str= level_str.replace("Level", "").replace("level", "").strip()
        # Normalize separators
        level_str= level_str.replace("+", ",")
    
    # Clean up major - normalize format
    if major_str:
        # Normalize to uppercase and replace / with ,
        major_str= major_str.upper().replace("/", ",")
        # Clean up spaces
        if "," in major_str:
            parts= [p.strip() for p in major_str.split(",")]
            major_str= ",".join(parts)
    
    # Parse date to ISO format
    iso_date= date_str
    if date_str:
        try:
            parsed_date= parse(date_str, fuzzy= True, dayfirst= True)
            iso_date= parsed_date.date().isoformat()
        except (ParserError, ValueError):
            pass
    
    # Create title
    if code_str and name_str:
        title= f"{code_str}: {name_str}"
    elif name_str:
        title= name_str
    elif code_str:
        title= code_str
    else:
        title= "Exam"
    
    # Create description
    description_parts= []
    if date_str:
        description_parts.append(f"Date: {date_str}")
    if time_str:
        description_parts.append(f"Time: {time_str}")
    if level_str:
        description_parts.append(f"Major-Level: {level_str}")
    if major_str:
        description_parts.append(f"Offered To: {major_str}")
    
    return {
        "date": iso_date,
        "time": time_str,
        "title": title,
        "description": "\n".join(description_parts),
        "course_code": code_str,
        "course_name": name_str,
        "major_level": level_str,
        "offered_to": major_str,
        "confidence": 0.95
    }


def extract_all_events_from_file(file_path: str, filename: str) -> List[Dict[str, Any]]:
    """
    STAGE 1: Extract ALL events from file without any filtering.
    For PDFs with complex tables, prioritize image-based extraction.
    """
    
    if not extraction_model:
        raise ValueError("AI model not initialized")
    
    ext= get_file_extension(filename)
    all_events= []
    
    if ext == 'pdf':
        logger.info("Processing PDF file...")
        
        # Strategy 1: PRIORITIZE IMAGE EXTRACTION for complex table PDFs
        # This preserves the visual table structure better
        if PDF_IMAGE_SUPPORT:
            logger.info("Using image-based extraction for better table structure...")
            
            # Convert PDF pages to images
            page_images= convert_pdf_to_images(file_path)
            
            if page_images:
                for i, page_image in enumerate(page_images):
                    logger.info(f"Processing PDF page {i + 1} as image...")
                    
                    # Preprocess each page
                    processed_image= preprocess_image(page_image)
                    
                    # Extract from preprocessed image
                    response= extraction_model.extract_from_image(processed_image)
                    page_events= parse_ai_response(response)
                    
                    for event in page_events:
                        normalized= normalize_event(event)
                        # Skip events with no course code (likely parsing errors)
                        if normalized.get('course_code'):
                            # Avoid duplicates
                            if not any(e['course_code'] == normalized['course_code'] and e['date'] == normalized['date'] for e in all_events):
                                all_events.append(normalized)
                    
                    # Clean up
                    try:
                        os.remove(page_image)
                        if processed_image != page_image:
                            os.remove(processed_image)
                    except:
                        pass
        
        # Strategy 2: Fall back to text extraction if image conversion fails or yields few results
        if len(all_events) < 5:
            logger.info("Trying text extraction as fallback...")
            text= extract_text_from_pdf(file_path)
            
            if text and len(text) > 100:
                logger.info(f"Extracted {len(text)} characters of text from PDF")
                response= extraction_model.extract_from_text(text)
                raw_events= parse_ai_response(response)
                
                for event in raw_events:
                    normalized= normalize_event(event)
                    if normalized.get('course_code'):
                        if not any(e['course_code'] == normalized['course_code'] and e['date'] == normalized['date'] for e in all_events):
                            all_events.append(normalized)
    
    else:
        # Image file processing
        logger.info(f"Processing image file: {filename}")
        
        # Preprocess image for better OCR
        processed_image= preprocess_image(file_path)
        
        # Extract using vision model
        response= extraction_model.extract_from_image(processed_image)
        raw_events= parse_ai_response(response)
        
        for event in raw_events:
            normalized= normalize_event(event)
            if normalized.get('course_code'):
                all_events.append(normalized)
        
        # Clean up processed image
        if processed_image != file_path:
            try:
                os.remove(processed_image)
            except:
                pass
    
    # Post-processing: Validate and clean up events
    all_events= validate_and_fix_events(all_events)
    
    logger.info(f"STAGE 1 Complete: Extracted {len(all_events)} total events")
    return all_events


def validate_and_fix_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Post-process events to validate data quality.
    """
    
    valid_events= []
    
    for event in events:
        # Skip events without course code (likely parsing errors)
        if not event.get('course_code'):
            continue
        
        # Skip events without date
        if not event.get('date'):
            logger.warning(f"Skipping event without date: {event.get('course_code')}")
            continue
        
        # Validate date is in expected range (Dec 2025 - Jan 2026 for this schedule)
        date_str= event.get('date', '')
        if date_str:
            try:
                from datetime import datetime as dt
                if '-' in date_str:
                    date_obj= dt.strptime(date_str, '%Y-%m-%d')
                elif '/' in date_str:
                    date_obj= dt.strptime(date_str, '%d/%m/%Y')
                else:
                    date_obj= None
                
                if date_obj:
                    if date_obj.year < 2025 or date_obj.year > 2026:
                        logger.warning(f"Suspicious date for {event.get('course_code')}: {date_str}")
            except Exception as e:
                logger.warning(f"Date parsing error: {e}")
        
        valid_events.append(event)
    
    return valid_events


def parse_level_major_pairs(level_str: str) -> List[Tuple[str, Optional[str]]]:
    """
    Parse complex level formats into (level, major) pairs using regex.
    
    Handles formats like:
    - "5" -> [("5", None)]
    - "5,7" -> [("5", None), ("7", None)]
    - "5+7" -> [("5", None), ("7", None)]
    - "5-7" -> [("5", None), ("7", None)]
    - "7 (AI) 9 (CS) 9(CYS)" -> [("7", "AI"), ("9", "CS"), ("9", "CYS")]
    - "5 (CS)-7(CS)" -> [("5", "CS"), ("7", "CS")]
    - "5 (A1)-7(ΑΙ)" -> [("5", "A1"), ("7", "AI")]
    
    Uses \\s* to handle 0 or more spaces between elements.
    
    Returns list of (level, major) tuples where major can be None
    """
    
    if not level_str:
        return []
    
    pairs= []
    
    # Pattern: digit(s) with optional (MAJOR) - flexible spacing with \s*
    # Matches: "5", "5 (CS)", "5(CS)", "5 ( CS )", etc.
    # Pattern breakdown:
    # (\d+)           - capture one or more digits (the level)
    # \s*             - zero or more whitespace
    # (?:             - non-capturing group for optional (MAJOR)
    #   \(\s*         - opening parenthesis with optional space
    #   ([^)]+?)      - capture the major (any chars except closing paren, non-greedy)
    #   \s*\)         - optional space and closing parenthesis
    # )?              - the whole (MAJOR) part is optional
    pattern= r'(\d+)\s*(?:\(\s*([^)]+?)\s*\))?'
    
    matches= re.findall(pattern, level_str)
    
    for match in matches:
        level= match[0].strip()
        major= match[1].strip().upper() if match[1] else None
        if level: # Only add if we have a valid level
            pairs.append((level, major))
    
    return pairs


def check_level_match(event_level: str, filter_level: str, filter_major: str) -> bool:
    """
    Check if user's level matches the event level.
    
    Handles complex formats like "7 (AI) 9 (CS) 9(CYS)" where different
    levels apply to different majors.
    
    Args:
        event_level: The event's level string (e.g., "5", "5,7", "7 (AI) 9 (CS)")
        filter_level: User's level (e.g., "5")
        filter_major: User's major (e.g., "CS")
    
    Returns:
        True if user's level matches for their major
    """
    
    if not event_level or not filter_level:
        return False
    
    # Parse the level string into (level, major) pairs
    pairs= parse_level_major_pairs(event_level)
    
    if not pairs:
        return False
    
    filter_level= filter_level.strip()
    filter_major_upper= filter_major.strip().upper() if filter_major else None
    
    for level, major in pairs:
        if level == filter_level:
            if major:
                # This level is specific to a major - check if it matches user's major
                if filter_major_upper and major == filter_major_upper:
                    return True
            else:
                # No associated major means this level applies to everyone
                return True
    
    return False


def check_major_match(event_offered: str, filter_major: str) -> bool:
    """
    Check if user's major matches the event's offered_to field.
    
    Handles formats like:
    - "ALL" -> matches everyone
    - "CS" -> matches only CS
    - "CS/CYS" -> matches CS or CYS (split and check each)
    - "AI,CS,CYS" -> matches AI, CS, or CYS
    - "CS,CIS,CYS,AI" -> matches any of these
    
    Args:
        event_offered: The event's offered_to string
        filter_major: User's major
    
    Returns:
        True if user's major is in the event's offered_to list
    """
    
    if not filter_major:
        return False
    
    if not event_offered:
        return False  # Unknown major= exclude
    
    event_offered= event_offered.strip().upper()
    filter_major= filter_major.strip().upper()
    
    # "ALL" means everyone
    if event_offered == "ALL":
        return True
    
    # Split by common separators: / , + - with optional spaces around them
    # Pattern: \s*[/,+-]\s* matches separators with optional surrounding spaces
    majors= re.split(r'\s*[/,+]\s*', event_offered)
    majors= [m.strip() for m in majors if m.strip()]
    
    return filter_major in majors


def filter_events_by_criteria(
    events: List[Dict[str, Any]], # List of the events
    major_level: str, # REQUIRED
    offered_to: str # REQUIRED
) -> List[Dict[str, Any]]:
    """
    STAGE 2: Filter events based on user criteria.
    Uses regex-based parsing for complex level formats.
    STRICT: Both level AND major must match exactly.
    
    When an event has multiple levels (e.g., "5,7"), the returned event
    will have the level normalized to the user's specific level.
    
    Args:
        events: List of all extracted events
        major_level: User's level (REQUIRED)
        offered_to: User's major (REQUIRED)
    
    Returns:
        Filtered list of events matching criteria with normalized levels
    """
    
    if not events:
        return []
    
    if not major_level or not offered_to:
        logger.warning("Both major_level and offered_to are REQUIRED for filtering")
        return []
    
    logger.info(f"STAGE 2: STRICT Filtering {len(events)} events (Level: {major_level}, Major: {offered_to})")
    
    filtered= []
    
    # Normalize filter inputs
    filter_level= str(major_level).strip()
    filter_major= str(offered_to).strip().upper()
    
    for event in events:
        # Get event values
        event_level= str(event.get("major_level", "")).strip()
        event_offered= str(event.get("offered_to", "")).strip().upper()
        
        # Check level match using regex-based parser
        level_match= check_level_match(event_level, filter_level, filter_major)
        
        # Check major match
        major_match= check_major_match(event_offered, filter_major)
        
        # BOTH criteria must match
        if level_match and major_match:
            # Create a copy of the event to avoid modifying original
            filtered_event= event.copy()
            
            # Normalize the level to user's specific level (e.g., "5,7" -> "5" if user is level 5)
            filtered_event["major_level"]= filter_level
            
            # Update description to reflect normalized level
            if filtered_event.get("description"):
                # Replace the Major-Level line in description
                description_lines= filtered_event["description"].split("\n")
                updated_lines= []
                for line in description_lines:
                    if line.startswith("Major-Level:"):
                        updated_lines.append(f"Major-Level: {filter_level}")
                    else:
                        updated_lines.append(line)
                filtered_event["description"]= "\n".join(updated_lines)
            
            filtered.append(filtered_event)
            logger.debug(f"✓ {event.get('course_code')}: L{event_level} -> {filter_level}, M{event_offered} ∋ {filter_major}")
        else:
            logger.debug(f"✗ {event.get('course_code')}: level_match= {level_match}, major_match= {major_match}")
    
    logger.info(f"STRICT filter: {len(events)} -> {len(filtered)} events")
    return filtered


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    
    return {
        "status": "healthy" if extraction_model else "degraded",
        "ai_enabled": extraction_model is not None,
        "pdf_text_support": PDF_TEXT_SUPPORT,
        "pdf_image_support": PDF_IMAGE_SUPPORT,
        "image_preprocessing": CV2_AVAILABLE,
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "message": "Ready for event extraction" if extraction_model else "AI model not configured"
    }


@app.post("/extract-events")
async def extract_events(
    file: UploadFile= File(...), # REQUIRED
    major_level: str= Form(...), # REQUIRED
    offered_to: str= Form(...) # REQUIRED
):
    """
    Extract and filter events from uploaded file.
    
    Two-stage process:
    1. Extract ALL events from document
    2. Filter by user criteria (major_level, offered_to)
    
    Args:
        file: PDF or image file
        major_level: Student's year/level (1-9) - REQUIRED
        offered_to: Student's major (CS, AI, CIS, CYS, etc.) - REQUIRED
    
    Returns:
        Filtered events matching criteria
    """
    
    # Validate required fields
    if not major_level or not major_level.strip():
        raise HTTPException(status_code= 400, detail= "major_level is required")
    
    if not offered_to or not offered_to.strip():
        raise HTTPException(status_code= 400, detail= "offered_to is required")
    
    # Validate AI model
    if not extraction_model:
        raise HTTPException(status_code= 503, detail= "AI model not configured. Set GEMINI_API_KEY and GEMINI_MODEL_URL.")
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code= 400, detail= "No file selected")
    
    if not allowed_file(file.filename, 'document'):
        raise HTTPException(status_code= 400, detail= f"File type not allowed. Supported: {ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DOCUMENT_EXTENSIONS}")
    
    # Read file content
    file_content= await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(status_code= 400, detail= f"File too large. Maximum: {MAX_FILE_SIZE / 1024 / 1024}MB")
    
    try:
        # Save uploaded file
        timestamp= datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename= f"{timestamp}_{file.filename}"
        file_path= os.path.join(UPLOAD_FOLDER, unique_filename)
        
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        logger.info(f"Processing file: {file.filename}")
        logger.info(f"User filters - Level: {major_level}, Major: {offered_to}")
        
        # STAGE 1: Extract ALL events
        all_events= extract_all_events_from_file(file_path, file.filename)
        
        # STAGE 2: Filter by user criteria
        filtered_events= filter_events_by_criteria(all_events, major_level, offered_to)
        
        # Clean up uploaded file
        try:
            os.remove(file_path)
        except:
            pass
        
        # Save extraction results for debugging
        debug_path= os.path.join(UPLOAD_FOLDER, "last_extraction.json")
        with open(debug_path, "w") as f:
            json.dump({
                "filename": file.filename,
                "filters": {"major_level": major_level, "offered_to": offered_to},
                "total_extracted": len(all_events),
                "after_filter": len(filtered_events),
                "all_events": all_events,
                "filtered_events": filtered_events
            }, f, indent= 2)
        
        return {
            "success": True,
            "events": filtered_events,
            "total_extracted": len(all_events),
            "total_after_filter": len(filtered_events),
            "filters_applied": {
                "major_level": major_level,
                "offered_to": offered_to
            },
            "ai_enabled": True
        }
    
    except Exception as e:
        logger.error(f"Error processing file: {e}", exc_info= True)
        raise HTTPException(status_code= 500, detail= f"Error processing file: {str(e)}")


@app.post("/extract-all-events")
async def extract_all_events_endpoint(file: UploadFile= File(...)):
    """
    Extract ALL events from file without any filtering.
    Returns complete extraction for client-side filtering.
    """
    
    if not extraction_model:
        raise HTTPException(status_code= 503, detail= "AI model not configured")
    
    if not file.filename or not allowed_file(file.filename, 'document'):
        raise HTTPException(status_code= 400, detail= "Invalid file")
    
    file_content= await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(status_code= 400, detail= "File too large")
    
    try:
        timestamp= datetime.now().strftime('%Y%m%d_%H%M%S')
        file_path= os.path.join(UPLOAD_FOLDER, f"{timestamp}_{file.filename}")
        
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        # Extract ALL events
        all_events= extract_all_events_from_file(file_path, file.filename)
        
        # Clean up
        try:
            os.remove(file_path)
        except:
            pass
        
        # Collect available filters from extracted data
        majors= set()
        levels= set()
        
        for event in all_events:
            if event.get("offered_to"):
                offered= event["offered_to"].upper()
                if "," in offered:
                    majors.update(m.strip() for m in offered.split(","))
                elif offered != "ALL":
                    majors.add(offered)
            
            if event.get("major_level"):
                level_str= str(event["major_level"]).strip()
                # Split combined levels like "5,7" or "5+7" into individual levels
                # Extract all digit sequences (handles "5", "5,7", "7 (AI) 9 (CS)", etc.)
                individual_levels= re.findall(r'\d+', level_str)
                levels.update(individual_levels)
        
        return {
            "success": True,
            "events": all_events,
            "total_events": len(all_events),
            "available_majors": sorted(list(majors)),
            "available_levels": sorted(list(levels)),
            "ai_enabled": True
        }
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info= True)
        raise HTTPException(status_code= 500, detail= str(e))


@app.post("/filter-events")
async def filter_events_endpoint(
    events: List[Dict[str, Any]],
    major_level: Optional[str]= None,
    offered_to: Optional[str]= None
):
    """
    Filter pre-extracted events by criteria.
    Useful for client-side filtering after initial extraction.
    """
    
    filtered= filter_events_by_criteria(events, major_level, offered_to)
    
    return {
        "success": True,
        "events": filtered,
        "original_count": len(events),
        "filtered_count": len(filtered)
    }


@app.get("/")
async def root():
    """API information."""
    
    return {
        "name": "Enhanced Calendar Event Extractor API",
        "version": "2.0.0",
        "features": [
            "AI-powered extraction (Gemini)",
            "Image preprocessing for better OCR",
            "PDF text and image extraction",
            "Two-stage extract & filter approach",
            "Multi-page document support"
        ],
        "endpoints": {
            "health": "GET /health",
            "extract_events": "POST /extract-events",
            "extract_all": "POST /extract-all-events",
            "filter": "POST /filter-events",
            "docs": "GET /docs"
        }
    }


if __name__ == '__main__':
    import uvicorn
    
    print("\n" + "="*60)
    print("Enhanced Calendar Event Extractor API v2.0")
    print("="*60)
    print(f"PDF Text Support: {PDF_TEXT_SUPPORT}")
    print(f"PDF Image Support: {PDF_IMAGE_SUPPORT}")
    print(f"Image Preprocessing: {CV2_AVAILABLE}")
    print(f"AI Model: {'✅ Ready' if extraction_model else '❌ Not configured'}")
    print("="*60)
    print("API Documentation: http://localhost:5000/docs")
    print("="*60 + "\n")
    
    uvicorn.run(
        app,
        host= "localhost",
        port= 5000,
        log_level= "info"
    )