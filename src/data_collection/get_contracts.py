import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

def money_to_int(x: str):
    if x is None:
        return None
    x = x.strip()
    if not x or x in {"-", "—"}:
        return None
    # "$62,587,158" -> 62587158
    m = re.sub(r"[^0-9]", "", x)
    return int(m) if m else None

def pct_to_float(x: str):
    if x is None:
        return None
    x = x.strip()
    if not x or x in {"-", "—"}:
        return None
    x = x.replace("%", "")
    try:
        return float(x)
    except:
        return None

def parse_contract_breakdown_table(table):
    """
    回傳: list[dict]，每列是一個年度 row，key 會是表頭 th 的文字
    """
    # 1) headers
    headers = []
    for th in table.select("thead th"):
        t = th.get_text(" ", strip=True)
        headers.append(t if t else f"col_{len(headers)}")

    # 2) rows
    rows = []
    for tr in table.select("tbody tr"):
        tds = [td.get_text(" ", strip=True) for td in tr.select("td")]
        if not tds:
            continue

        # 若欄位數不一致，做保護：補齊或截斷
        if len(tds) < len(headers):
            tds += [""] * (len(headers) - len(tds))
        elif len(tds) > len(headers):
            tds = tds[:len(headers)]

        row = dict(zip(headers, tds))

        # 3) 常用欄位型別轉換（你也可以依 headers 名稱更精準處理）
        for k, v in list(row.items()):
            if "$" in v:
                row[k] = money_to_int(v)
            elif "%" in v:
                row[k] = pct_to_float(v)

        rows.append(row)

    return headers, rows

def fetch_spotrac_player_contract(player_id: int, slug: str):
    url = f"https://www.spotrac.com/nba/player/_/id/{player_id}/{slug}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}")

    soup = BeautifulSoup(resp.text, "html.parser")

    results = []
    for w in soup.select("div.contract-wrapper"):
        years = w.select_one("h2 span.years")
        years = years.get_text(" ", strip=True) if years else None

        kv = {}
        for cell in w.select("div.contract-details div.cell"):
            label_el = cell.select_one("div.label")
            value_el = cell.select_one("div.value")
            if not label_el:
                continue
            label = label_el.get_text(" ", strip=True).rstrip(":")
            value = value_el.get_text(" ", strip=True) if value_el else ""
            kv[label] = value

        table = w.select_one("table.contract-breakdown")
        headers, rows = (None, None)
        if table:
            headers, rows = parse_contract_breakdown_table(table)

        results.append({
            "years": years,
            "fields": kv,
            "breakdown_headers": headers,
            "breakdown_rows": rows,
        })

    return {"url": url, "contracts": results}

if __name__ == "__main__":
    data = fetch_spotrac_player_contract(6287, "stephen-curry")
    for c in data["contracts"]:
        print("="*80)
        print("Years:", c["years"])
        print("Contract Terms:", c["fields"].get("Contract Terms"))
        if c["breakdown_rows"]:
            print("Breakdown headers:", c["breakdown_headers"])
            print("First row dict:", c["breakdown_rows"][0])
        else:
            print("No breakdown table (maybe premium/empty).")
