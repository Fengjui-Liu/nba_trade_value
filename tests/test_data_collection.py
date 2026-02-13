from types import SimpleNamespace

from bs4 import BeautifulSoup

from src.data_collection.fix_names_and_merge import normalize_name
from src.data_collection import get_salary_espn


def test_normalize_name_handles_accents_and_punctuation():
    assert normalize_name("Nikola Jokić") == "nikola jokic"
    assert normalize_name("D'Angelo   Russell") == "dangelo russell"


def test_parse_salary_rows_extracts_valid_rows():
    html = """
    <table>
      <tr><th>Rk</th><th>Player</th><th>Team</th><th>Salary</th></tr>
      <tr><td>1</td><td>Player A, G</td><td>LAL</td><td>$50,000,000</td></tr>
      <tr><td>2</td><td>Player B, F</td><td>BOS</td><td>$30,500,000</td></tr>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = get_salary_espn._parse_salary_rows(soup)

    assert rows == [
        {"PLAYER_NAME": "Player A", "TEAM": "LAL", "SALARY": 50000000},
        {"PLAYER_NAME": "Player B", "TEAM": "BOS", "SALARY": 30500000},
    ]


def test_get_espn_salaries_uses_mocked_session(monkeypatch):
    page1 = b"""
    <table>
      <tr><td>1</td><td>Player A, G</td><td>LAL</td><td>$50,000,000</td></tr>
      <tr><td>2</td><td>Player B, F</td><td>BOS</td><td>$30,500,000</td></tr>
    </table>
    """
    # Duplicate page; this triggers early stop via "all duplicates".
    page2 = b"""
    <table>
      <tr><td>1</td><td>Player A, G</td><td>LAL</td><td>$50,000,000</td></tr>
      <tr><td>2</td><td>Player B, F</td><td>BOS</td><td>$30,500,000</td></tr>
    </table>
    """

    class FakeSession:
        def __init__(self):
            self.calls = 0

        def get(self, url, timeout=20):
            self.calls += 1
            if "/page/1" in url:
                return SimpleNamespace(status_code=200, content=page1)
            if "/page/2" in url:
                return SimpleNamespace(status_code=200, content=page2)
            return SimpleNamespace(status_code=404, content=b"")

    monkeypatch.setattr(get_salary_espn, "_build_session", lambda: FakeSession())
    monkeypatch.setattr(get_salary_espn.time, "sleep", lambda _: None)

    df = get_salary_espn.get_espn_salaries(year=2026, max_pages=5, delay_sec=0)

    assert list(df["PLAYER_NAME"]) == ["Player A", "Player B"]
    assert list(df["SALARY"]) == [50000000, 30500000]
    assert list(df["SALARY_M"]) == [50.0, 30.5]

