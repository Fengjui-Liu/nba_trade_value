# CBA Rule Scope (Current Baseline and Planned Expansion)

## Current baseline implemented in code
Current salary matching is based on a simplified tiered incoming-salary rule:

- If outgoing `<= 7.5M`: incoming max = `2.0x + 0.25M`
- If outgoing `<= 29.0M`: incoming max = `outgoing + 7.5M`
- If outgoing `> 29.0M`: incoming max = `1.25x + 0.25M`

This is implemented in:
- `src/modules/contract_module.py` (`max_incoming_salary`, `is_salary_match`)
- `src/modules/trade_value_engine.py` (`simulate_trade`)

## Explicitly out of scope in baseline
The following are intentionally not modeled yet:
- Team tax status and apron-state conditional logic.
- Non-simultaneous trade aggregation nuances.
- Trade exception creation/consumption constraints.
- Sign-and-trade, BYC, poison pill, hard-cap edge cases.
- Full roster-count and timing-window validation.

## Phase 1 expansion target
Phase 1 should add a rule-engine layer that can evaluate:
- Team payroll state: below tax, tax, first apron, second apron.
- Aggregation limits and incoming/outgoing constraints by team state.
- Explicit rule result payload with reason codes for failures.

## Validation approach
- Table-driven tests for each rule path.
- Golden-scenario regression tests with expected `salary_match` outcomes.
- Deterministic fixtures; no network required.

