from __future__ import annotations

import json

import httpx
import pytest

from powersmarts.home_assistant import HomeAssistantClient


def _client_recording(calls: list[httpx.Request], handler=None) -> HomeAssistantClient:
    def default_handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if handler:
            return handler(request)
        if request.method == "GET" and request.url.path.endswith("/states"):
            return httpx.Response(
                200,
                json=[
                    {
                        "entity_id": "switch.dehumidifier",
                        "state": "off",
                        "attributes": {"friendly_name": "Dehumidifier"},
                    },
                    {
                        "entity_id": "light.kitchen",
                        "state": "on",
                        "attributes": {"friendly_name": "Kitchen"},
                    },
                ],
            )
        if request.url.path.endswith("/states/switch.missing"):
            return httpx.Response(404, json={"message": "Entity not found"})
        return httpx.Response(200, json=[])

    http = httpx.AsyncClient(transport=httpx.MockTransport(default_handler))
    return HomeAssistantClient("http://supervisor/core/api", "supervisor-token", http)


@pytest.mark.asyncio
async def test_turn_on_service_call() -> None:
    calls: list[httpx.Request] = []
    client = _client_recording(calls)
    await client.turn_on(["switch.dehumidifier"])
    request = calls[-1]
    assert request.method == "POST"
    assert str(request.url) == "http://supervisor/core/api/services/switch/turn_on"
    assert request.headers["Authorization"] == "Bearer supervisor-token"
    assert json.loads(request.content) == {"entity_id": ["switch.dehumidifier"]}


@pytest.mark.asyncio
async def test_turn_off_service_call() -> None:
    calls: list[httpx.Request] = []
    client = _client_recording(calls)
    await client.turn_off(["switch.dehumidifier", "switch.heater"])
    request = calls[-1]
    assert str(request.url) == "http://supervisor/core/api/services/switch/turn_off"
    assert json.loads(request.content) == {
        "entity_id": ["switch.dehumidifier", "switch.heater"]
    }


@pytest.mark.asyncio
async def test_list_switches_filters_domains() -> None:
    client = _client_recording([])
    switches = await client.list_switches()
    assert [(item.friendly_name, item.entity_id) for item in switches] == [
        ("Dehumidifier", "switch.dehumidifier")
    ]


@pytest.mark.asyncio
async def test_missing_entity_returns_none() -> None:
    client = _client_recording([])
    assert await client.get_state("switch.missing") is None
