# AI Stock Trend

Full-stack project with:

- Backend: FastAPI (Python)
- Frontend: React + TailwindCSS
- Model: Python scripts using yfinance and scikit-learn

## Setup

Backend

```powershell
cd backend
python -m pip install -r requirements.txt
# Set your OpenAI API key:
# PowerShell (temporary for current session):
$env:OPENAI_API_KEY = "sk-..."
# Bash (Linux/macOS):
# export OPENAI_API_KEY="sk-..."
# Run server
uvicorn backend.main:app --reload
```

Frontend

```powershell
cd frontend
npm install
npm start
```

## Notes
- The `/predict` endpoint fetches historical close prices via `yfinance` and returns the last 30 closing prices plus a simple linear-regression next-day prediction.
- The `/chat` endpoint proxies messages to OpenAI ChatCompletion. Set `OPENAI_API_KEY` in your environment before starting the backend.

