from flask import Flask, render_template, request, send_file
import os
from tradingview_ta_v2_fetcher import run_ta_analysis
from cot_fetcher_custom import run_cot_analysis  # dodano

app = Flask(__name__)
OUTPUT_FOLDER = "output_files"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        symbols = request.form.get("symbols", "")
        mode = request.form.get("mode", "ta")  # novo: dohvat odabranog moda
        if symbols:
            symbols_list = [s.strip().upper() for s in symbols.split(",")]

            if mode == "ta":
                output_path = run_ta_analysis(symbols_list, OUTPUT_FOLDER)
            elif mode == "cot":
                output_path = run_cot_analysis(symbols_list, OUTPUT_FOLDER)
            else:
                return "Nepoznat mod", 400

            if output_path and os.path.exists(output_path):
                return send_file(output_path, as_attachment=True)
            else:
                return "Fajl nije generisan ili ne postoji.", 500

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
