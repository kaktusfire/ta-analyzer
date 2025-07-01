
from flask import Flask, render_template, request, send_file
import os
from tradingview_ta_v2_fetcher import run_ta_analysis

app = Flask(__name__)
OUTPUT_FOLDER = "output_files"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        symbols = request.form.get("symbols", "")
        if symbols:
            symbols_list = [s.strip().upper() for s in symbols.split(",")]
            output_path = run_ta_analysis(symbols_list, OUTPUT_FOLDER)
            return send_file(output_path, as_attachment=True)
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
