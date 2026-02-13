from mcp.server.fastmcp import FastMCP
import threading
import uuid
import time
import json
from src.core.macro import get_detailed_macro_logic
from src.core.valuation import analyze_tech_valuation_full, TechValuationEngine
from src.engine.optimizer import optimize_strategy_async, backtest_engine
from src.indicators import calculate_indicators
from src.engine.registry import save_to_registry, get_registered_strategy # registry.py 구현 필요
import yfinance as yf

mcp = FastMCP("Nasdaq-Master-Agent")
JOBS = {}

@mcp.tool()
def get_market_regime() -> str:
    """거시 경제 국면 조회"""
    data = get_detailed_macro_logic()
    if "error" in data: return f"Error: {data['error']}"
    return f"State: {data['regime']} | Growth: {data['dg']:.2f}% | CPI: {data['di']:.2f}%"

@mcp.tool()
def analyze_tech_valuation(ticker: str) -> str:
    """테크 밸류에이션 분석"""
    val = analyze_tech_valuation_full(ticker)
    if not val: return "Data Not Found"
    return f"Rule of 40: {val['rule_of_40']:.1f} | ERG: {val['erg_ratio']:.2f}"

if __name__ == "__main__":
    mcp.run()
