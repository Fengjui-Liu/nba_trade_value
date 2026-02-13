"""
Scoring configuration loader and validator.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml


CONFIG_DIR = Path("config/scoring")
DEFAULT_CONFIG_NAME = "default"


class ScoringConfigError(ValueError):
    pass


def _require_keys(obj: Dict[str, Any], keys: set, prefix: str) -> None:
    missing = [k for k in keys if k not in obj]
    extra = [k for k in obj.keys() if k not in keys]
    if missing:
        raise ScoringConfigError(f"{prefix} missing keys: {missing}")
    if extra:
        raise ScoringConfigError(f"{prefix} unknown keys: {extra}")


def _validate_config(config: Dict[str, Any]) -> None:
    _require_keys(config, {"name", "advanced_stats", "salary_model", "fit_model", "trade_value"}, "root")
    _require_keys(config["advanced_stats"], {"league_avg", "value_score_weights", "age_adjustments"}, "advanced_stats")
    _require_keys(config["salary_model"], {"salary_tiers", "market_segments", "age_discounts"}, "salary_model")
    _require_keys(config["fit_model"], {"versatility_weights", "defense_role_scores"}, "fit_model")
    _require_keys(config["trade_value"], {"weights", "tier_thresholds"}, "trade_value")

    adv_w = config["advanced_stats"]["value_score_weights"]
    _require_keys(adv_w, {"pie", "per", "bpm", "production", "ts", "ws"}, "advanced_stats.value_score_weights")
    if round(sum(float(v) for v in adv_w.values()), 6) != 1.0:
        raise ScoringConfigError("advanced_stats.value_score_weights must sum to 1.0")

    fit_w = config["fit_model"]["versatility_weights"]
    _require_keys(fit_w, {"position", "defense", "balance"}, "fit_model.versatility_weights")
    if round(sum(float(v) for v in fit_w.values()), 6) != 1.0:
        raise ScoringConfigError("fit_model.versatility_weights must sum to 1.0")

    tv_w = config["trade_value"]["weights"]
    _require_keys(tv_w, {"performance", "contract", "fit"}, "trade_value.weights")
    if round(sum(float(v) for v in tv_w.values()), 6) != 1.0:
        raise ScoringConfigError("trade_value.weights must sum to 1.0")

    tier = config["trade_value"]["tier_thresholds"]
    _require_keys(tier, {"untouchable", "franchise", "all_star", "quality_starter", "rotation"}, "trade_value.tier_thresholds")


def _hash_config(config: Dict[str, Any]) -> str:
    content = yaml.safe_dump(config, sort_keys=True).encode("utf-8")
    return hashlib.sha256(content).hexdigest()[:12]


@lru_cache(maxsize=8)
def load_scoring_config(name: str = DEFAULT_CONFIG_NAME) -> Dict[str, Any]:
    path = CONFIG_DIR / f"{name}.yaml"
    if not path.exists():
        raise ScoringConfigError(f"config not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    _validate_config(config)
    config["meta"] = {
        "name": config["name"],
        "hash": _hash_config(config),
        "path": str(path),
    }
    return config


def get_default_scoring_config() -> Dict[str, Any]:
    return load_scoring_config(DEFAULT_CONFIG_NAME)

