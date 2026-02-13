"""
NBA Trade Decision Support Dashboard (Phase 3 redesign).
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd
import plotly.express as px
import streamlit as st

# Project path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.config import CURRENT_SEASON
    from src.models.scoring_config import load_scoring_config
    from src.modules.ai_analysis_module import AIAnalysisModule
    from src.modules.rule_types import RULE_VERSION
    from src.modules.trade_value_engine import TradeValueEngine
except ImportError:
    from config import CURRENT_SEASON
    from models.scoring_config import load_scoring_config
    from modules.ai_analysis_module import AIAnalysisModule
    from modules.rule_types import RULE_VERSION
    from modules.trade_value_engine import TradeValueEngine

try:
    from src.dashboard.dashboard_logic import (
        build_explain_bullets,
        build_metric_pills,
    )
    from src.dashboard.report_export import (
        build_markdown_report,
        export_markdown,
        export_pdf_optional,
    )
    from src.dashboard.scenario_store import ScenarioStore
except ImportError:
    from dashboard_logic import build_explain_bullets, build_metric_pills
    from report_export import build_markdown_report, export_markdown, export_pdf_optional
    from scenario_store import ScenarioStore


st.set_page_config(
    page_title="NBA Trade Decision Support",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
:root {
  --bg: #0a0d12;
  --panel: #111723;
  --card: #171f2e;
  --line: #273246;
  --text: #ebf0f7;
  --muted: #9fb0c8;
  --good: #31c48d;
  --bad: #ff6b6b;
  --accent: #6ea8fe;
}

html, body, [class*="css"] {
  font-family: "Inter", "SF Pro Display", -apple-system, BlinkMacSystemFont, sans-serif;
}

.stApp {
  background: radial-gradient(1200px 380px at 10% -10%, #1a263f 0%, transparent 60%),
              radial-gradient(1200px 420px at 100% -25%, #13324d 0%, transparent 55%),
              var(--bg);
  color: var(--text);
}

.main .block-container {
  max-width: 1280px;
  padding-top: 1.1rem;
  padding-bottom: 2rem;
}

.card {
  background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0));
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 0.95rem 1.05rem;
  box-shadow: 0 14px 30px rgba(0,0,0,0.18);
}

.header-row {
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap: 1rem;
}

.title {
  font-size: 1.55rem;
  font-weight: 700;
  letter-spacing: -0.015em;
  margin: 0;
  color: var(--text);
}

.subtitle {
  margin: 0.15rem 0 0 0;
  color: var(--muted);
  font-size: 0.92rem;
}

.pill {
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 0.22rem 0.58rem;
  font-size: 0.75rem;
  color: var(--muted);
  background: rgba(255,255,255,0.02);
}

.metric-pill {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 0.72rem 0.8rem;
}

.metric-k {
  color: var(--muted);
  font-size: 0.74rem;
  text-transform: uppercase;
  letter-spacing: 0.07em;
}

.metric-v {
  margin-top: 0.2rem;
  font-size: 1.13rem;
  font-weight: 700;
}

.good { color: var(--good); }
.bad { color: var(--bad); }

[data-testid="stSidebar"] {
  background: #0e1420;
  border-right: 1px solid #1f293a;
}

[data-testid="stSidebar"] * {
  color: #d9e3f0;
}

hr {
  border: 0;
  height: 1px;
  background: var(--line);
}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data
def load_data() -> pd.DataFrame:
    path = Path("data/processed/trade_value_full.csv")
    if not path.exists():
        path = Path("../data/processed/trade_value_full.csv")
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _render_header(metrics: Dict[str, str], scoring_cfg: Dict, ai_cached: bool):
    hit = "HIT" if ai_cached else "MISS"
    hit_cls = "good" if ai_cached else "bad"
    st.markdown(
        f"""
