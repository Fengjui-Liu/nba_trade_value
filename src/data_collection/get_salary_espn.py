"""
NBA 球員薪資數據收集
從 ESPN 抓取指定賽季薪資資料
"""

import argparse
import re
import time
from typing import List, Dict
import os
import sys

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from src.config import SEASON_END_YEAR, CURRENT_SEASON
except ImportError:
    SEASON_END_YEAR = 2026
    CURRENT_SEASON = "2025-26"


def _build_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=4,
        backoff_factor=0.8,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    })
    return session


def _parse_salary_rows(soup: BeautifulSoup) -> List[Dict]:
    players = []
    rows = soup.select("table tr")
    if not rows:
        rows = soup.find_all("tr")

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 4:
            continue

        rank = cols[0].get_text(strip=True)
        if not rank.isdigit():
            continue

        name = cols[1].get_text(" ", strip=True)
        name = re.sub(r",\s*[GFC]+$", "", name)
        team = cols[2].get_text(strip=True)

        salary_text = cols[3].get_text(strip=True)
        salary_clean = re.sub(r"[^0-9]", "", salary_text)
        if not salary_clean:
            continue

        salary = int(salary_clean)
        if not name or salary <= 0:
            continue

        players.append({
            "PLAYER_NAME": name,
            "TEAM": team,
            "SALARY": salary,
        })

    return players


def get_espn_salaries(year: int = SEASON_END_YEAR, max_pages: int = 30, delay_sec: float = 0.8) -> pd.DataFrame:
    """從 ESPN 抓取所有球員薪資（分頁）。"""
    session = _build_session()
    all_players: List[Dict] = []
    seen_names = set()
    empty_pages = 0

    for page in range(1, max_pages + 1):
        url = f"https://www.espn.com/nba/salaries/_/year/{year}/page/{page}"
        print(f"正在抓取第 {page} 頁: {url}")
        try:
            response = session.get(url, timeout=20)
        except requests.RequestException as exc:
            print(f"  抓取失敗: {exc}")
            break

        if response.status_code != 200:
            print(f"  抓取失敗: HTTP {response.status_code}")
            break

        soup = BeautifulSoup(response.content, "html.parser")
        page_players = _parse_salary_rows(soup)

        if not page_players:
            empty_pages += 1
            print("  本頁無有效資料")
            if empty_pages >= 2:
                print("連續 2 頁無資料，停止抓取")
                break
            time.sleep(delay_sec)
            continue

        empty_pages = 0
        new_players = [p for p in page_players if p["PLAYER_NAME"] not in seen_names]
        for p in new_players:
            seen_names.add(p["PLAYER_NAME"])
        all_players.extend(new_players)
        print(f"  本頁 {len(page_players)} 筆，新增 {len(new_players)} 筆")

        if len(new_players) == 0:
            print("本頁全部為重複資料，停止抓取")
            break

        time.sleep(delay_sec)

    df = pd.DataFrame(all_players).drop_duplicates(subset=["PLAYER_NAME"], keep="first")
    if not df.empty:
        df["SALARY_M"] = (df["SALARY"] / 1_000_000).round(2)
        df = df.sort_values("SALARY", ascending=False).reset_index(drop=True)
    return df


def main():
    parser = argparse.ArgumentParser(description="從 ESPN 抓取 NBA 薪資資料")
    parser.add_argument("--year", type=int, default=SEASON_END_YEAR, help="薪資頁面年份，例如 2026")
    parser.add_argument("--max-pages", type=int, default=30, help="最多抓取頁數")
    parser.add_argument("--delay", type=float, default=0.8, help="每頁抓取間隔秒數")
    parser.add_argument("--output", type=str, default=f"data/raw/player_salaries_{CURRENT_SEASON}.csv", help="輸出檔案")
    args = parser.parse_args()

    df_salary = get_espn_salaries(year=args.year, max_pages=args.max_pages, delay_sec=args.delay)
    if df_salary.empty:
        print("抓取失敗或沒有資料")
        return

    df_salary.to_csv(args.output, index=False)
    print(f"\n薪資數據已儲存至 {args.output}")
    print(f"共抓取 {len(df_salary)} 名球員")
    print("\n薪資前 15 名球員：")
    print(df_salary.head(15).to_string(index=False))


if __name__ == "__main__":
    main()
