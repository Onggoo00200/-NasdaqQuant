import sys
import os
import traceback
import asyncio

# Add current dir to path
sys.path.append(os.getcwd())

async def run_comparison():
    try:
        from src.reporting_beta.engine import BetaReportingEngine
        engine = BetaReportingEngine()
        
        tickers = ["NVDA", "TSLA"]
        reports = {}

        print(f"🚀 Starting Deep Analysis Comparison: {tickers}\n")

        for ticker in tickers:
            print(f"--- Analyzing {ticker} ---")
            report = await engine.generate_markdown_report(ticker)
            reports[ticker] = report
            print(f"✅ {ticker} Analysis Complete.\n")

        for ticker, report in reports.items():
            print(f"\n{'='*20} {ticker} REPORT {'='*20}")
            print(report)
            
    except Exception as e:
        print("\n!!! COMPARISON FAILED !!!")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_comparison())
