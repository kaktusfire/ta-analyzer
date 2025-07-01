import os
import json
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from pathlib import Path
import re

# ⚙️ Konfiguracija putanja
CACHE_DIR = Path("sources/cot_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = Path("data/ai/full_cot_report.json")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = Path("sources/cot_sources_config.json")
TODAY = datetime.now().strftime("%Y-%m-%d")

# 🔧 Učitaj izvorne linkove
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    sources = json.load(f)

def download_and_cache(url, filename):
    path = CACHE_DIR / filename
    if path.exists():
        print(f"📁 Keš postoji: {filename}")
        return path
    print(f"⬇️ Preuzimam: {url}")
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    if response.status_code == 200:
        with open(path, "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"💾 Sačuvano u: {path}")
        return path
    else:
        print(f"❌ Neuspješno preuzimanje: {url} ({response.status_code})")
        return None

def extract_cot_blocks_from_pre(text):
    sections = []
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if "OPEN INTEREST IS" in line.upper():
            header_lines = []
            for i in range(1, 4):
                if idx - i >= 0:
                    header_lines.insert(0, lines[idx - i].strip())
            header = " ".join(header_lines)
            block = "\n".join(lines[idx-1:idx+60])
            sections.append((header.strip(), block))
    return sections

def parse_cot_block_full(market_name, block_text):
    categories = ["Non-Commercial", "Commercial", "Spreading", "Total", "Nonreportable"]
    groups = []
    lines = block_text.splitlines()

    open_interest = None
    for line in lines:
        match = re.search(r"Open Interest is\s+([\d,]+)", line)
        if match:
            open_interest = int(match.group(1).replace(",", ""))
            break

    def extract_row(after_phrase):
        for i, line in enumerate(lines):
            if after_phrase.upper() in line.upper():
                candidates = lines[i+1:i+4]
                best_line = ""
                max_count = 0
                for c in candidates:
                    count = len(re.findall(r"-?\d[\d,\.]*", c))
                    if count > max_count:
                        best_line = c
                        max_count = count
                return best_line
        return ""

    def extract_numbers(line, dtype=int):
        return list(map(lambda x: dtype(x.replace(",", "")), re.findall(r"-?\d[\d,\.]*", line)))

    pos = extract_numbers(extract_row("Positions"), int)
    chg = extract_numbers(extract_row("Changes from"), int)
    pct = extract_numbers(extract_row("Percent of Open Interest"), float)
    trd = extract_numbers(extract_row("Number of Traders"), int)

    result = {
        "market": market_name,
        "open_interest": open_interest,
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
        ratio = round(net / open_interest, 4) if open_interest else None
        dominance = "bullish" if net > 0 else "bearish" if net < 0 else "neutral"
        alert = "high" if ratio and abs(ratio) > 0.3 else "medium" if ratio and abs(ratio) > 0.15 else "low"
        density = "low" if num_traders and num_traders < 20 else "normal" if num_traders and num_traders < 50 else "high"

        group_data = {
            "group": cat,
            "long": long,
            "short": short,
            "spread": spread,
            "traders": num_traders,
            "analysis": {
                "net": net,
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
        }

        result["groups"].append(group_data)

    return result

# 📦 Glavna lista rezultata
full_report = {
    "symbol": "FULL",
    "collected_at": datetime.now().isoformat(),
    "entries": []
}

# 🔁 Loop kroz sve izvore
for source_id, url in sources.items():
    filename = f"{source_id}_{TODAY}.html"
    path = download_and_cache(url, filename)
    if not path:
        continue
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    soup = BeautifulSoup(html, "html.parser")
    pre = soup.find("pre")
    if not pre:
        print(f"⚠️ Nema <pre> taga u: {source_id}")
        continue
    blocks = extract_cot_blocks_from_pre(pre.get_text())
    for header, block in blocks:
        parsed = parse_cot_block_full(header, block)
        if parsed and parsed["groups"]:
            full_report["entries"].append(parsed)

# 💾 Snimi finalni JSON
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(full_report, f, indent=2)

print(f"✅ Full COT izvještaj sačuvan u: {OUTPUT_FILE}")
