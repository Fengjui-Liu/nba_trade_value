# Phase 0 Specs (Baseline and Guardrails)

## Purpose
Establish a stable baseline before larger feature work so future phases can ship without silent regressions.

## Scope
- Document phased roadmap and rule boundary assumptions.
- Add golden fixtures for deterministic regression checks.
- Add baseline regression tests that validate data and scenario invariants.
- Ensure local developer workflow is documented and repeatable.

## Deliverables
1. Documentation
- `docs/roadmap_phase_specs.md` (this file)
- `docs/cba_rule_scope.md`

2. Golden fixtures
- `tests/fixtures/sample_players_with_salary.csv`
- `tests/fixtures/sample_trade_packages.json`

3. Regression tests
- `tests/test_phase0_regression_fixtures.py`

4. Developer tooling
- `requirements-dev.txt` with pytest tooling
- README developer setup + test commands

## Non-goals (Phase 0)
- No CBA rule engine expansion yet.
- No scoring-model recalibration yet.
- No dashboard feature expansion yet.
- No production AI behavior changes yet.

## Acceptance Criteria
- `python3 -m pytest -q` passes locally.
- Fixture tests fail clearly on malformed fixture data.
- Documentation clearly states current boundary and deferred work.

## Exit Criteria to Enter Phase 1
- Baseline tests are green and deterministic.
- Golden fixtures are committed and treated as regression contracts.
- Rule scope is explicitly documented and agreed.

