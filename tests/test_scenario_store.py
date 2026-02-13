from src.dashboard.scenario_store import ScenarioStore


def test_scenario_store_save_load_rename_delete(tmp_path):
    store = ScenarioStore(base_dir=str(tmp_path))

    payload = {"salary_match": True, "value_difference": -2.5}
    name = store.save("baseline_case", payload)
    assert name == "baseline_case"
    assert "baseline_case" in store.list_scenarios()

    loaded = store.load("baseline_case")
    assert loaded["salary_match"] is True

    renamed = store.rename("baseline_case", "updated_case")
    assert renamed == "updated_case"
    assert "updated_case" in store.list_scenarios()

    store.delete("updated_case")
    assert "updated_case" not in store.list_scenarios()