<div class="card">
  <div class="header-row">
    <div>
      <p class="title">NBA Trade Decision Support</p>
      <p class="subtitle">{CURRENT_SEASON} | Rule {RULE_VERSION} | Config {scoring_cfg['meta']['name']} · {scoring_cfg['meta']['hash']}</p>
    </div>
    <div style="display:flex; gap:0.45rem; align-items:center;">
      <span class="pill">AI Cache <span class="{hit_cls}">{hit}</span></span>
      <span class="pill">Trade Workbench</span>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='metric-pill'><div class='metric-k'>Trade Value</div><div class='metric-v'>{metrics['trade_value_delta']}</div></div>", unsafe_allow_html=True)
    status_cls = "good" if metrics["salary_match_status"] == "PASS" else "bad"
    c2.markdown(f"<div class='metric-pill'><div class='metric-k'>Salary Match</div><div class='metric-v {status_cls}'>{metrics['salary_match_status']}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-pill'><div class='metric-k'>Cap Impact</div><div class='metric-v'>{metrics['cap_impact_m']}</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='metric-pill'><div class='metric-k'>Fit Score</div><div class='metric-v'>{metrics['fit_score']}</div></div>", unsafe_allow_html=True)


def _get_team_players(df: pd.DataFrame, team: str) -> List[str]:
    if df.empty:
        return []
    return sorted(df[df["TEAM_ABBREVIATION"] == team]["PLAYER_NAME"].tolist())


def _build_sidebar(df: pd.DataFrame):
    teams = sorted(df["TEAM_ABBREVIATION"].dropna().unique().tolist()) if not df.empty else []
    if len(teams) < 2:
        return None

    with st.sidebar.expander("Data", expanded=True):
        st.caption("Dataset snapshot")
        st.write(f"Rows: {len(df)}")
        st.write(f"Teams: {df['TEAM_ABBREVIATION'].nunique()}")

    with st.sidebar.expander("Trade Packages", expanded=True):
        team_a = st.selectbox("Team A", teams, index=0)
        team_b_default = 1 if teams[0] == team_a and len(teams) > 1 else 0
        team_b = st.selectbox("Team B", teams, index=team_b_default)

        a_pool = _get_team_players(df, team_a)
        b_pool = _get_team_players(df, team_b)

        team_a_gives = st.multiselect("Package A (Outgoing)", a_pool)
        team_b_gives = st.multiselect("Package B (Outgoing)", b_pool)

    with st.sidebar.expander("Rules", expanded=False):
        rule = st.selectbox("Salary Rule", [RULE_VERSION, "tiered_2023", "simple_125"], index=0)

    with st.sidebar.expander("Scoring", expanded=False):
        cfg_name = st.selectbox("Config", ["default", "experimental"], index=0)

    with st.sidebar.expander("AI", expanded=False):
        use_ai = st.checkbox("Enable Remote AI", value=False)
        token_mode = st.radio("Token Mode", ["min", "standard"], horizontal=True)
        response_length = st.radio("Response Length", ["short", "medium", "long"], horizontal=True)

    return {
        "team_a": team_a,
        "team_b": team_b,
        "team_a_gives": team_a_gives,
        "team_b_gives": team_b_gives,
        "rule": rule,
        "config_name": cfg_name,
        "use_ai": use_ai,
        "token_mode": token_mode,
        "response_length": response_length,
    }


