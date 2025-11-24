import requests
import json
import os
import base64
import logging
import re
from typing import List, Dict, Any, Optional, Tuple

logging.basicConfig(level= logging.INFO)
logger= logging.getLogger(__name__)


class ExtractionModel:
    """
    Primary model for extracting ALL exam information from documents.
    Uses enhanced prompts for accurate OCR and structured data extraction.
    """

    def __init__(self, api_key: str, url_endpoint: str):
        self.API_KEY= api_key
        self.URL= url_endpoint
        self.headers= {
            "Content-Type": "application/json",
            "X-goog-api-key": self.API_KEY
        }
        self.response= None

    def _get_extraction_prompt(self) -> str:
        """Returns the enhanced extraction prompt optimized for exam schedules. This prompt is designed for maximum accuracy and completeness."""
        
        return """
        You are an expert exam schedule data extractor. Extract ALL exams with CORRECT dates and times.

        ## TABLE STRUCTURE (6 COLUMNS)
        | Date | Session | Time | Offered To | Level-Major | Course Code | Course Name |

        ## CRITICAL: MERGED CELL RULES

        The Date, Session, and Time columns have MERGED CELLS spanning multiple rows.
        - When you see a date (e.g., "Tuesday 23/12/2025"), it applies to ALL courses until the NEXT date appears
        - When you see a session (e.g., "Session 1"), it applies to ALL courses until "Session 2" appears
        - When you see a time (e.g., "9:00 to 11:30"), it applies to ALL courses in that session

        ## READING THE TABLE ROW BY ROW

        For EACH row, determine:
        1. **Current Date**: What date is this row under? (Look UP to find the nearest date)
        2. **Current Session**: Is this Session 1 or Session 2? (Look UP to find)
        3. **Current Time**: What time slot? (Session 1 = morning 9:00, Session 2 = afternoon 12:00)
        4. **Offered To**: Read directly from the row
        5. **Level**: Read directly from the row
        6. **Course Code**: Read directly from the row
        7. **Course Name**: Read directly from the row

        ## IMPORTANT: SESSION AND TIME MAPPING
        - **Session 1** times: "9:00 to 11:00" OR "9:00 to 11:30"
        - **Session 2** times: "12:00 to 2:00"

        If you see multiple courses BEFORE "Session 2" appears, they are ALL in Session 1 with the Session 1 time!

        ## EXAMPLE OF CORRECT EXTRACTION

        If the table shows:
        ```
        Tuesday    | Session 1 | 9:00 to 11:30 | CS  | 5 | MATH306 | Logic Proof
        23/12/2025 |           |               | CS  | 7 | MATH401 | Logic Proof  
                |           |               | CYS | 5 | CYS 301 | Math Found.
                |           |               | CIS | 5 | CIS 308 | IT Project Mgmt  ← STILL Session 1!
                |           |               | CIS | 7 | CIS 414 | IT Project Mgmt
                | Session 2 | 12:00 to 2:00 | ALL | 3 | STAT238 | Statistics  ← NOW Session 2 starts
        ```

        Correct extraction:
        - MATH306: Date=23/12/2025, Time=9:00 to 11:30
        - MATH401: Date=23/12/2025, Time=9:00 to 11:30
        - CYS 301: Date=23/12/2025, Time=9:00 to 11:30
        - CIS 308: Date=23/12/2025, Time=9:00 to 11:30 ← SAME TIME as above (still Session 1)
        - CIS 414: Date=23/12/2025, Time=9:00 to 11:30
        - STAT238: Date=23/12/2025, Time=12:00 to 2:00 ← NEW TIME (Session 2 started)

        ## OUTPUT FORMAT
        Return ONLY valid JSON array:

        [
            {
                "Date": "21/12/2025",
                "Time": "9:00 to 11:00",
                "Major-Level": "5",
                "Offered To": "ALL",
                "Course Code": "CSC331",
                "Course Name": "Operating Systems"
            }
        ]

        ## DATA CLEANING
        - Times: NO extra spaces - "9:00 to 11:00" not "9 : 0 0 to 11:00"
        - Majors: Uppercase, comma-separated - "AI,CS" not "AI/CS"
        - Levels: Numbers only - "5" not "Level 5"
        - Multiple levels: "5,7" format

        ## SELF-CHECK BEFORE RESPONDING
        1. Did each course get the CORRECT date from its merged cell section?
        2. Did each course get the CORRECT time based on Session 1 or Session 2?
        3. Are courses BEFORE "Session 2" getting Session 1 time (morning)?
        4. Are courses AFTER "Session 2" getting Session 2 time (afternoon)?

        EXTRACT ALL EXAMS NOW WITH CORRECT DATES AND TIMES!
        """

    def _get_image_extraction_prompt(self) -> str:
        """Returns enhanced prompt specifically optimized for image OCR extraction."""
        
        return """
        You are an expert OCR system extracting exam schedules from images. Pay EXTREME attention to merged cells.

        ## TABLE STRUCTURE (Read Left to Right)
        | Date | Session | Time | Offered To | Level | Course Code | Course Name |

        ## CRITICAL: UNDERSTANDING MERGED CELLS

        This table has MERGED CELLS in the first 3 columns:
        - **Date**: One date spans MANY course rows (10-20 rows!)
        - **Session**: "Session 1" or "Session 2" spans several course rows
        - **Time**: Time slot spans all courses in that session

        ## HOW TO READ MERGED CELLS CORRECTLY

        ### Step 1: Identify Date Boundaries
        Look at the leftmost column. Each date block contains multiple sessions and courses.
        Dates in this schedule: 21/12, 22/12, 23/12, 24/12, 25/12, 28/12, 29/12, 30/12, 31/12, 01/01, 04/01

        ### Step 2: Identify Sessions Within Each Date
        Within each date, find "Session 1" and "Session 2":
        - Session 1 = Morning (typically 9:00 to 11:00 or 9:00 to 11:30)
        - Session 2 = Afternoon (typically 12:00 to 2:00)

        ### Step 3: Assign Time to Each Course
        IMPORTANT: A course belongs to Session 1 until you see "Session 2" appear!

        Example:
        ```
        Tuesday    | Session 1 | 9:00-11:30 | CS  | 5 | MATH306 | Logic       ← Session 1
        23/12/2025 |           |            | CYS | 5 | CYS301  | Math Found  ← Session 1 (same!)
                |           |            | CIS | 5 | CIS308  | IT Project  ← Session 1 (same!)
                |           |            | CIS | 7 | CIS414  | IT Project  ← Session 1 (same!)
                | Session 2 | 12:00-2:00 | ALL | 3 | STAT238 | Statistics  ← Session 2 (NEW!)
                |           |            | CIS | 9 | CIS512  | Software QA ← Session 2 (same!)
        ```

        In this example:
        - CIS 308 gets: Date=23/12/2025, Time=9:00 to 11:30 (because it's BEFORE Session 2)
        - STAT238 gets: Date=23/12/2025, Time=12:00 to 2:00 (because it's AFTER Session 2 marker)

        ## KEY COURSES TO GET RIGHT (CIS Level 5)
        Make sure these specific courses have correct dates/times:
        - CSC331 (Operating Systems) - Should be 21/12/2025, Session 1
        - CIS 308 (IT Project Management) - Should be 23/12/2025, Session 1 (9:00 to 11:30)
        - CIS 302 (System Analysis) - Check which date/session
        - CIS 306 (Data Management) - Check which date/session  
        - CIS 304+326 (IT Infrastructure) - Check which date/session

        ## OUTPUT FORMAT
        Return ONLY valid JSON array:

        [
            {
                "Date": "23/12/2025",
                "Time": "9:00 to 11:30",
                "Major-Level": "5",
                "Offered To": "CIS",
                "Course Code": "CIS 308",
                "Course Name": "Information Technology Project Management"
            }
        ]

        ## DATA CLEANING RULES
        - Remove spaces in times: "9 : 0 0" → "9:00"
        - Normalize majors: "AI/CS" → "AI,CS"
        - Level as numbers: "5" not "Level 5"

        ## VERIFICATION CHECKLIST
        Before outputting, verify:
        ✓ Is CIS 308 on 23/12/2025 with time 9:00 to 11:30? (Session 1)
        ✓ Does every course have a date?
        ✓ Are Session 1 courses getting morning times (9:00)?
        ✓ Are Session 2 courses getting afternoon times (12:00)?

        EXTRACT ALL EXAMS WITH CORRECT DATE AND TIME ASSIGNMENTS!
        """

    def extract_from_text(self, text: str) -> str:
        """
        Extract exam data from text content (PDFs).
        
        Args:
            text: Text content extracted from PDF
            
        Returns:
            JSON string with extracted exam data
        """
        logger.info("Extracting exams from text content")
        
        prompt= f"""
        {self._get_extraction_prompt()}

        ## DOCUMENT CONTENT TO PROCESS:
        {text}
        """

        data= {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.1,  # Low temperature for accuracy
                "topP": 0.8,
                "maxOutputTokens": 8192
            }
        }

        return self._send_request(data)

    def extract_from_image(self, image_path: str) -> str:
        """
        Extract exam data from image using vision capabilities.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            JSON string with extracted exam data
        """
        logger.info(f"Extracting exams from image: {image_path}")

        # Read and encode image
        with open(image_path, "rb") as image_file:
            image_data= base64.b64encode(image_file.read()).decode("utf-8")

        # Determine MIME type
        mime_type= self._get_mime_type(image_path)

        data= {
            "contents": [{
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": image_data
                        }
                    },
                    {
                        "text": self._get_image_extraction_prompt()
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "topP": 0.8,
                "maxOutputTokens": 8192
            }
        }

        return self._send_request(data)

    def extract_from_pdf_images(self, image_paths: List[str]) -> str:
        """
        Extract exam data from multiple PDF page images.
        Processes each page and combines results.
        
        Args:
            image_paths: List of paths to page images
            
        Returns:
            Combined JSON string with all extracted exams
        """
        logger.info(f"Extracting from {len(image_paths)} PDF page images")
        
        all_exams= []
        
        for i, image_path in enumerate(image_paths):
            logger.info(f"Processing page {i + 1}/{len(image_paths)}")
            try:
                response= self.extract_from_image(image_path)
                page_exams= self._parse_json_response(response)
                all_exams.extend(page_exams)
            except Exception as e:
                logger.error(f"Error processing page {i + 1}: {e}")
                continue
        
        return json.dumps(all_exams)

    def _get_mime_type(self, file_path: str) -> str:
        """Determine MIME type from file extension."""
        ext= file_path.lower().split('.')[-1]
        mime_types= {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "bmp": "image/bmp",
            "webp": "image/webp",
            "tiff": "image/tiff",
            "tif": "image/tiff"
        }
        return mime_types.get(ext, "image/jpeg")

    def _send_request(self, data: dict) -> str:
        """Send request to Gemini API and return response."""
        logger.info("Sending request to Gemini model")
        
        response= requests.post(self.URL, headers=self.headers, data=json.dumps(data), timeout=120)

        if response.status_code != 200:
            logger.error(f"API request failed: {response.status_code} - {response.text}")
            raise Exception(f"API request failed: {response.status_code}")

        json_response= response.json()

        try:
            text_response= json_response["candidates"][0]["content"]["parts"][0]["text"]
            self.response= text_response
            return text_response
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to parse response: {e}")
            logger.error(f"Response: {json.dumps(json_response, indent= 2)}")
            raise Exception(f"Failed to parse Gemini response: {e}")

    def _parse_json_response(self, response: str) -> List[Dict]:
        """Parse JSON from model response, handling markdown code blocks."""
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
        
        # Parse JSON
        return json.loads(response)


