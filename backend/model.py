import requests
import json
import os
import base64
import re
from typing import List, Dict, Any, Optional, Tuple

import logging
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
        """
        Returns the enhanced extraction prompt optimized for exam schedules.
        This prompt is designed for maximum accuracy and completeness.
        """
        
        return """
        You are an expert exam schedule data extractor. Extract ALL exams with CORRECT dates and times.

        ## TABLE STRUCTURE (6 COLUMNS)
        | Date | Session | Time | Offered To | Level-Major | Course Code | Course Name |

        ## CRITICAL: SESSION BOUNDARY RULES

        Each day has TWO sessions:
        - **Session 1** = Morning (9:00 to 11:00 or 9:00 to 11:30)
        - **Session 2** = Afternoon (12:00 to 2:00)

        ### READING RULE:
        1. Find "Session 1" marker → All courses below it until "Session 2" get the Session 1 TIME
        2. Find "Session 2" marker → All courses below it until next date get the Session 2 TIME

        ### EXAMPLE - Tuesday 23/12/2025:
        ```
        Session 1 | 9:00-11:30 | CS  | 5 | MATH306 | Logic Proof        ← TIME: 9:00 to 11:30
                |            | CS  | 7 | MATH401 | Logic Proof        ← TIME: 9:00 to 11:30
                |            | CYS | 7 | CYS 402 | Math Foundations   ← TIME: 9:00 to 11:30
                |            | CYS | 5 | CYS 301 | Math Foundations   ← TIME: 9:00 to 11:30
                |            | CIS | 5 | CIS 308 | IT Project Mgmt    ← TIME: 9:00 to 11:30 !!!
                |            | CIS | 7 | CIS 414 | IT Project Mgmt    ← TIME: 9:00 to 11:30
        Session 2 | 12:00-2:00 | AI  | 7 | ARTI401 | AI Principles      ← TIME: 12:00 to 2:00 (Session 2 starts here!)
        ```

        ## KEY POINT:
        CIS 308 and CIS 414 are in Session 1 (morning) on 23/12/2025!
        Their time is 9:00 to 11:30, NOT 12:00 to 2:00!

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

        ## MANDATORY VERIFICATION CHECKLIST
        Before outputting, verify these specific courses have CORRECT times:

        | Course | Date | Correct Time | Session |
        |--------|------|--------------|---------|
        | CIS 308 | 23/12/2025 | 9:00 to 11:30 | Session 1 (morning) |
        | CIS 414 | 23/12/2025 | 9:00 to 11:30 | Session 1 (morning) |
        | ARTI 401 | 23/12/2025 | 12:00 to 2:00 | Session 2 (afternoon) |

        If your extraction shows CIS 308 with time "12:00 to 2:00", that is WRONG! Go back and fix it.

        EXTRACT ALL EXAMS NOW WITH CORRECT SESSION TIMES!
        """

    def _get_image_extraction_prompt(self) -> str:
        """
        Returns enhanced prompt specifically optimized for image OCR extraction.
        """
        
        return """
        You are an expert OCR system extracting exam schedules from images. Pay EXTREME attention to SESSION BOUNDARIES.

        ## TABLE STRUCTURE (Read Left to Right)
        | Date | Session | Time | Offered To | Level | Course Code | Course Name |

        ## CRITICAL: SESSION BOUNDARY DETECTION

        The table has TWO sessions per day:
        - **Session 1** = MORNING exams (time starts with 9:00)
        - **Session 2** = AFTERNOON exams (time starts with 12:00)

        ### HOW TO DETECT SESSION BOUNDARIES:
        1. Look for the text "Session 1" or "Session 2" in the Session column
        2. The TIME column shows the actual time (9:00-11:00/11:30 OR 12:00-2:00)
        3. ALL courses ABOVE "Session 2" text belong to Session 1
        4. ALL courses BELOW "Session 2" text belong to Session 2

        ### CRITICAL RULE:
        When you see courses listed vertically, they share the SAME session/time until you see a NEW session marker!

        Example for Tuesday 23/12/2025:
        ```
        Tuesday    | Session 1 | 9:00-11:30 | CS    | 5 | MATH306  | Logic        ← 9:00-11:30
        23/12/2025 |           |            | CS    | 7 | MATH401  | Logic        ← 9:00-11:30 (SAME!)
                |           |            | CYS   | 7 | CYS 402  | Math Found   ← 9:00-11:30 (SAME!)
                |           |            | CYS   | 5 | CYS 301  | Math Found   ← 9:00-11:30 (SAME!)
                |           |            | CIS   | 5 | CIS 308  | IT Project   ← 9:00-11:30 (SAME! Still Session 1!)
                |           |            | CIS   | 7 | CIS 414  | IT Project   ← 9:00-11:30 (SAME!)
                | Session 2 | 12:00-2:00 | AI,CS | 7 | ARTI 401 | AI Princ.    ← 12:00-2:00 (NOW Session 2!)
        ```

        In this example:
        - CIS 308 time = 9:00 to 11:30 (because it's BEFORE "Session 2" marker)
        - ARTI 401 time = 12:00 to 2:00 (because it's AFTER "Session 2" marker)

        ## KEY RULE FOR CIS 308:
        CIS 308 (IT Project Management) is in Session 1 on Tuesday 23/12/2025.
        Its time MUST be 9:00 to 11:30, NOT 12:00 to 2:00!

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
        - Normalize majors: "AI/CS" → "AI,CS", "AL" → "AI"
        - Level as numbers only: "5" not "Level 5"

        ## VERIFICATION BEFORE OUTPUT
        For EACH course, ask yourself:
        1. Is this course BEFORE or AFTER the "Session 2" marker for its date?
        2. If BEFORE Session 2 → Time should be 9:00 (morning)
        3. If AFTER Session 2 → Time should be 12:00 (afternoon)

        EXTRACT ALL EXAMS WITH CORRECT SESSION/TIME ASSIGNMENTS!
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
                "temperature": 0.1, # Low temperature for accuracy
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
            image_data= base64.b64encode(image_file.read()).decode('utf-8')

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
                "temperature": 0.1, # Low temperature for accuracy
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
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'bmp': 'image/bmp',
            'webp': 'image/webp',
            'tiff': 'image/tiff',
            'tif': 'image/tiff'
        }
        return mime_types.get(ext, 'image/jpeg')

    def _send_request(self, data: dict) -> str:
        """Send request to Gemini API and return response."""
        
        logger.info("Sending request to Gemini model")
        
        response= requests.post(
            self.URL, 
            headers= self.headers, 
            data= json.dumps(data),
            timeout= 120
        )

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
            logger.error(f"Response: {json.dumps(json_response, indent=2)}")
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
        major_level: str, # REQUIRED
        offered_to: str # REQUIRED
    ) -> List[Dict[str, Any]]:
        """
        Filter events based on user criteria using AI understanding.
        
        Args:
            events: List of all extracted events
            major_level: User's major level (e.g., "3", "5", "7", "9") - REQUIRED
            offered_to: User's major (e.g., "CS", "AI", "CIS", "CYS") - REQUIRED
            
        Returns:
            Filtered list of events matching criteria
        """
        
        # Both filters are required
        if not major_level or not offered_to:
            logger.warning("Both major_level and offered_to are REQUIRED")
            return []

        logger.info(f"Filtering events - Level: {major_level}, Major: {offered_to}")

        prompt= f"""
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
                "temperature": 0.1, # Low temperature for accuracy
                "maxOutputTokens": 8192
            }
        }

        try:
            response= requests.post(
                self.URL, 
                headers= self.headers, 
                data= json.dumps(data),
                timeout= 60
            )

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

    def _parse_level_major_pairs(self, level_str: str) -> List[Tuple[str, Optional[str]]]:
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
        """
        
        if not level_str:
            return []
        
        pairs= []
        
        # Pattern: digit(s) with optional (MAJOR) - flexible spacing with \s*
        # Matches: "5", "5 (CS)", "5(CS)", "5 ( CS )", etc.
        pattern= r'(\d+)\s*(?:\(\s*([^)]+?)\s*\))?'
        
        matches= re.findall(pattern, level_str)
        
        for match in matches:
            level= match[0].strip()
            major= match[1].strip().upper() if match[1] else None
            if level:
                pairs.append((level, major))
        
        return pairs

    def _check_level_match(self, event_level: str, filter_level: str, filter_major: str) -> bool:
        """
        Check if user's level matches the event level using regex parsing.
        
        Handles complex formats like "7 (AI) 9 (CS) 9(CYS)" where different
        levels apply to different majors.
        """
        
        if not event_level or not filter_level:
            return False
        
        pairs= self._parse_level_major_pairs(event_level)
        
        if not pairs:
            return False
        
        filter_level= filter_level.strip()
        filter_major_upper= filter_major.strip().upper() if filter_major else None
        
        for level, major in pairs:
            if level == filter_level:
                if major:
                    # This level is specific to a major
                    if filter_major_upper and major == filter_major_upper:
                        return True
                else:
                    # No associated major = applies to everyone
                    return True
        
        return False

    def _check_major_match(self, event_offered: str, filter_major: str) -> bool:
        """
        Check if user's major matches the event's offered_to field.
        
        Handles formats like:
        - "ALL" -> matches everyone
        - "CS" -> matches only CS
        - "CS/CYS" -> matches CS or CYS
        - "AI,CS,CYS" -> matches any of these
        """
        
        if not filter_major:
            return False
        
        if not event_offered:
            return False
        
        event_offered= event_offered.strip().upper()
        filter_major= filter_major.strip().upper()
        
        if event_offered == "ALL":
            return True
        
        # Split by separators: / , + with optional spaces
        majors= re.split(r'\s*[/,+]\s*', event_offered)
        majors= [m.strip() for m in majors if m.strip()]
        
        return filter_major in majors

    def _local_filter(
        self, 
        events: List[Dict[str, Any]], 
        major_level: str, # REQUIRED
        offered_to: str # REQUIRED
    ) -> List[Dict[str, Any]]:
        """
        Local filtering with regex-based level parsing.
        STRICT filtering: Both level AND major must match.
        
        Args:
            events: List of events to filter
            major_level: User's level (REQUIRED)
            offered_to: User's major (REQUIRED)
        """
        
        logger.info("Using regex-based local filtering (STRICT mode)")
        
        if not major_level or not offered_to:
            logger.warning("Both major_level and offered_to are REQUIRED")
            return []
        
        filtered= []
        filter_level= str(major_level).strip()
        filter_major= str(offered_to).strip().upper()

        for event in events:
            # Get event values
            event_level= str(event.get("Major-Level", event.get("major_level", ""))).strip()
            event_offered= str(event.get("Offered To", event.get("offered_to", ""))).strip().upper()

            # Check level match using regex parser
            level_match= self._check_level_match(event_level, filter_level, filter_major)
            
            # Check major match
            major_match= self._check_major_match(event_offered, filter_major)

            # BOTH must match
            if level_match and major_match:
                filtered.append(event)
                logger.debug(f"✓ {event.get('course_code', event.get('Course Code', ''))}: L{event_level}= {filter_level}, M{event_offered} ∋ {filter_major}")
            else:
                logger.debug(f"✗ {event.get('course_code', event.get('Course Code', ''))}: level_match= {level_match}, major_match= {major_match}")

        logger.info(f"STRICT regex filter: {len(events)} -> {len(filtered)} events")
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
        is_image: bool= False, 
        image_path: str= None
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
        events: List[Dict[str, Any]], # List of the events
        major_level: str, # REQUIRED
        offered_to: str # REQUIRED
    ) -> List[Dict[str, Any]]:
        """
        Filter extracted events based on user criteria.
        
        Args:
            events: List of events to filter
            major_level: User's level (REQUIRED)
            offered_to: User's major (REQUIRED)
        """
        
        return self.filter_model.filter_events(events, major_level, offered_to)

    def _save_response(self, filename: str= "Response.json"):
        """Save response to file."""
        
        if self.response:
            backend_folder= os.path.dirname(os.path.abspath(__file__))
            response_path= os.path.join(backend_folder, filename)
            with open(response_path, "w", encoding= "utf-8") as f:
                f.write(self.response)
            logger.info(f"Response saved to {response_path}")