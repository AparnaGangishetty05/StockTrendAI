import yfinance as yf
import pandas as pd
from sklearn.linear_model import LinearRegression
import joblib

def fetch_data(symbol='AAPL', period='1y'):
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=period)
    hist = hist.reset_index()
    hist['date_ordinal'] = pd.to_datetime(hist['Date']).map(pd.Timestamp.toordinal)
    return hist[['date_ordinal', 'Close']]

def train_and_save(symbol='AAPL'):
    df = fetch_data(symbol)
    X = df[['date_ordinal']].values
    y = df['Close'].values
    model = LinearRegression()
    model.fit(X, y)
    joblib.dump(model, 'model.pkl')
    print('Saved model.pkl')

if __name__ == '__main__':
    train_and_save()
