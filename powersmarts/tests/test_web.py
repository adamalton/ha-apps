from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from powersmarts.applicator import DeviceApplicator
from powersmarts.engine import PollingEngine
from powersmarts.home_assistant import HomeAssistantClient
from powersmarts.polling import CloudPoller
from powersmarts.storage import ConfigStore
from powersmarts.web import create_web_app
from tests.helpers import make_automation
import httpx


def _app(tmp_path: Path) -> TestClient:
    store = ConfigStore(tmp_path / "powersmarts.json")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/states"):
            return httpx.Response(
                200,
                json=[
                    {
                        "entity_id": "switch.dehumidifier",
                        "state": "off",
                        "attributes": {"friendly_name": "Dehumidifier"},
                    }
                ],
            )
        return httpx.Response(200, json=[])

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    ha = HomeAssistantClient("http://supervisor/core/api", "token", http)
    engine = PollingEngine(store, CloudPoller(http), DeviceApplicator(ha))
    return TestClient(create_web_app(store, engine, ha))


def test_index_lists_automations(tmp_path: Path) -> None:
    client = _app(tmp_path)
    store = ConfigStore(tmp_path / "powersmarts.json")
    store.upsert(make_automation())
    response = client.get("/")
    assert response.status_code == 200
    assert "Powersmarts" in response.text
    assert "Dehumidifier" in response.text
    assert "switch.dehumidifier" in response.text
    assert "Add device automation" in response.text


def test_form_shows_switch_entities(tmp_path: Path) -> None:
    client = _app(tmp_path)
    response = client.get("/automations/new")
    assert response.status_code == 200
    assert "Dehumidifier (switch.dehumidifier)" in response.text


def test_create_automation(tmp_path: Path) -> None:
    client = _app(tmp_path)
    response = client.post(
        "/automations/new",
        data={
            "name": "Dehumidifier",
            "poll_url": "https://example.com/dehumidifier/state",
            "poll_interval_seconds": "5",
            "enabled": "1",
            "target_entities": "switch.dehumidifier",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    loaded = ConfigStore(tmp_path / "powersmarts.json").load()
    assert loaded.automations[0].name == "Dehumidifier"
    assert loaded.automations[0].target_entities == ["switch.dehumidifier"]
