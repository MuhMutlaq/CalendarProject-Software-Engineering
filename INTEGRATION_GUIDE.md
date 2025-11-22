# Image & PDF Date Extraction Integration Guide

This guide explains how to use the Python backend to extract dates from images and PDF files in your React Native calendar app.

## Overview

The integration consists of two parts:

1. **Python Flask Backend** - Handles OCR and date extraction from files
2. **React Native Frontend** - Provides UI for file upload and event management

## Architecture

```
┌─────────────────────────────────────┐
│   React Native App                  │
│   ┌─────────────────────────────┐   │
│   │ AutoEventExtractorModal     │   │
│   │  - File picker              │   │
│   │  - Image picker             │   │
│   │  - Event preview/edit       │   │
│   └──────────┬──────────────────┘   │
│              │ HTTP POST            │
│              │ (multipart/form-data)│
└──────────────┼──────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Python FastAPI Backend (port 5000)  │
│   ┌──────────────────────────────┐   │
│   │ /extract-events (async)      │   │
│   │  1. Receive file             │   │
│   │  2. Extract text (OCR/PDF)   │   │
│   │  3. Parse dates              │   │
│   │  4. Return events JSON       │   │
│   └──────────────────────────────┘   │
│                                      │
│   Features:                          │
│   - Async/await support              │
│   - Auto API docs (/docs)            │
│   - Type validation                  │
│                                      │
│   Dependencies:                      │
│   - Tesseract OCR                    │
│   - PyPDF2, pdf2image                │
│   - pytesseract, Pillow              │
└──────────────────────────────────────┘
```

## Quick Start

### Step 1: Set Up Python Backend

1. **Install system dependencies:**

   **macOS:**
   ```bash
   brew install tesseract poppler
   ```

   **Linux (Ubuntu/Debian):**
   ```bash
   sudo apt-get update
   sudo apt-get install tesseract-ocr poppler-utils
   ```

2. **Install Python packages:**
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Start the backend server:**
   ```bash
   python app.py
   ```

   You should see:
   ```
   Starting FastAPI server...
   PDF Support: True
   Upload folder: uploads
   API Documentation: http://localhost:5000/docs
   INFO:     Started server process
   INFO:     Uvicorn running on http://0.0.0.0:5000
   ```

### Step 2: Test the Backend

```bash
curl http://localhost:5000/health
```

Expected response:
```json
{
  "status": "healthy",
  "pdf_support": true,
  "timestamp": "2025-11-19T...",
  "framework": "FastAPI"
}
```

You can also visit http://localhost:5000/docs for interactive API documentation (Swagger UI).

### Step 3: Configure React Native App

The React Native dependencies are already installed. The app will automatically connect to:

- **iOS Simulator**: `http://localhost:5000`
- **Android Emulator**: `http://10.0.2.2:5000`

For a **physical device**, you need to:

1. Find your computer's IP address:
   ```bash
   # macOS/Linux
   ifconfig | grep "inet "

   # Windows
   ipconfig
   ```

