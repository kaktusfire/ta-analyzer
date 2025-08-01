import os
import json
import re
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

# 📁 Putanje
CONFIG_PATH = Path(__file__).resolve().parents[2] / "sources" / "symbols_config.json"
CACHE_DIR = Path(__file__).resolve().parents[2] / "sources" / "cot_cache"
OUT_DIR = Path("data/ai")

# 📦 Učitaj config
def load_symbols_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def normalize_symbol(s):
    return s.replace("-", "/").replace(" ", "/").upper()

def extract_blocks_from_pre(text):
    lines = text.splitlines()
    blocks = []
    for i, line in enumerate(lines):
        if "OPEN INTEREST IS" in line.upper():
            header_lines = []
            for j in range(1, 4):
                if i - j >= 0:
                    header_lines.insert(0, lines[i - j].strip())
            header = " ".join(header_lines).strip()
            block = "\n".join(lines[i-1:i+60])
            blocks.append((header, block))
    return blocks

def extract_row(lines, after_phrase):
    for i, line in enumerate(lines):
        if after_phrase.upper() in line.upper():
            candidates = lines[i+1:i+4]
            best = ""
            max_count = 0
            for c in candidates:
                count = len(re.findall(r"-?\d[\d,\.]*", c))
                if count > max_count:
                    best = c
                    max_count = count
            return best
    return ""

def extract_largest_traders(lines):
    largest = {}
    pattern = re.compile(r"Percent of Open Interest Held by the Largest (\d) Traders.*?: ([\d\.]+)% Long, ([\d\.]+)% Short")
    for line in lines:
        match = pattern.search(line)
        if match:
            count = int(match.group(1))
            largest[str(count)] = {
                "long": float(match.group(2)),
                "short": float(match.group(3))
            }
    return largest

def parse_cot_block(header, block_text):
    lines = block_text.splitlines()
    categories = ["Non-Commercial", "Commercial", "Spreading", "Total", "Nonreportable"]

    def extract_numbers(line, dtype=int):
        return list(map(lambda x: dtype(x.replace(",", "")), re.findall(r"-?\d[\d,\.]*", line)))

    open_interest = None
    for line in lines:
        m = re.search(r"Open Interest is\s+([\d,]+)", line)
        if m:
            open_interest = int(m.group(1).replace(",", ""))
            break

    pos = extract_numbers(extract_row(lines, "Positions"))
    chg = extract_numbers(extract_row(lines, "Changes from"))
    pct = extract_numbers(extract_row(lines, "Percent of Open Interest"), float)
    trd = extract_numbers(extract_row(lines, "Number of Traders"))
    largest_traders = extract_largest_traders(lines)

    entry = {
        "market": header,
        "open_interest": open_interest,
        "largest_traders": largest_traders,
        "groups": []
    }

    for i, cat in enumerate(categories):
        offset = i * 3
        try:
            long = pos[offset]
            short = pos[offset + 1]
            spread = pos[offset + 2]
            long_chg = chg[offset]
            short_chg = chg[offset + 1]
            spread_chg = chg[offset + 2]
            long_pct = pct[offset] if offset < len(pct) else None
            short_pct = pct[offset + 1] if offset+1 < len(pct) else None
            num_traders = trd[i] if i < len(trd) else None
        except IndexError:
            continue

        net = long - short
        net_change = long_chg - short_chg
        ratio = round(net / open_interest, 4) if open_interest else None
        dominance = "bullish" if net > 0 else "bearish" if net < 0 else "neutral"
        alert = "high" if ratio and abs(ratio) > 0.3 else "medium" if ratio and abs(ratio) > 0.15 else "low"
        density = "low" if num_traders and num_traders < 20 else "normal" if num_traders and num_traders < 50 else "high"

        entry["groups"].append({
            "group": cat,
            "long": long,
            "short": short,
            "spread": spread,
            "traders": num_traders,
            "analysis": {
                "net": net,
                "net_change": net_change,
                "net_ratio": ratio,
                "dominance": dominance,
                "alert_level": alert,
                "flip_tag": False,
                "trader_density": density
            },
            "changes": {
                "long_chg": long_chg,
                "short_chg": short_chg,
                "spread_chg": spread_chg
            },
            "percentages": {
                "long_pct": long_pct,
                "short_pct": short_pct
            }
        })

    return entry

def search_all_sources(report_name):
    results = []
    for file in CACHE_DIR.glob("*.html"):
        with open(file, "r", encoding="utf-8") as f:
            html = f.read()
        soup = BeautifulSoup(html, "html.parser")
        pre = soup.find("pre")
        if not pre:
            continue
        blocks = extract_blocks_from_pre(pre.get_text())
        for header, block in blocks:
            if report_name.upper() in header.upper():
                print(f"📥 Pronađen blok: {report_name} u {file.name}")
                entry = parse_cot_block(header, block)
                entry["source"] = file.stem.split("_")[0]  # npr: financial_lf
                results.append(entry)
    return results

def save_json(symbol_key, data):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{symbol_key.lower().replace('/', '')}_cot.json"
    filepath = OUT_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"💾 JSON snimljen: {filepath}")

# ▶️ MAIN
if __name__ == "__main__":
    cfg = load_symbols_config()
    all_symbols = list(cfg.keys())
    print("📌 Dostupni simboli iz symbols_config.json:")
    print(", ".join(all_symbols))

    user_input = input("Unesi simbol(e) (ALL za sve, FULL za cijeli COT izvještaj): ").strip().lower()

    if user_input == "full":
        os.system("python modules/cot/cot_fetcher_full.py")
        exit()

    selected = all_symbols if user_input == "all" else [normalize_symbol(user_input)]

    for symbol in selected:
        sym_info = next(
            (info for key, info in cfg.items()
             if symbol == key or symbol in [normalize_symbol(alias) for alias in info.get("aliases", [])]),
            None
        )
        print(f"🔍 DEBUG: sym_info for {symbol} →", sym_info)
        if not sym_info or "cot" not in sym_info or "report_name" not in sym_info["cot"]:
            print(f"⚠️ Nema mappinga za simbol: {symbol}")
            continue

        report_name = sym_info["cot"]["report_name"]
        results = search_all_sources(report_name)

        if results:
            result_json = {
                "symbol": symbol,
                "collected_at": datetime.now().isoformat(),
                "entries": results
            }
            save_json(symbol, result_json)
        else:
            print(f"⚠️ Nema rezultata za: {symbol}")
