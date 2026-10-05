from __future__ import annotations

import json
from pathlib import Path

import pytest

from powersmarts.storage import ConfigError, ConfigStore, automation_from_dict
from tests.helpers import make_automation


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "powersmarts.json"
    store = ConfigStore(path)
    automation = make_automation()
    store.upsert(automation)
    loaded = store.load()
    assert len(loaded.automations) == 1
    assert loaded.automations[0] == automation
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["automations"][0]["name"] == "Dehumidifier"


def test_invalid_config_is_rejected_before_write(tmp_path: Path) -> None:
    path = tmp_path / "powersmarts.json"
    store = ConfigStore(path)
    store.upsert(make_automation())
    original = path.read_text(encoding="utf-8")
    with pytest.raises(ConfigError):
        store.upsert(make_automation(poll_url="not-a-url"))
    assert path.read_text(encoding="utf-8") == original


def test_missing_file_loads_empty(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "missing.json")
    assert store.load().automations == []


def test_delete_automation(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "powersmarts.json")
    store.upsert(make_automation())
    assert store.delete("auto-1") is True
    assert store.load().automations == []


def test_form_payload_validation() -> None:
    with pytest.raises(ConfigError, match="at least one"):
        automation_from_dict(
            {
                "name": "Dehumidifier",
                "poll_url": "https://example.com/state",
                "poll_interval_seconds": 5,
                "target_entities": [],
            },
            generate_id=True,
        )
