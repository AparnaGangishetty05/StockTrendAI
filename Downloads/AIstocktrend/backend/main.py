from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import joblib
from pathlib import Path
import json
import os
import requests
import logging
from logging.handlers import RotatingFileHandler
import yfinance as yf
import subprocess
import shutil

app = FastAPI()

# Setup file logging (rotating)
log_path = Path(__file__).resolve().parents[1] / 'backend_ollama.log'
handler = RotatingFileHandler(str(log_path), maxBytes=5 * 1024 * 1024, backupCount=3)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger = logging.getLogger()
if not logger.handlers:
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StockRequest(BaseModel):
    symbol: str
    days: int


class ChatRequest(BaseModel):
    message: str


@app.post("/predict")
def predict_stock(req: StockRequest):
    # Dummy data for demonstration
    dates = np.arange(req.days)
    prices = np.random.rand(req.days) * 100
    model = LinearRegression()
    model.fit(dates.reshape(-1, 1), prices)
    next_day = np.array([[req.days]])
    prediction = model.predict(next_day)[0]
    return {"predicted_price": float(prediction)}


@app.get("/predict")
def predict_get(symbol: str = "AAPL", days: int = 30):
    # Fetch historical data for the symbol using yfinance (per-symbol)
    if days <= 0:
        raise HTTPException(status_code=400, detail="days must be > 0")

    try:
        period_days = max(days, 30) + 10
        tk = yf.Ticker(symbol)
        raw = tk.history(period=f"{period_days}d", auto_adjust=False)
    except Exception as e:
        logging.exception("yfinance fetch failed for %s", symbol)
        raise HTTPException(status_code=500, detail=f"Failed to fetch data for {symbol}: {e}")

    if raw is None or raw.empty or 'Close' not in raw.columns:
        logging.warning("No data for symbol %s (raw empty or no Close)", symbol)
        raise HTTPException(status_code=400, detail=f"No data found for symbol: {symbol}")

    closes = raw['Close'].dropna()
    closes = closes.tail(days)
    if closes.empty:
        logging.warning("Not enough data for symbol %s after tail(%s)", symbol, days)
        raise HTTPException(status_code=400, detail=f"Not enough data for symbol: {symbol}")

    dates = [d.strftime('%Y-%m-%d') for d in closes.index]
    prices = [float(x) for x in closes.values]

    # Try per-symbol trained model first: model/<SYMBOL>.pkl
    pred = None
    used_trained = False
    model_dir = Path(__file__).resolve().parents[1] / 'model'
    model_path_specific = model_dir / f"{symbol}.pkl"
    model_path_global = model_dir / 'model.pkl'

    if model_path_specific.exists():
        try:
            trained = joblib.load(model_path_specific)
            last_date = closes.index[-1]
            next_date = pd.to_datetime(last_date) + pd.Timedelta(days=1)
            next_ord = pd.Timestamp(next_date).toordinal()
            pred = float(trained.predict([[next_ord]])[0])
            used_trained = True
            logging.info("Using per-symbol trained model for %s: %s", symbol, model_path_specific)
        except Exception:
            logging.exception("Per-symbol trained model failed for %s", symbol)
            pred = None
    else:
        if model_path_global.exists():
            logging.info("Global trained model exists at %s but will NOT be used for symbol %s. Using fallback regression.", model_path_global, symbol)
        else:
            logging.info("No trained model found for symbol %s; using fallback regression.", symbol)

    if pred is None:
        try:
            X = np.arange(len(prices)).reshape(-1, 1)
            y = np.array(prices)
            lr = LinearRegression()
            lr.fit(X, y)
            pred = float(lr.predict(np.array([[len(prices)]]))[0])
        except Exception:
            logging.exception("Fallback regression failed for symbol %s", symbol)
            raise HTTPException(status_code=500, detail=f"Failed to compute prediction for {symbol}")

    try:
        last_close = float(closes.iloc[-1])
    except Exception:
        last_close = None

    logging.info("Predict for %s: rows=%d last_close=%s predicted_price=%.6f used_trained=%s", symbol, len(closes), last_close, pred, used_trained)

    return {"symbol": symbol, "dates": dates, "prices": prices, "predicted_price": pred, "used_trained_model": used_trained}