2. Update [AutoEventExtractorModal.tsx](components/AutoEventExtractorModal.tsx#L49):
   ```typescript
   const BACKEND_URL = "http://YOUR_IP_ADDRESS:5000";
   ```

### Step 4: Run the App

```bash
npm start
```

Then press:
- `i` for iOS
- `a` for Android
- `w` for Web

## Usage

### In the App

1. Open the calendar app
2. Tap the "Auto Add Events" button
3. Choose an option:
   - **Upload Photo** - Select an image from your gallery
   - **Upload File** - Select a PDF or image file

4. The app will:
   - Upload the file to the Python backend
   - Extract dates using OCR/PDF parsing
   - Display extracted events for review

5. Review and edit the extracted events
6. Tap "Save All Events" to add them to your calendar

### Supported Date Formats

The backend can extract dates in various formats:

- `12/25/2025` or `25/12/2025` (MM/DD/YYYY or DD/MM/YYYY)
- `2025-12-25` (ISO format)
- `Dec 25, 2025` (abbreviated month)
- `25 Dec 2025` (day-month-year)
- `December 25, 2025` (full month name)

### Example Test Files

Create a test image with dates:

**test_dates.txt** (then convert to image or PDF):
```
Important Dates:

Team Meeting - 12/15/2025
Project Deadline - 2025-12-20
Holiday Party - December 25, 2025
Conference - Jan 10, 2026
```

You can use online tools to convert this to an image, or create a simple document.

## Code Walkthrough

### Backend: Date Extraction Flow

1. **File Upload** ([app.py:215](backend/app.py#L215)):
   ```python
   @app.post('/extract-events')
   async def extract_events(file: UploadFile = File(...)):
       # Async file processing
       file_content = await file.read()
   ```

2. **Text Extraction** ([app.py:63](backend/app.py#L63)):
   ```python
   def extract_text_from_image(image_path: str) -> str:
       img = Image.open(image_path)
       text = pytesseract.image_to_string(img)
       return text
   ```

3. **Date Parsing** ([app.py:103](backend/app.py#L103)):
   ```python
   def extract_dates_from_text(text: str) -> List[str]:
       # Use regex patterns to find dates
       # Parse with dateutil
       return parsed_dates
   ```

4. **Event Generation** ([app.py:133](backend/app.py#L133)):
   ```python
   def extract_events_with_ai(text: str, dates: List[str]) -> List[Dict[str, Any]]:
       # Extract context around dates
       # Create event objects with confidence scores
       return events
   ```

### Frontend: Upload Flow

1. **File Selection** ([AutoEventExtractorModal.tsx:117](components/AutoEventExtractorModal.tsx#L117)):
   ```typescript
   const result = await DocumentPicker.getDocumentAsync({
     type: ["application/pdf", "image/*"],
   });
   ```

2. **Upload to Backend** ([AutoEventExtractorModal.tsx:55](components/AutoEventExtractorModal.tsx#L55)):
   ```typescript
   const formData = new FormData();
   formData.append("file", {
     uri: fileUri,
     name: fileName,
     type: mimeType,
   });

   const response = await fetch(`${BACKEND_URL}/extract-events`, {
     method: "POST",
     body: formData,
   });
   ```

3. **Display Results** ([AutoEventExtractorModal.tsx:87](components/AutoEventExtractorModal.tsx#L87)):
   ```typescript
   const events: ExtractedEvent[] = data.events.map(
     (event: any, index: number) => ({
       id: `temp-${Date.now()}-${index}`,
       date: event.date,
       title: event.title || "Untitled Event",
       description: event.description || "",
       confidence: event.confidence || 0.7,
     })
   );
   ```

## Customization

### Improving Event Extraction

The default implementation uses simple pattern matching. For better results, you can integrate an LLM:

**Option 1: OpenAI GPT (with FastAPI)**
```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

async def extract_events_with_ai(text: str, dates: List[str]):
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[{
            "role": "user",
            "content": f"Extract event information from this text: {text}"
        }]
    )
    # Parse response and return events
```

**Option 2: Anthropic Claude (with FastAPI)**
```python
from anthropic import AsyncAnthropic

client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

async def extract_events_with_ai(text: str, dates: List[str]):
    message = await client.messages.create(
        model="claude-3-sonnet-20240229",
        messages=[{
            "role": "user",
            "content": f"Extract events from: {text}"
        }]
    )
    # Parse response
```

### Adding More Date Formats

Edit the `date_patterns` list in [app.py:106](backend/app.py#L106):

```python
date_patterns = [
    r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',
    # Add your custom pattern here
    r'your-regex-pattern',
]
```

### Improving OCR Accuracy

1. **Preprocess images** before OCR:
   ```python
   from PIL import Image, ImageEnhance

   img = Image.open(image_path)
   # Increase contrast
   enhancer = ImageEnhance.Contrast(img)
   img = enhancer.enhance(2)
   # Convert to grayscale
   img = img.convert('L')
   ```

2. **Configure Tesseract**:
   ```python
   custom_config = r'--oem 3 --psm 6'
   text = pytesseract.image_to_string(img, config=custom_config)
   ```

## Troubleshooting

### Backend Issues

**Problem**: `pytesseract.pytesseract.TesseractNotFoundError`
- **Solution**: Install Tesseract OCR:
  ```bash
  brew install tesseract  # macOS
  ```

**Problem**: `PDF support disabled`
- **Solution**: Install PDF dependencies:
  ```bash
  pip install PyPDF2 pdf2image
  brew install poppler  # macOS
  ```

**Problem**: No dates extracted
- **Solution**:
  - Check image quality (should be clear and readable)
  - Ensure text is not too small
  - Try preprocessing the image to enhance contrast

### Frontend Issues

**Problem**: `Failed to process file. Make sure the Python backend is running.`
- **Solution**:
  1. Verify backend is running: `curl http://localhost:5000/health`
  2. Check BACKEND_URL in AutoEventExtractorModal.tsx
  3. For physical devices, use your computer's IP address

**Problem**: File picker not opening
- **Solution**:
  - Rebuild the app: `npm start` (then press `a` or `i`)
  - Check permissions in app settings

**Problem**: CORS errors
- **Solution**: Ensure `flask-cors` is installed in backend

## Performance Optimization

### Backend

1. **Limit file size**: Already set to 16MB
2. **Process in background**: For large PDFs, consider using Celery
3. **Cache results**: Store processed files temporarily

### Frontend

1. **Compress images** before upload:
   ```typescript
   const result = await ImagePicker.launchImageLibraryAsync({
     quality: 0.7,  // Reduce quality
     allowsEditing: true,
   });
   ```

2. **Show progress indicator**: Already implemented

## Security Considerations

1. **File validation**: Backend validates file types
2. **File size limits**: 16MB maximum
3. **Temporary file cleanup**: Files are deleted after processing
4. **CORS**: Configured for development (tighten for production)

### For Production

1. Use HTTPS:
   ```python
   app.run(ssl_context=('cert.pem', 'key.pem'))
   ```

2. Add authentication:
   ```python
   from flask_httpauth import HTTPBasicAuth
   ```

3. Rate limiting:
   ```python
   from flask_limiter import Limiter
   ```

## Next Steps

1. **Test with real files**: Try uploading various images and PDFs
2. **Improve accuracy**: Integrate an LLM for better event extraction
3. **Add more features**:
   - Time extraction (not just dates)
   - Location detection
   - Event categories
   - Recurring events

## Support

For issues or questions:
1. Check the [Backend README](backend/README.md)
2. Review error messages in backend console
3. Check React Native debugger console

## Reference Files

- Backend API: [backend/app.py](backend/app.py)
- React Native Component: [components/AutoEventExtractorModal.tsx](components/AutoEventExtractorModal.tsx)
- Python Dependencies: [backend/requirements.txt](backend/requirements.txt)
- Backend Documentation: [backend/README.md](backend/README.md)
