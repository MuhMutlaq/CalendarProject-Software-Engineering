# Calendar Event Extractor - Backend Setup Guide

## Overview
This backend uses the Gemini AI API to extract exam/event information from PDF documents and images. It processes both text (from PDFs) and images (using Gemini's vision capabilities).

## Architecture

```
┌─────────────────────┐
│   Frontend (GUI)    │
│  AutoEventExtractor │
│      Modal.tsx      │
└──────────┬──────────┘
           │
           │ HTTP POST /extract-events
           │ (file + major_level + offered_to)
           ▼
┌─────────────────────┐
│   FastAPI Backend   │
│      app.py         │
└──────────┬──────────┘
           │
           │ calls
           ▼
┌─────────────────────┐
│   AI Model Layer    │
│     model.py        │
│   (PromptChat)      │
└──────────┬──────────┘
           │
           │ API request
           ▼
┌─────────────────────┐
│   Gemini API        │
│  (Vision + Text)    │
└─────────────────────┘
```

## Setup Instructions

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the `backend` folder (or a `secrets` file):

```bash
cp .env.example .env
```

Edit the `.env` file and add your Gemini API key:

```env
GEMINI_API_KEY=your_actual_api_key_here
GEMINI_MODEL_URL=https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent
```

**Get your API key from:** https://makersuite.google.com/app/apikey

### 3. Run the Backend Server

```bash
python app.py
```

Or with uvicorn:

```bash
uvicorn app:app --host localhost --port 5000 --reload
```

The server will start at: http://localhost:5000

### 4. API Documentation

Once running, you can access:
- **API Docs:** http://localhost:5000/docs
- **Health Check:** http://localhost:5000/health

## How It Works

### File Processing Flow

1. **Frontend Upload:**
   - User selects a PDF or image file
   - User optionally provides:
     - Major Level (e.g., "1", "2", "3", "4")
     - Offered To (e.g., "Computer Science", "Software Engineering")
   - File is sent to `/extract-events` endpoint

2. **Backend Processing (app.py):**
   - Receives file and user filters
   - Determines file type (PDF or image)
   - For PDFs: Extracts text using PyPDF2
   - For Images: Passes file path to model layer
   - Calls `extract_events_with_ai()` with appropriate parameters

3. **AI Extraction (model.py):**
   - **For Images:**
     - Encodes image to base64
     - Sends to Gemini API with vision capabilities
     - Includes prompt with filtering instructions
   - **For PDFs:**
     - Sends extracted text to Gemini API
     - Includes prompt with filtering instructions
   - Receives JSON response with extracted events

4. **Response Formatting:**
   - Parses JSON from AI response
   - Converts to standardized event format
   - Returns to frontend with:
     - Date (ISO format)
     - Time
     - Title (Course Code + Course Name)
     - Description (all details)
     - Course Code
     - Course Name
     - Major Level
     - Offered To

### Filtering Logic

The AI model applies filters based on user input:

- **No filters:** Extracts ALL events from the document
- **Major Level only:** Extracts events for that level (all majors)
- **Offered To only:** Extracts events for that major (all levels)
- **Both filters:** Extracts events matching BOTH conditions
  - Special case: "Offered To: All" means the event applies to all majors at that level

### Response Format

```json
{
  "success": true,
  "events": [
    {
      "date": "2025-01-15",
      "time": "9:00 to 12:00",
      "title": "CS201: Data Structures",
      "description": "Date: 2025-01-15\\nTime: 9:00 to 12:00\\nMajor-Level: 2\\nOffered To: CS",
      "course_code": "CS201",
      "course_name": "Data Structures",
      "major_level": "2",
      "offered_to": "CS",
      "confidence": 0.95
    }
  ],
  "total_events": 1,
  "ai_enabled": true
}
```

## File Structure

```
backend/
├── app.py              # FastAPI application (API endpoints)
├── model.py            # PromptChat class (Gemini AI integration)
├── requirements.txt    # Python dependencies
├── .env.example        # Example environment variables
├── .env               # Your actual environment variables (gitignored)
├── SETUP.md           # This file
├── uploads/           # Temporary file storage (gitignored)
└── Response.json      # Last AI response (for debugging)
```

## API Endpoints

### POST /extract-events
Extract events from uploaded file.

**Request:**
- `file`: Image or PDF file
- `major_level`: (Optional) Student's major level (e.g., "1", "2", "3", "4")
- `offered_to`: (Optional) Student's major (e.g., "Computer Science")

**Response:**
```json
{
  "success": true,
  "events": [...],
  "total_events": 5,
  "ai_enabled": true
}
```

### GET /health
Check server and AI model status.

**Response:**
```json
{
  "status": "healthy",
  "ai_enabled": true,
  "pdf_support": true,
  "timestamp": "2025-11-24T10:30:00",
  "framework": "FastAPI",
  "message": "Ready"
}
```

## Troubleshooting

### Common Issues

1. **"AI model not initialized"**
   - Check that GEMINI_API_KEY is set in .env file
   - Verify the API key is valid

2. **"Request failed with status code 400"**
   - Check GEMINI_MODEL_URL is correct
   - Ensure the model name supports vision (use gemini-1.5-flash or gemini-1.5-pro)

3. **"No text could be extracted from PDF"**
   - PDF might be image-based (scanned document)
   - Try using an image file instead

4. **Empty events array**
   - Check that the filters match data in the document
   - Try without filters to extract everything
   - Check Response.json to see the raw AI output

### Debug Mode

The backend automatically saves the last AI response to `Response.json`. Check this file to see what the AI model returned.

## Performance Tips

- **Gemini 1.5 Flash** is recommended for faster processing
- **Gemini 1.5 Pro** provides better accuracy but is slower
- Image files should be under 16MB
- PDF text extraction is faster than image processing

## Security Notes

- Never commit `.env` or `secrets` file to version control
- The `uploads/` folder is temporary and cleaned automatically
- API key should be kept secret and not shared

## Support

For issues or questions:
1. Check Response.json for AI model output
2. Check backend logs for detailed error messages
3. Verify API key and model URL are correct
4. Test with /health endpoint to verify configuration
