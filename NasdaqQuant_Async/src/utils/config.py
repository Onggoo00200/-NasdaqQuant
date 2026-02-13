import os

# API Keys
FRED_API_KEY = os.environ.get("FRED_API_KEY", "3662881107b1dc7e444adf1dcc698477")

# File Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REGISTRY_FILE = os.path.join(BASE_DIR, "data", "strategy_registry.json")

# Strategy Parameters
PARAM_GRID = {
    'AdaptiveDonchian': [{}], 
    'Supertrend': [{}], 
    'Ichimoku': [{}],
    'LinRegSlope': [{'threshold': 0.2}], 
    'TTMSqueeze': [{}], 
    'CrabelORB': [{}],
    'LarryWilliamsVBO': [{'k': 0.5}, {'k': 0.6}], 
    'ConnorsRSI2': [{'rsi_limit': 5}, {'rsi_limit': 10}],
    'WilliamsRZScore': [{}], 
    'MAEnvelopes': [{}], 
    'VWAPMFI': [{}],
    'AnchoredVWAP': [{}], 
    'OBVDivergence': [{}]
}
