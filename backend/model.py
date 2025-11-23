import requests
import json
import os
import base64
import logging
logging.basicConfig(level= logging.INFO)
logger= logging.getLogger(__name__)

class PromptChat(object):
    """
    Class to interact with Gemini Model for exam dates extraction.
    Args:
        api_key (str): API key for authentication.
        url_endpoint (str): URL endpoint for the Gemini Model.
    """

    def __init__(self, api_key: str, url_endpoint: str):
        self.API_KEY= api_key
        self.URL= url_endpoint
        self.headers= {
            "Content-Type": "application/json",
            "X-goog-api-key": self.API_KEY
        }
        self.response= None

    def get_content(self, page: str, is_image: bool = False, image_path: str = None) -> str:
        """
        Get exam dates from Gemini Model based on the provided content.
        Extracts ALL events from the document without filtering.
        Args:
            page (str): The text content or marker for image file.
            is_image (bool): Whether the input is an image file.
            image_path (str): Path to the image file if is_image is True.
        Returns:
            str: All exam dates from the Gemini Model in JSON format.
        """

        logger.info("Preparing prompt for event extraction (extracting ALL events).")

        base_prompt = """You are an exam schedule extraction assistant. Extract ALL exam information from this schedule.

Extract these columns for EVERY exam in the schedule:
- Date: The exam date (keep the original format from the document, e.g., "2025/01/15" or "15/01/2025")
- Time: The exam time (keep the original format, e.g., "9:00 to 12:00" or "9:00-12:00")
- Major-Level: The student level (e.g., "1", "2", "3", "4")
- Offered To: The major this exam is for (e.g., "AI", "CIS", "CS", "CYS", "SE", "All")
- Course Code: The course code (e.g., "CS201", "MATH101")
- Course Name: The full course name (e.g., "Data Structures", "Calculus I")

Return the result ONLY as a JSON array with this exact structure:
[
    {
        "Date": "2025/01/15",
        "Time": "9:00 to 12:00",
        "Major-Level": "2",
        "Offered To": "CS",
        "Course Code": "CS201",
        "Course Name": "Data Structures"
    },
    {
        "Date": "2025/01/16",
        "Time": "14:00 to 17:00",
        "Major-Level": "1",
        "Offered To": "All",
        "Course Code": "MATH101",
        "Course Name": "Calculus I"
    }
]

CRITICAL RULES:
1. Return ONLY valid JSON - no markdown, no explanations, no code blocks
2. Extract EVERY exam from the schedule - do not skip any
3. If "Offered To" shows multiple majors (e.g., "CS, SE"), keep it as is
4. If a field is missing or unclear, use an empty string ""
5. Ensure all date and time formats match the source document exactly"""

        # Prepare the request data
        data = {"contents": [{"parts": []}]}

        if is_image and image_path and os.path.exists(image_path):
            # For image files, encode as base64 and send with vision
            logger.info(f"Processing image file: {image_path}")
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')

            # Determine mime type
            mime_type = "image/jpeg"
            if image_path.lower().endswith('.png'):
                mime_type = "image/png"
            elif image_path.lower().endswith(('.jpg', '.jpeg')):
                mime_type = "image/jpeg"
            elif image_path.lower().endswith('.gif'):
                mime_type = "image/gif"
            elif image_path.lower().endswith('.bmp'):
                mime_type = "image/bmp"

            # Add image and text prompt
            data["contents"][0]["parts"] = [
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": image_data
                    }
                },
                {
                    "text": base_prompt
                }
            ]
        else:
            # For text content (from PDFs), include the text in the prompt
            logger.info("Processing text content.")
            full_prompt = f"""{base_prompt}

Here is the exam schedule content:

{page}"""
            data["contents"][0]["parts"] = [
                {
                    "text": full_prompt
                }
            ]

        logger.info("Prompt prepared successfully.")
        return self._get_response(data)
    
    def _get_response(self, data: dict):
        """
        Internal method to send request to Gemini Model and retrieve the response.
        Args:
            data (dict): The request data containing the prompt and/or image.
        Returns:
            str: The exam dates in JSON format from the Gemini Model.
        """

        logger.info("Sending request to Gemini model for event extraction.")
        response= requests.post(self.URL, headers= self.headers, data= json.dumps(data))

        if response.status_code != 200:
            logger.error(f"Request failed with status code {response.status_code}: {response.text}")
            raise Exception(f"Request failed with status code {response.status_code}: {response.text}")

        logger.info("Response received successfully from Gemini model.")
        json_response= response.json()

        # Extract text content from the response
        try:
            self.response= json_response["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            logger.error(f"Error parsing response: {e}")
            logger.error(f"Response structure: {json.dumps(json_response, indent=2)}")
            raise Exception(f"Failed to parse Gemini response: {str(e)}")

        # Automatically save response to backend folder
        backend_folder = os.path.dirname(os.path.abspath(__file__))
        response_path = os.path.join(backend_folder, "Response.json")
        self.save_response(response_path)

        return self.response
    
    def save_response(self, filename: str = "Response.json"):
        """
        Save exam dates response to a file.
        Args:
            filename (str): The name of the file to save the response. Defaults to "Response.json".
        """
        
        logger.info(f"Saving exam dates to ({filename}).")
        with open(filename, "w", encoding= "utf-8") as f:
            f.write(self.response)
        
        if os.path.exists(filename):
            logger.info(f"Exam dates saved successfully to ({filename}).")