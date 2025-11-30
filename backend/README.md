# Environment Setup

Before running the backend, create a secure place for environment variables.


## 1. Create `secrets` folder
Inside the project `backend` directory, create a folder named: `secrets`.


## 2. Create `.env` file
Inside the `backend/secrets` folder, create a file named: `.env`.



## 3. Add these environment variables to `.env`
Open `backend/secrets/.env` and add the following lines (replace the placeholder with your real key):

- GEMINI_API_KEY= YOUR_GEMINI_API_KEY
- GEMINI_MODEL_URL= https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent
