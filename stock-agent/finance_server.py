import yfinance as yf
from mcp.server.fastmcp import FastMCP
import json

# FastMCP 서버 인스턴스 생성
# 서버 이름: Yahoo-Finance-Agent
mcp = FastMCP("Yahoo-Finance-Agent")

"""
TIP: 티커(Ticker) 사용법
- 미국 주식: AAPL, TSLA, NVDA 등 (심볼 그대로 사용)
- 한국 주식: 티커 뒤에 시장 구분 접미사를 붙여야 합니다.
  - 코스피: 005930.KS (삼성전자)
  - 코스닥: 066570.KQ (LG전자)
"""

@mcp.tool()
def get_stock_price(ticker: str) -> str:
    """
    특정 종목의 현재 가격과 통화(Currency) 정보를 조회합니다.
    ticker: 종목 코드 (예: AAPL, 005930.KS)
    """
    try:
        stock = yf.Ticker(ticker)
        # fast_info 또는 info 사용 (최신 yfinance 기준)
        info = stock.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        currency = info.get('currency', 'Unknown')
        
        if current_price is None:
            return f"Error: Could not find price for {ticker}. Please check the ticker symbol."
            
        return f"The current price of {ticker} is {current_price} {currency}."
    except Exception as e:
        return f"Error fetching stock price for {ticker}: {str(e)}"

@mcp.tool()
def get_stock_history(ticker: str, period: str = "1mo") -> str:
    """
    특정 기간의 주가 기록(시가, 종가, 최고가, 최저가)을 조회합니다.
    ticker: 종목 코드
    period: 조회 기간 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
    """
    try:
        stock = yf.Ticker(ticker)
        history = stock.history(period=period)
        
        if history.empty:
            return f"No history data found for {ticker} with period {period}."
            
        # LLM이 분석하기 좋게 주요 통계 요약
        summary = {
            "ticker": ticker,
            "period": period,
            "start_date": str(history.index[0].date()),
            "end_date": str(history.index[-1].date()),
            "highest_price": float(history['High'].max()),
            "lowest_price": float(history['Low'].min()),
            "start_price": float(history['Open'].iloc[0]),
            "end_price": float(history['Close'].iloc[-1]),
            "average_volume": float(history['Volume'].mean())
        }
        
        return json.dumps(summary, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Error fetching stock history for {ticker}: {str(e)}"

@mcp.tool()
def get_financial_info(ticker: str) -> str:
    """
    종목의 시가총액, PER, PBR 등 주요 재무 지표를 조회합니다.
    ticker: 종목 코드
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        financial_data = {
            "name": info.get('longName', ticker),
            "market_cap": info.get('marketCap'),
            "trailing_pe": info.get('trailingPE'),
            "forward_pe": info.get('forwardPE'),
            "price_to_book": info.get('priceToBook'),
            "dividend_yield": info.get('dividendYield'),
            "total_revenue": info.get('totalRevenue'),
            "ebitda": info.get('ebitda'),
            "profit_margins": info.get('profitMargins')
        }
        
        # 가독성을 위해 null 값이 아닌 항목들만 정리하여 JSON 반환
        result = {k: v for k, v in financial_data.items() if v is not None}
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Error fetching financial info for {ticker}: {str(e)}"

if __name__ == "__main__":
    # 서버 실행
    mcp.run()
