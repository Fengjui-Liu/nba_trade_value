"""
Export utilities for trade reports.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict


def build_markdown_report(payload: Dict) -> str:
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return "\n".join(
        [
            "# Trade Scenario Report",
            f"Generated: {ts}",
            "",
            f"- Team A sends: {', '.join(payload.get('team_a_gives', [])) or 'None'}",
            f"- Team B sends: {', '.join(payload.get('team_b_gives', [])) or 'None'}",
            f"- Salary Match: {payload.get('salary_match')}",
            f"- Value Difference: {payload.get('value_difference')}",
            f"- Rule Version: {payload.get('rule_version', 'n/a')}",
            f"- Scoring Config Hash: {payload.get('scoring_config_hash', 'n/a')}",
            "",
            "## Explain This Result",
            *[f"- {line}" for line in payload.get("explain", [])],
        ]
    )


def export_markdown(path: str, content: str) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return str(p)


def export_pdf_optional(path: str, content: str):
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except Exception:
        return False, "PDF backend unavailable (install reportlab)"

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(p), pagesize=letter)
    y = 760
    for line in content.splitlines():
        c.drawString(40, y, line[:110])
        y -= 14
        if y < 40:
            c.showPage()
            y = 760
    c.save()
    return True, str(p)