@app.post("/chat")
def chat_ai(req: ChatRequest):
    # Detect symbols, collect predictions, build comparison summary, and send to Ollama for commentary
    default_url = 'http://localhost:11434/v1/chat/completions'
    ollama_url = os.getenv('OLLAMA_URL', default_url).rstrip('/')
    ollama_model = os.getenv('OLLAMA_MODEL', 'llama3.1')

    import re

    # Detect symbols: prefer $SYMBOL first, then uppercase tokens (2-5 chars). Keep order and dedupe.
    raw_candidates = []
    raw_candidates += re.findall(r"\$([A-Z]{1,5})\b", req.message)
    raw_candidates += re.findall(r"\b([A-Z]{2,5})\b", req.message)
    seen = set()
    candidates_ordered = [c for c in raw_candidates if not (c in seen or seen.add(c))]

    logging.info("/chat detected candidates: %s", candidates_ordered)

    all_predictions = {}
    primary_symbol = None
    primary_price = None

    # Collect predictions for each candidate using the local predict_get function
    for cand in candidates_ordered:
        try:
            pred_json = predict_get(symbol=cand, days=30)
            if pred_json and 'predicted_price' in pred_json:
                price = float(pred_json['predicted_price'])
                all_predictions[cand] = price
                logging.info("/chat prediction: %s -> %.6f", cand, price)
                if primary_symbol is None:
                    primary_symbol = cand
                    primary_price = price
        except HTTPException as he:
            logging.warning("predict_get HTTP error for %s: %s", cand, he.detail)
            continue
        except Exception as e:
            logging.exception("predict_get failed for %s", cand)
            continue

    # Build plain text listing of predictions
        # Prefer the API chat endpoint; some Ollama builds accept /api/chat only
        ollama_url = os.getenv('OLLAMA_URL', default_url.replace('/v1/chat/completions', '/api/chat')).rstrip('/')
        
        # ensure model tag includes :latest (Ollama expects model:tag)
        ollama_model = os.getenv('OLLAMA_MODEL', 'llama3.1')
        if ':' not in ollama_model:
            ollama_model = ollama_model + ':latest'
        lines = [f"Prediction for {s}: {all_predictions[s]:.2f} USD" for s in all_predictions]
        predictions_text = "\n".join(lines)
    else:
        predictions_text = "No numeric predictions available."

    # Build a concise comparison summary: compare adjacent symbols when sorted by predicted value
    comparison_summary = ""
    if len(all_predictions) == 1:
        comparison_summary = "Only one symbol detected; no comparison available."
    elif len(all_predictions) > 1:
        # sort symbols by price descending
        sorted_syms = sorted(all_predictions.items(), key=lambda kv: kv[1], reverse=True)
        # adjacency comparisons to keep it short
        comps = []
        for i in range(len(sorted_syms) - 1):
            a, pa = sorted_syms[i]
            b, pb = sorted_syms[i+1]
            if pa > pb:
                comps.append(f"{a} is predicted slightly higher than {b}.")
            elif pa < pb:
                comps.append(f"{b} is predicted slightly higher than {a}.")
            else:
                comps.append(f"{a} and {b} are predicted to be the same.")
        comparison_summary = " ".join(comps)

    # Build the prompt: include system instruction, numeric predictions, comparison summary, and user message
    system_instruction = (
        "You are a helpful assistant. The user will provide stock tickers and a question. "
        "Below you will be given exact numeric predictions and a short comparison summary. "
        "Do NOT invent or change the numeric values; base your commentary only on the provided numbers. "
        "Provide a friendly, human-readable commentary referencing the predictions and comparisons. "
        "Keep it concise and avoid giving financial advice."
    )

    user_content = f"User message: {req.message}\n\nNumeric predictions:\n{predictions_text}\n\nComparison summary:\n{comparison_summary}\n\nPlease provide a concise, human-readable commentary based on the numeric data above."

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_content}
    ]

    payload = {"model": ollama_model, "messages": messages, "stream": False}

    logging.info("Ollama payload: %s", payload)

    logging.info("/chat all_predictions: %s", all_predictions)
    logging.info("/chat prompt being sent to Ollama: %s", user_content)

    # Allow configuring request timeout via env var (seconds)
    try:
        timeout = int(os.getenv('OLLAMA_TIMEOUT', '60'))
    except Exception:
        timeout = 60

    try:
        logging.info("Sending request to Ollama: %s", ollama_url)
        resp = requests.post(ollama_url, json=payload, timeout=timeout)
    except requests.exceptions.ConnectTimeout:
        fallback = "Ollama request timed out; numerical predictions returned above."
        logging.exception("Ollama connect timeout")
        return {"symbol": primary_symbol, "predicted_price": primary_price, "response": fallback, "all_predictions": all_predictions, "comparison_summary": comparison_summary}
    except requests.exceptions.ConnectionError:
        fallback = "Ollama API unavailable; numerical predictions returned above."
        logging.exception("Ollama connection error")
        return {"symbol": primary_symbol, "predicted_price": primary_price, "response": fallback, "all_predictions": all_predictions, "comparison_summary": comparison_summary}
    except Exception as e:
        logging.exception("Ollama request failed")
        return {"symbol": primary_symbol, "predicted_price": primary_price, "response": f"Ollama request failed: {e}. Numerical predictions returned above if available.", "all_predictions": all_predictions, "comparison_summary": comparison_summary}

    if resp.status_code != 200:
        logging.error("Ollama returned non-200: %s", resp.text)
        return {"symbol": primary_symbol, "predicted_price": primary_price, "response": f"Ollama returned status {resp.status_code}. Numerical predictions returned above if available.", "all_predictions": all_predictions, "comparison_summary": comparison_summary}

    # Parse JSON response robustly. Some Ollama builds return NDJSON or multiple JSON objects.
    text = resp.text
    try:
        data = resp.json()
    except Exception as e:
        logging.warning("resp.json() failed: %s -- attempting NDJSON parse", e)
        data = None
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                data = obj
            except Exception:
                # ignore non-json lines
                continue
        if data is None:
            logging.exception("Invalid JSON from Ollama; raw response start: %s", text[:1000])
            return {"symbol": primary_symbol, "predicted_price": primary_price, "response": f"Invalid JSON from Ollama: {e}. Numerical predictions returned above if available.", "all_predictions": all_predictions, "comparison_summary": comparison_summary}

    # parse assistant text: prefer top-level `message.content` (Ollama builds),
    # then choices[].message.content (OpenAI-like), then 'answer'.
    assistant_text = ""
    try:
        # Top-level Ollama shape: { "message": { "role": "assistant", "content": "..." }, ... }
        if isinstance(data, dict) and 'message' in data and isinstance(data['message'], dict) and 'content' in data['message']:
            assistant_text = data['message']['content']
        # OpenAI-like choices shape
        elif isinstance(data, dict) and 'choices' in data and len(data['choices']) > 0:
            choice = data['choices'][0]
            if isinstance(choice, dict) and 'message' in choice and isinstance(choice['message'], dict) and 'content' in choice['message']:
                assistant_text = choice['message']['content']
            elif isinstance(choice, dict) and 'content' in choice:
                assistant_text = choice['content']
            else:
                assistant_text = str(choice)
        elif isinstance(data, dict) and 'answer' in data:
            assistant_text = data['answer']
        else:
            assistant_text = str(data)
    except Exception:
        assistant_text = str(data)

    # Ensure assistant_text is a plain string
    if assistant_text is None:
        assistant_text = ""
    elif not isinstance(assistant_text, str):
        try:
            assistant_text = json.dumps(assistant_text)
        except Exception:
            assistant_text = str(assistant_text)

    logging.info("Ollama assistant text extracted: %s", assistant_text)

    # Return assistant text (clean), numeric predictions, and comparison summary
    return {"symbol": primary_symbol, "predicted_price": primary_price, "response": assistant_text, "all_predictions": all_predictions, "comparison_summary": comparison_summary}