def _render_summary_tabs(df: pd.DataFrame, selection: Dict, result: Dict, scoring_cfg: Dict, ai_meta: Dict):
    bullets = build_explain_bullets(result)

    tabs = st.tabs(["Summary", "Salary Match", "Value", "Fit", "Contract", "AI Notes", "Scenarios"])

    with tabs[0]:
        c1, c2 = st.columns(2)
        a_details = pd.DataFrame(result["team_a_package"]["details"])
        b_details = pd.DataFrame(result["team_b_package"]["details"])
        c1.markdown("#### Team A Outgoing")
        c1.dataframe(a_details, use_container_width=True)
        c2.markdown("#### Team B Outgoing")
        c2.dataframe(b_details, use_container_width=True)

        st.markdown("#### Explain this result")
        for b in bullets:
            st.markdown(f"- {b}")

    with tabs[1]:
        st.markdown("#### Salary Match Check")
        st.write(f"Rule Version: {result.get('rule_version', selection['rule'])}")
        st.write(f"Salary Match: {result['salary_match']}")
        st.write(f"Salary Diff: {result['salary_diff_m']:.2f}M")
        if "cba" in result:
            c1, c2 = st.columns(2)
            c1.write("Team A Reasons", result["cba"]["team_a"]["reasons"])
            c1.write("Team A Warnings", result["cba"]["team_a"]["warnings"])
            c2.write("Team B Reasons", result["cba"]["team_b"]["reasons"])
            c2.write("Team B Warnings", result["cba"]["team_b"]["warnings"])

    with tabs[2]:
        value_df = pd.DataFrame(
            [
                {
                    "side": "Team A",
                    "trade_value": result["team_a_package"]["total_trade_value"],
                    "surplus": result["team_a_package"]["total_surplus_m"],
                },
                {
                    "side": "Team B",
                    "trade_value": result["team_b_package"]["total_trade_value"],
                    "surplus": result["team_b_package"]["total_surplus_m"],
                },
            ]
        )
        fig = px.bar(value_df, x="side", y=["trade_value", "surplus"], barmode="group", title="Package Value Comparison")
        st.plotly_chart(fig, use_container_width=True)

    with tabs[3]:
        st.markdown("#### Fit Snapshot")
        st.write("Team A avg age outgoing:", result["team_a_package"]["avg_age"])
        st.write("Team B avg age outgoing:", result["team_b_package"]["avg_age"])

    with tabs[4]:
        def _contract_snapshot(players: List[str]):
            if not players:
                return pd.DataFrame()
            cols = [c for c in ["PLAYER_NAME", "CONTRACT_TYPE_CN", "YEARS_REMAINING", "TRADE_RESTRICTIONS", "SALARY_M"] if c in df.columns]
            return df[df["PLAYER_NAME"].isin(players)][cols]

        st.markdown("#### Contract Snapshot")
        st.dataframe(_contract_snapshot(selection["team_a_gives"]), use_container_width=True)
        st.dataframe(_contract_snapshot(selection["team_b_gives"]), use_container_width=True)

    with tabs[5]:
        st.markdown("#### AI Commentary")
        st.write(f"Rule Version: {result.get('rule_version', selection['rule'])}")
        st.write(f"Scoring Config: {scoring_cfg['meta']['name']} ({scoring_cfg['meta']['hash']})")
        st.write(f"Cache: {'HIT' if ai_meta.get('cache_hit') else 'MISS'}")
        st.caption(f"Cache Key: {ai_meta.get('cache_key', '-')}")
        st.markdown(ai_meta.get("text", "No AI commentary generated yet."))

    with tabs[6]:
        _render_scenarios(result, selection, bullets, scoring_cfg)


