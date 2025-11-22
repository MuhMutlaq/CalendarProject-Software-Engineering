# Calendar Event Extractor Backend

Python FastAPI backend for extracting dates and events from images and PDF files using OCR and text processing.

## Features

- Extract dates from images using OCR (Tesseract)
- Extract dates from PDF files (text-based and scanned)
- Parse multiple date formats
- High-performance async RESTful API
- Automatic interactive API documentation (Swagger UI & ReDoc)
- Type safety with Pydantic models
- CORS enabled for cross-origin requests

## Prerequisites

### Required Software

1. **Python 3.8+**
   ```bash
   python3 --version
   ```

2. **Tesseract OCR**

   **macOS:**
   ```bash
   brew install tesseract
   ```

   **Linux (Ubuntu/Debian):**
   ```bash
   sudo apt-get update
   sudo apt-get install tesseract-ocr
   ```

   **Windows:**
   - Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
   - Add Tesseract to PATH

3. **Poppler (for PDF to image conversion)**

   **macOS:**
   ```bash
   brew install poppler
   ```

   **Linux (Ubuntu/Debian):**
   ```bash
   sudo apt-get install poppler-utils
   ```

   **Windows:**
   - Download from: https://blog.alivate.com.au/poppler-windows/
   - Add to PATH

## Installation

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create virtual environment (recommended):**
   ```bash
   python3 -m venv venv
   ```

3. **Activate virtual environment:**

   **macOS/Linux:**
   ```bash
   source venv/bin/activate
   ```

   **Windows:**
   ```bash
   venv\Scripts\activate
   ```

4. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Running the Backend

1. **Make sure virtual environment is activated**

2. **Start the FastAPI server:**
   ```bash
   python app.py
   ```

   Or use uvicorn directly:
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 5000 --reload
   ```

   The server will start on `http://0.0.0.0:5000`

3. **View interactive API documentation:**
   - Swagger UI: http://localhost:5000/docs
   - ReDoc: http://localhost:5000/redoc

4. **Test the server:**
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

## API Endpoints

### Health Check
```
GET /health
```
Returns server status and configuration.

### Extract Events from File
```
POST /extract-events
Content-Type: multipart/form-data

Body:
  file: <image or PDF file>
```

**Supported file types:**
- Images: PNG, JPG, JPEG, GIF, BMP, TIFF
- Documents: PDF

**Response:**
```json
{
  "success": true,
  "events": [
    {
      "date": "2025-12-25",
      "title": "Christmas Party",
      "description": "Annual holiday celebration",
      "confidence": 0.85
    }
  ],
  "total_events": 1
}
```

### Extract Events from Image
```
POST /extract-events-from-image
```
Same as `/extract-events` - provided for convenience.

## Testing with cURL

### Upload an image:
```bash
curl -X POST http://localhost:5000/extract-events \
  -F "file=@/path/to/your/image.jpg"
```

### Upload a PDF:
```bash
curl -X POST http://localhost:5000/extract-events \
  -F "file=@/path/to/your/document.pdf"
```

## Configuration

### Changing the Port
Edit `app.py` and modify the uvicorn.run() call:
```python
uvicorn.run(app, host='0.0.0.0', port=5000, log_level='info')
```

Or run with uvicorn CLI:
```bash
uvicorn app:app --port 8000
```

### File Size Limits
Default: 16MB. Change in `app.py`:
```python
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
```

### Allowed File Extensions
Modify in `app.py`:
```python
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf'}
```

## Connecting from React Native

The React Native app needs to know your backend URL:

### iOS Simulator
```
http://localhost:5000
```

### Android Emulator
```
http://10.0.2.2:5000
```

### Physical Device
Find your computer's IP address:

**macOS/Linux:**
```bash
ifconfig | grep "inet "
```

**Windows:**
```bash
ipconfig
```

Then use:
```
http://YOUR_IP_ADDRESS:5000
```

Update the `BACKEND_URL` in [AutoEventExtractorModal.tsx](../components/AutoEventExtractorModal.tsx:49) accordingly.

## Troubleshooting

### Tesseract not found
```
Error: pytesseract.pytesseract.TesseractNotFoundError
```
**Solution:** Install Tesseract OCR and ensure it's in your PATH.

### PDF support disabled
```
Warning: PyPDF2 and pdf2image not installed. PDF support disabled.
```
**Solution:**
```bash
pip install PyPDF2 pdf2image
brew install poppler  # macOS
```

### No events extracted
- Check if the image/PDF has clear, readable text
- Ensure dates are in recognizable formats (MM/DD/YYYY, YYYY-MM-DD, etc.)
- Try improving image quality or resolution

### CORS errors
If you see CORS errors in React Native, CORS is already configured in FastAPI. Check that the middleware is enabled in `app.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Port already in use
```
Error: Address already in use
```
**Solution:** Change the port in `app.py` or kill the process using port 5000:
```bash
# macOS/Linux
lsof -ti:5000 | xargs kill -9

# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

## Production Deployment

FastAPI with Uvicorn is production-ready. For better performance with multiple workers:

```bash
uvicorn app:app --host 0.0.0.0 --port 5000 --workers 4
```

Or use Gunicorn with Uvicorn workers:

```bash
pip install gunicorn
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:5000
```

### Additional Production Considerations

1. **Use a process manager** (systemd, supervisor, or PM2)
2. **Set up a reverse proxy** (nginx or Apache)
3. **Enable HTTPS** with SSL certificates
4. **Configure specific CORS origins** instead of `allow_origins=["*"]`
5. **Add rate limiting** and authentication
6. **Monitor performance** with logging and metrics

## Advanced Features (Optional)

### AI-Powered Event Extraction

The current implementation uses simple pattern matching. For better results, integrate an LLM:

1. Install OpenAI or Anthropic SDK:
   ```bash
   pip install openai
   # or
   pip install anthropic
   ```

2. Set API key:
   ```bash
   export OPENAI_API_KEY="your-key"
   ```

3. Modify `extract_events_with_ai()` function in `app.py` to use the API.

## License

MIT
