import pytest

from src.models.scoring_config import ScoringConfigError, load_scoring_config


def test_load_default_scoring_config_has_meta_and_weights():
    cfg = load_scoring_config("default")
    assert cfg["name"] == "default"
    assert "meta" in cfg
    assert len(cfg["meta"]["hash"]) == 12
    assert round(sum(cfg["trade_value"]["weights"].values()), 6) == 1.0


def test_load_unknown_config_raises():
    with pytest.raises(ScoringConfigError):
        load_scoring_config("does_not_exist")