def _render_scenarios(result: Dict, selection: Dict, bullets: List[str], scoring_cfg: Dict):
    store = ScenarioStore()
    scenario_name = st.text_input("Scenario name", value=f"{selection['team_a']}_vs_{selection['team_b']}")

    payload = {
        "timestamp": datetime.utcnow().isoformat(),
        "team_a": selection["team_a"],
        "team_b": selection["team_b"],
        "team_a_gives": selection["team_a_gives"],
        "team_b_gives": selection["team_b_gives"],
        "salary_match": result["salary_match"],
        "value_difference": result["value_difference"],
        "rule_version": result.get("rule_version", selection["rule"]),
        "scoring_config_hash": scoring_cfg["meta"]["hash"],
        "explain": bullets,
    }

    c1, c2, c3, c4 = st.columns(4)
    if c1.button("Save scenario"):
        saved_name = store.save(scenario_name, payload)
        st.success(f"Saved: {saved_name}")

    scenarios = store.list_scenarios()
    selected = c2.selectbox("Load", ["(none)"] + scenarios)
    if c2.button("Load") and selected != "(none)":
        loaded = store.load(selected)
        st.json(loaded)

    if c3.button("Delete") and selected != "(none)":
        store.delete(selected)
        st.warning(f"Deleted: {selected}")

    new_name = c4.text_input("Rename to", value="")
    if c4.button("Apply") and selected != "(none)" and new_name.strip():
        renamed = store.rename(selected, new_name.strip())
        st.success(f"Renamed to: {renamed}")

    st.markdown("#### Compare")
    compare_sel = st.multiselect("Pick Scenarios", scenarios)
    if compare_sel:
        rows = []
        for name in compare_sel:
            d = store.load(name)
            rows.append(
                {
                    "scenario": name,
                    "salary_match": d.get("salary_match"),
                    "value_difference": d.get("value_difference"),
                    "rule_version": d.get("rule_version"),
                    "scoring_hash": d.get("scoring_config_hash"),
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

    st.markdown("#### Export report")
    md = build_markdown_report(payload)
    md_path = export_markdown("outputs/latest_trade_report.md", md)
    st.write(f"Markdown: {md_path}")

    ok, msg = export_pdf_optional("outputs/latest_trade_report.pdf", md)
    if ok:
        st.success(f"PDF: {msg}")
    else:
        st.info(msg)


def main():
    df = load_data()
    if df.empty:
        st.error("No processed data found. Run `python src/main.py` first.")
        return

    selection = _build_sidebar(df)
    if selection is None:
        st.error("Insufficient teams in dataset.")
        return

    scoring_cfg = load_scoring_config(selection["config_name"])

    default_result = {
        "salary_match": False,
        "salary_diff_m": 0.0,
        "value_difference": 0.0,
        "team_a_package": {"details": [], "avg_age": 0, "total_trade_value": 0, "total_surplus_m": 0},
        "team_b_package": {"details": [], "avg_age": 0, "total_trade_value": 0, "total_surplus_m": 0},
    }

    ai_meta = {"cache_hit": False, "cache_key": "-", "text": "No AI commentary generated yet."}

    result = default_result
    if selection["team_a_gives"] and selection["team_b_gives"]:
        engine = TradeValueEngine(scoring_config=scoring_cfg)
        result = engine.simulate_trade(
            df,
            team_a_gives=selection["team_a_gives"],
            team_b_gives=selection["team_b_gives"],
            rule=selection["rule"],
        )

        ai = AIAnalysisModule()
        if st.sidebar.button("Generate AI Notes"):
            ai_meta = ai.get_trade_commentary(
                df=df,
                team_a=selection["team_a"],
                team_a_gives=selection["team_a_gives"],
                team_b=selection["team_b"],
                team_b_gives=selection["team_b_gives"],
                rule_version=result.get("rule_version", selection["rule"]),
                scoring_config_hash=scoring_cfg["meta"]["hash"],
                use_ai=selection["use_ai"],
                response_length=selection["response_length"],
                token_mode=selection["token_mode"],
            )
            st.session_state["ai_meta"] = ai_meta
        elif "ai_meta" in st.session_state:
            ai_meta = st.session_state["ai_meta"]

    metrics = build_metric_pills(result)
    _render_header(metrics, scoring_cfg, ai_meta.get("cache_hit", False))

    st.markdown("<div style='height:0.25rem'></div>", unsafe_allow_html=True)
    quick_actions = st.columns([1, 1, 6])
    if quick_actions[0].button("Reset"):
        st.session_state.clear()
        st.rerun()
    if quick_actions[1].button("Clear AI Cache"):
        from src.modules.ai_cache import TradeAICache

        TradeAICache().clear()
        st.success("AI cache cleared")

    st.markdown("<div style='height:0.55rem'></div>", unsafe_allow_html=True)
    _render_summary_tabs(df, selection, result, scoring_cfg, ai_meta)


if __name__ == "__main__":
    main()
