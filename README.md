# ChoiceStock Trading Research Program

This project implements a trading research tool that scrapes financial data from ChoiceStock and presents it in a web interface, inspired by the reference video.

## Project Structure

- **backend/**: FastAPI server + Selenium Scraper
- **frontend/**: React + Bootstrap UI

## Prerequisites

- Python 3.8+
- Node.js & npm
- Chrome Browser (for Selenium scraping)

## How to Run

### 1. Start the Backend Server

The backend handles the data scraping and API.

1.  Open a terminal/command prompt.
2.  Navigate to the `backend` directory:
    ```bash
    cd backend
    ```
3.  (Optional) Create and activate a virtual environment:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```
4.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
5.  Start the server:
    - **Windows**: Double-click `run_server.bat` or run it from the terminal.
    - **Manual**: `uvicorn main:app --reload`

The server will start at `http://127.0.0.1:8000`.

### 2. Start the Frontend Application

The frontend provides the user interface.

1.  Open a new terminal.
2.  Navigate to the `frontend` directory:
    ```bash
    cd frontend
    ```
3.  Install dependencies:
    ```bash
    npm install
    ```
4.  Start the development server:
    ```bash
    npm run dev
    ```

### 3. Usage

1.  Open your browser and go to the URL provided by the frontend (usually `http://localhost:5173`).
2.  Enter a stock ticker (e.g., `AAPL`, `NVDA`, `005930`) in the input field.
3.  Click "조회" (Search) to view the investment indicators and financial statements.