@app.get("/chart-data")
def chart_data(symbol: str = "AAPL", days: int = 30):
    dates = pd.date_range(end=pd.Timestamp.today(), periods=days).strftime('%Y-%m-%d').tolist()
    prices = np.random.rand(days) * 100
    return {"dates": dates, "prices": prices}


@app.get("/forecast")
def forecast(symbol: str = "AAPL", history_days: int = 90, predict_days: int = 7):
    """
    Return historical close prices (last `history_days`) and a `predict_days`-long forecast.

    Forecast algorithm: try ETS (ExponentialSmoothing) from statsmodels; if unavailable or it fails,
    fall back to a simple polynomial regression on the historical index.

    Response shape:
    {
      "symbol": "AAPL",
      "history": [{"date":"2025-10-01","price":123.45}, ...],
      "forecast": [{"date":"2025-10-02","price":124.23}, ...],
      "method": "ets"|"poly",
      "model_version": "demo-v1"
    }
    """
    if history_days <= 1 or predict_days < 1:
        raise HTTPException(status_code=400, detail="history_days must be >1 and predict_days must be >=1")

    try:
        tk = yf.Ticker(symbol)
        raw = tk.history(period=f"{max(history_days,30)}d", auto_adjust=False)
    except Exception as e:
        logging.exception("yfinance fetch failed for %s", symbol)
        raise HTTPException(status_code=500, detail=f"Failed to fetch data for {symbol}: {e}")

    if raw is None or raw.empty or 'Close' not in raw.columns:
        logging.warning("No data for symbol %s (raw empty or no Close)", symbol)
        raise HTTPException(status_code=400, detail=f"No data found for symbol: {symbol}")

    closes = raw['Close'].dropna()
    closes = closes.tail(history_days)
    if closes.empty:
        logging.warning("Not enough data for symbol %s after tail(%s)", symbol, history_days)
        raise HTTPException(status_code=400, detail=f"Not enough data for symbol: {symbol}")

    history = [{"date": d.strftime('%Y-%m-%d'), "price": float(p)} for d, p in zip(closes.index, closes.values)]

    # Forecasting
    forecast_vals = None
    method = 'poly'
    try:
        # Try ETS if available (statsmodels)
        from statsmodels.tsa.holtwinters import ExponentialSmoothing

        try:
            # fit on the historical closes (simple additive trend)
            model = ExponentialSmoothing(closes.astype(float), trend='add', seasonal=None, damped_trend=False)
            fitted = model.fit(optimized=True)
            preds = fitted.forecast(predict_days)
            forecast_vals = [float(x) for x in preds]
            method = 'ets'
        except Exception:
            logging.exception('ETS forecasting failed, falling back to polynomial regression')
            forecast_vals = None
    except Exception:
        # statsmodels not installed or import failed; fallback later
        logging.info('statsmodels not available; using polynomial regression fallback')

    if forecast_vals is None:
        # Polynomial regression fallback (degree 2)
        try:
            x = np.arange(len(closes))
            y = np.array(closes.values.astype(float))
            deg = 2 if len(x) >= 3 else 1
            coeffs = np.polyfit(x, y, deg)
            poly = np.poly1d(coeffs)
            future_x = np.arange(len(closes), len(closes) + predict_days)
            forecast_vals = [float(poly(xx)) for xx in future_x]
            method = 'poly'
        except Exception:
            logging.exception('Polynomial fallback failed for %s', symbol)
            raise HTTPException(status_code=500, detail='Failed to compute forecast')

    # Build forecast dates (business days) starting after last historical date
    last_date = pd.to_datetime(closes.index[-1])
    try:
        future_dates = pd.bdate_range(start=last_date + pd.Timedelta(days=1), periods=predict_days)
        future_dates = [d.strftime('%Y-%m-%d') for d in future_dates]
    except Exception:
        # fallback: plain daily dates
        future_dates = [(last_date + pd.Timedelta(days=i+1)).strftime('%Y-%m-%d') for i in range(predict_days)]

    forecast = [{"date": d, "price": float(p)} for d, p in zip(future_dates, forecast_vals)]

    return {"symbol": symbol, "history": history, "forecast": forecast, "method": method, "model_version": "demo-v1"}


