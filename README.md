# Calendar Project

An intelligent calendar application built with React Native (Expo) and FastAPI that uses AI to automatically extract events from images and PDF documents.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Detailed Installation](#detailed-installation)
  - [Frontend Setup](#frontend-setup)
  - [Backend Setup](#backend-setup)
- [Environment Configuration](#environment-configuration)
- [Running the Project](#running-the-project)
- [API Documentation](#api-documentation)
- [Technologies Used](#technologies-used)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

## Features

- **AI-Powered Event Extraction**: Upload images or PDFs containing calendar events and let AI extract them automatically
- **Multi-Format Support**: Supports PNG, JPG, JPEG, GIF, BMP, TIFF, WEBP images and PDF documents
- **Smart Filtering**: Filter events by major and academic level
- **Cross-Platform**: Works on iOS, Android, and Web
- **Image Preprocessing**: Enhanced OCR accuracy with automatic image optimization
- **Multi-Page PDF Support**: Extracts events from multi-page documents
- **Real-Time Calendar**: View and manage your extracted events in an intuitive calendar interface

## Prerequisites

Before you begin, ensure you have the following installed:

### For Frontend

- **Node.js** (v18 or higher) - [Download](https://nodejs.org/)
- **npm** or **yarn** - Comes with Node.js
- **Expo CLI** - Will be installed automatically

### For Backend

- **Python** (v3.9 or higher) - [Download](https://www.python.org/)
- **pip** - Python package manager (comes with Python)
- **Poppler** (Optional, for PDF to image conversion):
  - **macOS**: `brew install poppler`
  - **Ubuntu/Debian**: `sudo apt-get install poppler-utils`
  - **Windows**: [Download from poppler releases](https://github.com/oschwartz10612/poppler-windows/releases/)

### Additional Requirements

- **Gemini API Key** - [Get one from Google AI Studio](https://makersuite.google.com/app/apikey)

## Project Structure

```text
CalendarProject/
├── app/                    # Expo app screens and routes
├── components/             # React Native components
│   ├── CalendarScreen.tsx
│   ├── AutoEventExtractorModal.tsx
│   └── DragDropUpload.tsx
├── hooks/                  # Custom React hooks
│   └── useEvents.ts
├── backend/                # Python FastAPI backend
│   ├── app.py             # Main API server
│   ├── model.py           # AI models (Gemini)
│   ├── image_preprocessor.py  # Image enhancement
│   ├── requirements.txt   # Python dependencies
│   └── secrets/
│       └── .env           # Environment variables
├── assets/                 # Images, fonts, and other assets
├── package.json           # Node.js dependencies
└── README.md              # This file
```

## Quick Start

Follow these steps to get the project up and running:

### 1. Install Frontend Dependencies

Navigate to the project root and install Node.js dependencies:

```bash
npm install
```

### 2. Install Python Package Manager (uv)

Install `uv`, a fast Python package installer and resolver:

```bash
pip3 install uv
```

### 3. Install Backend Dependencies

Navigate to the backend directory and install Python dependencies using `uv`:

```bash
cd backend
uv pip install -r requirements.txt
```

**Note**: If you encounter issues with `uv`, you can use traditional pip:

```bash
pip3 install -r requirements.txt
```

### 4. Configure Environment Variables

Create the `.env` file in `backend/secrets/`:

```bash
mkdir -p secrets
touch secrets/.env
```

Add your API credentials to `backend/secrets/.env`:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL_URL=https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent
```

Get your Gemini API Key from [Google AI Studio](https://makersuite.google.com/app/apikey).

### 5. Start the Backend Server

From the `backend` directory:

```bash
python app.py
```

The server will start on [http://localhost:5000](http://localhost:5000).

### 6. Start the Frontend

Open a **new terminal**, navigate to the project root, and start Expo:

```bash
npx expo start
```

### 7. Open the App

Once Expo starts, you can:

- Press **`w`** to open in web browser
- Press **`i`** to open iOS simulator (macOS only)
- Press **`a`** to open Android emulator
- Scan the QR code with Expo Go app on your physical device ([iOS](https://apps.apple.com/app/expo-go/id982107779) / [Android](https://play.google.com/store/apps/details?id=host.exp.exponent))

---

## Detailed Installation

If you need more detailed setup instructions or encounter issues, follow these steps:

### Frontend Setup

1. **Navigate to the project root**:

   ```bash
   cd /path/to/CalendarProject
   ```

2. **Install dependencies**:

   ```bash
   npm install
   ```

   Or if you prefer yarn:

   ```bash
   yarn install
   ```

3. **Verify installation**:

   ```bash
   npx expo --version
   ```

### Backend Setup

1. **Navigate to the backend directory**:

   ```bash
   cd backend
   ```

2. **Install uv (Fast Python Package Manager)**:

   ```bash
   pip3 install uv
   ```

3. **Install Python dependencies with uv**:

   ```bash
   uv pip install -r requirements.txt
   ```

   **Alternative (using traditional pip)**:

   ```bash
   pip3 install -r requirements.txt
   ```

4. **Optional: Create a virtual environment** (recommended for isolation):

   ```bash
   python -m venv venv
   source venv/bin/activate  # macOS/Linux
   # or
   venv\Scripts\activate     # Windows
   ```

   Then install dependencies:

   ```bash
   uv pip install -r requirements.txt
   ```

5. **Optional: Install additional features**:

   For enhanced PDF and image processing, install optional dependencies:

   ```bash
   uv pip install Pillow pdf2image opencv-python
   ```

   Or:

   ```bash
   pip3 install Pillow pdf2image opencv-python
   ```

## Environment Configuration

### Backend Environment Variables

1. **Create the secrets directory** (if it doesn't exist):

   ```bash
   mkdir -p backend/secrets
   ```

2. **Create a `.env` file** in `backend/secrets/`:

   ```bash
   touch backend/secrets/.env
   ```

3. **Add your Gemini API credentials** to `backend/secrets/.env`:

   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL_URL=https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent
   ```

4. **Get your Gemini API Key**:
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Sign in with your Google account
   - Create a new API key
   - Copy and paste it into your `.env` file

### Frontend Configuration

The frontend is pre-configured to connect to `http://localhost:5000` for local development. If you need to change this:

1. Open the relevant component files (e.g., [components/AutoEventExtractorModal.tsx](components/AutoEventExtractorModal.tsx))
2. Update the API URL if needed

## Running the Project

### Start the Backend Server

1. **Navigate to the backend directory**:

   ```bash
   cd backend
   ```

2. **Activate your virtual environment** (if not already activated):
   - **macOS/Linux**: `source venv/bin/activate`
   - **Windows**: `venv\Scripts\activate`

3. **Start the FastAPI server**:

   ```bash
   python app.py
   ```

   Or using uvicorn directly:

   ```bash
   uvicorn app:app --host localhost --port 5000 --reload
   ```

4. **Verify the server is running**:
   - Open your browser and visit: [http://localhost:5000](http://localhost:5000)
   - You should see the API information
   - Visit [http://localhost:5000/docs](http://localhost:5000/docs) for interactive API documentation

### Start the Frontend App

1. **Open a new terminal** (keep the backend running in the other terminal)

2. **Navigate to the project root**:

   ```bash
   cd /path/to/CalendarProject
   ```

3. **Start the Expo development server**:

   ```bash
   npx expo start
   ```

4. **Open the app**:
   - **iOS Simulator**: Press `i` in the terminal
   - **Android Emulator**: Press `a` in the terminal
   - **Web Browser**: Press `w` in the terminal
   - **Physical Device**: Scan the QR code with the Expo Go app ([iOS](https://apps.apple.com/app/expo-go/id982107779) / [Android](https://play.google.com/store/apps/details?id=host.exp.exponent))

## API Documentation

The backend provides the following endpoints:

### Health Check

- **GET** `/health`
- Returns server status and feature availability

### Extract Events (with filtering)

- **POST** `/extract-events`
- Parameters:
  - `file`: Image or PDF file (multipart/form-data)
  - `major_level`: Student level (1-9)
  - `offered_to`: Major (CS, AI, CIS, CYS, etc.)
- Returns: Filtered events matching criteria

### Extract All Events

- **POST** `/extract-all-events`
- Parameters:
  - `file`: Image or PDF file
- Returns: All extracted events without filtering

### Filter Events

- **POST** `/filter-events`
- Filters pre-extracted events by criteria

For interactive API documentation, visit [http://localhost:5000/docs](http://localhost:5000/docs) when the server is running.

## Technologies Used

### Frontend

- **React Native** - Mobile app framework
- **Expo** (v54) - Development platform
- **TypeScript** - Type-safe JavaScript
- **NativeWind** - Tailwind CSS for React Native
- **Expo Router** - File-based routing
- **Expo Image Picker** - Image selection and camera access

### Backend

- **FastAPI** - Modern Python web framework
- **Uvicorn** - ASGI server
- **Gemini AI** - Google's AI model for vision and text processing
- **PyPDF2** - PDF text extraction
- **pdf2image** - PDF to image conversion
- **OpenCV** (optional) - Image preprocessing
- **python-dateutil** - Date parsing

## Troubleshooting

### Backend Issues

**Problem**: `GEMINI_API_KEY not found`

- **Solution**: Make sure you created the `.env` file in `backend/secrets/` with your API key

**Problem**: `PDF image conversion not available`

- **Solution**: Install Poppler:
  - macOS: `brew install poppler`
  - Ubuntu: `sudo apt-get install poppler-utils`

**Problem**: `Port 5000 already in use`

- **Solution**: Change the port in [backend/app.py](backend/app.py:880) or kill the process using port 5000:

  ```bash
  lsof -ti:5000 | xargs kill -9
  ```

**Problem**: `Module not found` errors

- **Solution**: Make sure your virtual environment is activated and dependencies are installed:

  ```bash
  source venv/bin/activate  # or venv\Scripts\activate on Windows
  pip install -r requirements.txt
  ```

### Frontend Issues

**Problem**: `Unable to resolve module`

- **Solution**: Clear cache and reinstall:

  ```bash
  rm -rf node_modules
  npm install
  npx expo start --clear
  ```

**Problem**: Cannot connect to backend

- **Solution**:
  - Verify the backend server is running on port 5000
  - Check the API URL in your component files
  - For physical devices, use your computer's local IP instead of `localhost`

**Problem**: Expo Go app not detecting QR code

- **Solution**: Make sure your device and computer are on the same network

### Common Issues

**Problem**: Events not extracting correctly

- **Solution**:
  - Ensure your image/PDF is clear and readable
  - Check that the Gemini API key is valid
  - Try preprocessing the image with better lighting/contrast

**Problem**: Slow extraction performance

- **Solution**:
  - Large PDFs may take time to process
  - Consider reducing PDF quality or splitting into smaller files
  - Check your internet connection (API calls required)

---

## Development

### Running Tests

```bash
npm test
```

### Linting

```bash
npm run lint
```

### Build for Production

**iOS**:

```bash
npm run ios
```

**Android**:

```bash
npm run android
```

**Web**:

```bash
npm run web
```

---

## License

This project is private and proprietary.

---

## Support

For issues, questions, or contributions, please contact the development team.
Github: [text](https://github.com/MuhMutlaq/CalendarProject-Software-Engineering)
