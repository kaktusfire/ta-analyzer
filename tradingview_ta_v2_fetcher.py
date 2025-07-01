
import os
import json
import pandas as pd
from tradingview_ta import TA_Handler, Interval
from modules.utils.save_technical_analysis_json import save_json_data

def load_config():
    config_path = os.path.join("sources", "symbols_config.json")
    with open(config_path, "r") as f:
        return json.load(f)

def normalize_symbol(symbol):
    return symbol.upper().replace("/", "").replace("-", "").replace(" ", "")

def run_ta_analysis(selected_input, output_dir):
    symbols_config = load_config()
    normalized_config = {
        normalize_symbol(k): (k, v) for k, v in symbols_config.items()
    }

    if "ALL" in [s.upper() for s in selected_input]:
        selected_symbols = list(normalized_config.values())
    else:
        selected_symbols = []
        for s in selected_input:
            norm = normalize_symbol(s)
            if norm in normalized_config:
                selected_symbols.append(normalized_config[norm])

    timeframes = {
        "1m": Interval.INTERVAL_1_MINUTE,
        "5m": Interval.INTERVAL_5_MINUTES,
        "15m": Interval.INTERVAL_15_MINUTES,
        "30m": Interval.INTERVAL_30_MINUTES,
        "1h": Interval.INTERVAL_1_HOUR,
        "4h": Interval.INTERVAL_4_HOURS,
        "1d": Interval.INTERVAL_1_DAY,
    }

    for label, config in selected_symbols:
        symbol = config["map"]["tradingview_ta_v2"]
        screener = config.get("screener", "forex")
        exchanges = config.get("exchanges", [])
        exchange = exchanges[0] if exchanges else "OANDA"

        full_data = {}

        for tf_label, interval in timeframes.items():
            try:
                handler = TA_Handler(
                    symbol=symbol,
                    screener=screener,
                    exchange=exchange,
                    interval=interval
                )

                analysis = handler.get_analysis()
                summary = analysis.summary
                indicators = analysis.indicators

                full_data[tf_label] = {
                    "summary": summary,
                    "indicators": indicators
                }

            except Exception as e:
                full_data[tf_label] = {"error": str(e)}

        filename = f"{normalize_symbol(label)}_technical_full.json"
        out_path = os.path.join(output_dir, filename)
        save_json_data(label.replace("/", ""), full_data, filename=filename)
        return out_path