class FilterModel:
    """
    Secondary model for filtering extracted events based on user criteria.
    This handles the filtering logic for Major-Level and Offered To fields.
    """

    def __init__(self, api_key: str, url_endpoint: str):
        self.API_KEY= api_key
        self.URL= url_endpoint
        self.headers= {
            "Content-Type": "application/json",
            "X-goog-api-key": self.API_KEY
        }

    def filter_events(
        self, 
        events: List[Dict[str, Any]], 
        major_level: Optional[str] = None,
        offered_to: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter events based on user criteria using AI understanding.
        
        Args:
            events: List of all extracted events
            major_level: User's major level (e.g., "1", "2", "3", "4")
            offered_to: User's major (e.g., "SE", "AI", "CIS", "CS", "CYS")
            
        Returns:
            Filtered list of events matching criteria
        """
        # If no filters, return all events
        if not major_level and not offered_to:
            logger.info("No filters provided, returning all events")
            return events

        logger.info(f"Filtering events - Level: {major_level}, Major: {offered_to}")

        prompt = f"""
        You are a STRICT filtering assistant. Filter exam events based on student criteria.

        ## STUDENT CRITERIA
        - Major Level: {major_level if major_level else "Any"}
        - Major/Program: {offered_to if offered_to else "Any"}

        ## STRICT FILTERING RULES

        ### Level Matching (STRICT):
        - ONLY include events where Major-Level EXACTLY matches "{major_level}"
        - If event has multiple levels like "5,7", include ONLY if "{major_level}" is in that list
        - Do NOT include events with different levels (e.g., if student is level 5, do NOT include level 3 or 7)
        - Do NOT include events with empty/missing levels

        ### Major Matching (STRICT):
        - ONLY include events where Offered To contains "{offered_to}" OR is "ALL"
        - "ALL" means the course is for everyone - INCLUDE these
        - If event shows "AI,CS" and student is "CIS", do NOT include (CIS is not in the list)
        - If event shows "CS,CIS" and student is "CIS", INCLUDE (CIS is in the list)
        - Do NOT include events with empty/missing majors

        ### Both Must Match:
        - An event is ONLY included if BOTH level AND major criteria are satisfied
        - If either doesn't match, EXCLUDE the event

        ## EVENTS TO FILTER
        {json.dumps(events, indent= 2)}

        ## OUTPUT
        Return ONLY a JSON array of events that STRICTLY match BOTH criteria.
        Return valid JSON only - no markdown, no explanations.
        If NO events match, return: []
        """

        data= {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 8192
            }
        }

        try:
            response= requests.post(self.URL, headers= self.headers, data= json.dumps(data), timeout= 60)

            if response.status_code != 200:
                logger.error(f"Filter API failed: {response.status_code}")
                # Fall back to local filtering
                return self._local_filter(events, major_level, offered_to)

            json_response= response.json()
            text_response= json_response["candidates"][0]["content"]["parts"][0]["text"]
            
            # Parse filtered results
            filtered= self._parse_json(text_response)
            logger.info(f"AI filtered {len(events)} events to {len(filtered)}")
            return filtered

        except Exception as e:
            logger.error(f"AI filtering failed: {e}, using local filter")
            return self._local_filter(events, major_level, offered_to)

    def _local_filter(
        self, 
        events: List[Dict[str, Any]], 
        major_level: Optional[str],
        offered_to: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Local filtering fallback when AI filtering fails.
        STRICT filtering: Both level AND major must match.
        """
        logger.info("Using local filtering logic (STRICT mode)")
        filtered= []

        for event in events:
            # Get event values
            event_level= str(event.get("Major-Level", event.get("major_level", ""))).strip()
            event_offered= str(event.get("Offered To", event.get("offered_to", ""))).strip().upper()

            # Normalize filter inputs
            filter_level= str(major_level).strip() if major_level else None
            filter_major= str(offered_to).strip().upper() if offered_to else None

            level_match= True
            major_match= True

            # STRICT Level check - must match exactly or be in comma-separated list
            if filter_level:
                # Handle comma-separated levels like "5,7"
                if "," in event_level:
                    event_levels= [l.strip() for l in event_level.split(",")]
                    level_match= filter_level in event_levels
                elif "+" in event_level:
                    event_levels= [l.strip() for l in event_level.split("+")]
                    level_match= filter_level in event_levels
                else:
                    # Exact match required
                    level_match = event_level == filter_level
                
                # Empty level = unknown, don't include
                if event_level == "":
                    level_match= False

            # STRICT Major check
            if filter_major:
                # "ALL" means everyone
                if event_offered == "ALL":
                    major_match= True
                # Empty = unknown, don't include
                elif event_offered == "":
                    major_match= False
                # Check for exact match or in list
                else:
                    # Normalize separators: "/" and "," both mean list
                    event_majors= []
                    if "/" in event_offered:
                        event_majors= [m.strip() for m in event_offered.replace("/", ",").split(",")]
                    elif "," in event_offered:
                        event_majors= [m.strip() for m in event_offered.split(",")]
                    else:
                        event_majors= [event_offered]
                    
                    # Check if filter_major is in the list
                    major_match= filter_major in event_majors

            # BOTH must match
            if level_match and major_match:
                filtered.append(event)
                logger.debug(f"✓ Included: {event.get("course_code", event.get("Course Code", ""))} - Level:{event_level} Offered:{event_offered}")
            else:
                logger.debug(f"✗ Excluded: {event.get("course_code", event.get("Course Code", ""))} - Level:{event_level}(want:{filter_level}) Offered:{event_offered}(want:{filter_major})")

        logger.info(f"STRICT filter: {len(events)} -> {len(filtered)} events")
        return filtered

    def _parse_json(self, response: str) -> List[Dict]:
        """Parse JSON from response."""
        response= response.strip()
        if response.startswith("```json"):
            response= response[7:]
        elif response.startswith("```"):
            response= response[3:]
        if response.endswith("```"):
            response= response[:-3]
        return json.loads(response.strip())


class PromptChat:
    """
    Combined interface for exam extraction and filtering.
    Maintains backward compatibility while using enhanced models.
    """

    def __init__(self, api_key: str, url_endpoint: str):
        self.extraction_model= ExtractionModel(api_key, url_endpoint)
        self.filter_model= FilterModel(api_key, url_endpoint)
        self.response= None

    def get_content(
        self, 
        page: str, 
        is_image: bool = False, 
        image_path: str = None
    ) -> str:
        """
        Extract exam data from content.
        
        Args:
            page: Text content or placeholder for image
            is_image: Whether input is an image
            image_path: Path to image file
            
        Returns:
            JSON string with extracted exams
        """
        if is_image and image_path and os.path.exists(image_path):
            self.response= self.extraction_model.extract_from_image(image_path)
        else:
            self.response= self.extraction_model.extract_from_text(page)
        
        # Save response
        self._save_response()
        return self.response

    def filter_results(
        self, 
        events: List[Dict[str, Any]],
        major_level: Optional[str] = None,
        offered_to: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter extracted events based on user criteria.
        """
        return self.filter_model.filter_events(events, major_level, offered_to)

    def _save_response(self, filename: str = "Response.json"):
        """Save response to file."""
        if self.response:
            backend_folder= os.path.dirname(os.path.abspath(__file__))
            response_path= os.path.join(backend_folder, filename)
            with open(response_path, "w", encoding= "utf-8") as f:
                f.write(self.response)
            logger.info(f"Response saved to {response_path}")