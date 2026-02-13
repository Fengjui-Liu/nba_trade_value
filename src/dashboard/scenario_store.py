"""
Scenario persistence for dashboard trade simulations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


class ScenarioStore:
    def __init__(self, base_dir: str = "data/scenarios"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, name: str) -> Path:
        safe_name = "".join(c for c in name.strip() if c.isalnum() or c in ("_", "-", " ")).strip()
        safe_name = safe_name or "scenario"
        return self.base_dir / f"{safe_name}.json"

    def list_scenarios(self) -> List[str]:
        return sorted(p.stem for p in self.base_dir.glob("*.json"))

    def save(self, name: str, payload: Dict) -> str:
        path = self._path(name)
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return path.stem

    def load(self, name: str) -> Dict:
        path = self._path(name)
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def delete(self, name: str) -> None:
        path = self._path(name)
        if path.exists():
            path.unlink()

    def rename(self, old_name: str, new_name: str) -> str:
        old = self._path(old_name)
        new = self._path(new_name)
        if not old.exists():
            raise FileNotFoundError(old)
        old.rename(new)
        return new.stem
