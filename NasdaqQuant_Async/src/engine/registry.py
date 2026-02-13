import json
import os
from datetime import datetime
from src.utils.config import REGISTRY_FILE

def load_registry():
    if os.path.exists(REGISTRY_FILE):
        try:
            with open(REGISTRY_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: return {}
    return {}

def save_to_registry(ticker, strategy_data):
    registry = load_registry()
    registry[ticker.upper()] = {**strategy_data, "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    # Ensure directory exists
    os.makedirs(os.path.dirname(REGISTRY_FILE), exist_ok=True)
    with open(REGISTRY_FILE, 'w', encoding='utf-8') as f: json.dump(registry, f, indent=2, ensure_ascii=False)

def get_registered_strategy(ticker):
    return load_registry().get(ticker.upper())