@app.get('/health')
def health():
    """Health endpoint: runs `ollama list` via CLI and returns installed models.

    Returns:
      {"status":"ok","models":[...] } on success
      {"status":"error","detail":"..."} on failure
    """
    # Try to find an ollama CLI
    cli = os.getenv('OLLAMA_CLI', 'ollama')
    if not shutil.which(cli):
        # fallback to the common Windows install location
        fallback = str(Path.home() / 'AppData' / 'Local' / 'Programs' / 'Ollama' / 'ollama.exe')
        if Path(fallback).exists():
            cli = fallback

    try:
        if not cli or not shutil.which(cli) and not Path(cli).exists():
            raise RuntimeError('Ollama CLI not found on PATH and fallback not present')

        proc = subprocess.run([cli, 'list'], capture_output=True, text=True, timeout=15)
        if proc.returncode != 0:
            raise RuntimeError(f"ollama list failed: {proc.stderr.strip()}")

        out = proc.stdout.strip()
        models = []
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            # skip header separators
            if line.lower().startswith('name') or line.startswith('----'):
                continue
            # take first column as model name
            parts = line.split()
            if parts:
                models.append(parts[0])

        return {"status": "ok", "models": models}
    except Exception as e:
        logging.exception('Health check failed')
        return {"status": "error", "detail": str(e)}
