# 📁 modules/utils/save_technical_analysis_json.py
import os
import json
from datetime import datetime

def save_json_data(symbol: str, data: dict, filename: str = None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    folder_path = os.path.join("data", "ai")
    os.makedirs(folder_path, exist_ok=True)

    if filename is None:
        filename = f"{symbol}_technical_full.json"

    file_path = os.path.join(folder_path, filename)
    data["collected_at"] = timestamp

    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

    print(f"✅ Snimljeno u: {file_path}")
