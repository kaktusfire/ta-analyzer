from flask import Flask, render_template, request, send_file
import os
import json
from tradingview_ta_v2_fetcher import run_ta_analysis
from cot_fetcher_custom import run_cot_analysis

app = Flask(__name__)
OUTPUT_FOLDER = "output_files"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def load_summary(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Summary za TA fajl (po timeframeovima)
        if "1m" in data:
            summary_html = "<ul>"
            for tf, content in data.items():
                if isinstance(content, dict) and "summary" in content:
                    rec = content["summary"].get("RECOMMENDATION", "N/A")
                    summary_html += f"<li><strong>{tf}</strong>: {rec}</li>"
            summary_html += "</ul>"
            return summary_html

        # Summary za COT fajl
        elif "entries" in data and len(data["entries"]) > 0:
            entry = data["entries"][0]
            group = entry["groups"][0]
            net = group["analysis"].get("net", "N/A")
            dominance = group["analysis"].get("dominance", "N/A")
            alert = group["analysis"].get("alert_level", "N/A")
            traders = group.get("traders", "N/A")
            return f"""
                <p><strong>Market:</strong> {entry['market']}</p>
                <p><strong>Net pozicija:</strong> {net}</p>
                <p><strong>Dominacija:</strong> {dominance}</p>
                <p><strong>Alert nivo:</strong> {alert}, Trgovaca: {traders}</p>
            """

    except Exception as e:
        return f"<p><em>⚠️ Ne mogu učitati sažetak: {str(e)}</em></p>"

@app.route("/", methods=["GET", "POST"])
def index():
    summary = None

    if request.method == "POST":
        symbols = request.form.get("symbols", "")
        mode = request.form.get("mode", "ta")
        if symbols:
            symbols_list = [s.strip().upper() for s in symbols.split(",")]

            if mode == "ta":
                output_path = run_ta_analysis(symbols_list, OUTPUT_FOLDER)
            elif mode == "cot":
                output_path = run_cot_analysis(symbols_list, OUTPUT_FOLDER)
            else:
                return "Nepoznat mod", 400

            if output_path and os.path.exists(output_path):
                summary = load_summary(output_path)
                return render_template("index.html", summary=summary)
            else:
                return "Fajl nije generisan ili ne postoji.", 500

    return render_template("index.html", summary=summary)

if __name__ == "__main__":
    app.run(debug=True)
