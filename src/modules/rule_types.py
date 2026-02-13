"""
Types for CBA trade rule engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List


RULE_VERSION = "cba_v1"


class TaxState(str, Enum):
    BELOW_TAX = "below_tax"
    TAX = "tax"
    APRON_1 = "apron_1"
    APRON_2 = "apron_2"


@dataclass(frozen=True)
class TeamCBAContext:
    team_code: str
    payroll_m: float
    tax_state: TaxState


@dataclass(frozen=True)
class TradeSideInput:
    team_code: str
    outgoing_salary_m: float
    incoming_salary_m: float
    outgoing_players: int = 1
    incoming_players: int = 1


@dataclass
class RuleDecision:
    ok: bool
    max_incoming_m: float
    rule_version: str = RULE_VERSION
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

