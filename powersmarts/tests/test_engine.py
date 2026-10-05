from __future__ import annotations

from pathlib import Path

import pytest

from powersmarts.applicator import DeviceApplicator
from powersmarts.engine import PollingEngine
from powersmarts.models import DesiredState
from powersmarts.polling import PollError
from powersmarts.storage import ConfigStore
from tests.helpers import make_automation
from tests.test_applicator import FakeHomeAssistant


class FakePoller:
    def __init__(self, results: dict[str, object]) -> None:
        self.results = results
        self.fetched: list[str] = []

    async def fetch(self, automation):  # type: ignore[no-untyped-def]
        self.fetched.append(automation.name)
        result = self.results[automation.name]
        if isinstance(result, Exception):
            raise result
        return result


@pytest.mark.asyncio
async def test_http_failure_leaves_devices_untouched() -> None:
    ha = FakeHomeAssistant({"switch.dehumidifier": "on"})
    store = ConfigStore(Path("/tmp/unused-powersmarts.json"))
    poller = FakePoller({"Dehumidifier": PollError("HTTP 500")})
    engine = PollingEngine(store, poller, DeviceApplicator(ha))  # type: ignore[arg-type]
    await engine.process_automation(make_automation())
    assert ha.calls == []
    assert ha.states["switch.dehumidifier"] == "on"


@pytest.mark.asyncio
async def test_independent_automation_failure() -> None:
    ha = FakeHomeAssistant({"switch.bad": "off", "switch.good": "off"})
    store = ConfigStore(Path("/tmp/unused-powersmarts.json"))
    poller = FakePoller(
        {
            "Broken": PollError("HTTP 500"),
            "Working": DesiredState(power="on"),
        }
    )
    engine = PollingEngine(store, poller, DeviceApplicator(ha))  # type: ignore[arg-type]
    await engine.process_automation(
        make_automation(id="bad", name="Broken", target_entities=["switch.bad"])
    )
    await engine.process_automation(
        make_automation(id="good", name="Working", target_entities=["switch.good"])
    )
    assert ha.calls == [("on", ["switch.good"])]
    assert ha.states["switch.bad"] == "off"
    assert ha.states["switch.good"] == "on"
