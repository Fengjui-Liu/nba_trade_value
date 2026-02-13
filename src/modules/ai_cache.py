"""
Deterministic local cache for AI trade commentary.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


class TradeAICache:
    def __init__(self, cache_path: str = "data/cache/ai_trade_cache.json"):
        self.cache_path = Path(cache_path)

    @staticmethod
    def build_cache_key(rule_version: str, scoring_config_hash: str, trade_signature: str) -> str:
        return f"{rule_version}|{scoring_config_hash}|{trade_signature}"

    def _load(self) -> Dict[str, Any]:
        if not self.cache_path.exists():
            return {}
        with self.cache_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data: Dict[str, Any]) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self.cache_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        data = self._load()
        return data.get(key)

    def set(self, key: str, payload: Dict[str, Any]) -> None:
        data = self._load()
        data[key] = payload
        self._save(data)

    def clear(self) -> None:
        self._save({})
