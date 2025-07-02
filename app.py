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

        # Summary za COT fajl – poboljšan prikaz
        elif "entries" in data and len(data["entries"]) > 0:
            entry = data["entries"][0]
            market = entry["market"]
            oi = entry["open_interest"]
            rows = ""

            for group in entry["groups"]:
                g = group["group"]
                net = group["analysis"].get("net", 0)
                dom = group["analysis"].get("dominance", "-")
                alert = group["analysis"].get("alert_level", "-")
                long_pct = group["percentages"].get("long_pct", 0)
                short_pct = group["percentages"].get("short_pct", 0)
                traders = group.get("traders", 0)

                emoji_dom = "🟢" if dom == "bullish" else "🔴" if dom == "bearish" else "⚪"
                emoji_alert = "🔴" if alert == "high" else "🟠" if alert == "medium" else "🟢"

                rows += f"""
                <tr>
                    <td>{g}</td>
                    <td style='text-align:right;'>{net:+}</td>
                    <td>{emoji_dom} {dom.capitalize()}</td>
                    <td>{emoji_alert} {alert.capitalize()}</td>
                    <td>{long_pct:.1f}%</td>
                    <td>{short_pct:.1f}%</td>
                    <td>{traders}</td>
                </tr>
                """

            return f"""
            <p><strong>📌 Tržište:</strong> {market}<br><strong>📅 Open interest:</strong> {oi}</p>
            <table style="border-collapse: collapse; width: 100%; font-size: 14px;">
                <thead style="background-color: #f3f4f6;">
                    <tr>
                        <th style='text-align:left; padding: 8px; border: 1px solid #ccc;'>Grupa</th>
                        <th style='text-align:right; padding: 8px; border: 1px solid #ccc;'>Net pozicija</th>
                        <th style='text-align:left; padding: 8px; border: 1px solid #ccc;'>Dominacija</th>
                        <th style='text-align:left; padding: 8px; border: 1px solid #ccc;'>Upozorenje</th>
                        <th style='text-align:right; padding: 8px; border: 1px solid #ccc;'>% Long</th>
                        <th style='text-align:right; padding: 8px; border: 1px solid #ccc;'>% Short</th>
                        <th style='text-align:right; padding: 8px; border: 1px solid #ccc;'>Broj Trgovaca</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
            """

    except Exception as e:
        return f"<p><em>⚠️ Ne mogu učitati sažetak: {str(e)}</em></p>"

@app.route("/", methods=["GET", "POST"])
def index():
    summary = None
    download_link = None

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
                rel_path = os.path.relpath(output_path, start=".")
                return render_template("index.html", summary=summary, download_link="/" + rel_path.replace("\\", "/"))
            else:
                return "Fajl nije generisan ili ne postoji.", 500

    return render_template("index.html", summary=summary, download_link=download_link)

@app.route("/output_files/<path:filename>")
def download_file(filename):
    path = os.path.join("output_files", filename)
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    return "Fajl ne postoji", 404

if __name__ == "__main__":
    app.run(debug=True)
