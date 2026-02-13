from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sys
import os

# Add the current directory to sys.path so we can import from choicestock_scraper
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from choicestock_scraper.choicestock import scrape_stock_data_json

app = FastAPI()

# Allow CORS for frontend (assuming localhost:5173 for Vite)
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "*" # For development convenience
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/scrape")
async def scrape(ticker: str):
    """
    Endpoint to scrape stock data.
    """
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")
    
    print(f"Received scraping request for: {ticker}")
    
    try:
        data = scrape_stock_data_json(ticker)
        if not data:
             raise HTTPException(status_code=404, detail=f"No data found for ticker: {ticker}")
        return data
    except Exception as e:
        print(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
