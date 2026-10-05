from __future__ import annotations

from typing import Any

import pytest

from powersmarts.applicator import DeviceApplicator
from powersmarts.models import DesiredState
from tests.helpers import make_automation


class FakeHomeAssistant:
    def __init__(self, states: dict[str, str]) -> None:
        self.states = states
        self.calls: list[tuple[str, list[str]]] = []

    async def get_state(self, entity_id: str) -> dict[str, Any] | None:
        if entity_id not in self.states:
            return None
        return {"entity_id": entity_id, "state": self.states[entity_id]}

    async def turn_on(self, entity_ids: list[str]) -> None:
        self.calls.append(("on", list(entity_ids)))
        for entity_id in entity_ids:
            self.states[entity_id] = "on"

    async def turn_off(self, entity_ids: list[str]) -> None:
        self.calls.append(("off", list(entity_ids)))
        for entity_id in entity_ids:
            self.states[entity_id] = "off"


@pytest.mark.asyncio
async def test_turn_on_when_off() -> None:
    ha = FakeHomeAssistant({"switch.dehumidifier": "off"})
    applicator = DeviceApplicator(ha)  # type: ignore[arg-type]
    await applicator.apply(make_automation(), DesiredState(power="on"))
    assert ha.calls == [("on", ["switch.dehumidifier"])]


@pytest.mark.asyncio
async def test_turn_off_when_on() -> None:
    ha = FakeHomeAssistant({"switch.dehumidifier": "on"})
    applicator = DeviceApplicator(ha)  # type: ignore[arg-type]
    await applicator.apply(make_automation(), DesiredState(power="off"))
    assert ha.calls == [("off", ["switch.dehumidifier"])]


@pytest.mark.asyncio
async def test_multiple_target_entities() -> None:
    ha = FakeHomeAssistant({"switch.one": "off", "switch.two": "off"})
    applicator = DeviceApplicator(ha)  # type: ignore[arg-type]
    automation = make_automation(target_entities=["switch.one", "switch.two"])
    await applicator.apply(automation, DesiredState(power="on"))
    assert ha.calls == [("on", ["switch.one", "switch.two"])]


@pytest.mark.asyncio
async def test_no_service_call_when_already_correct() -> None:
    ha = FakeHomeAssistant({"switch.dehumidifier": "on"})
    applicator = DeviceApplicator(ha)  # type: ignore[arg-type]
    await applicator.apply(make_automation(), DesiredState(power="on"))
    assert ha.calls == []


@pytest.mark.asyncio
async def test_missing_entity_is_skipped() -> None:
    ha = FakeHomeAssistant({})
    applicator = DeviceApplicator(ha)  # type: ignore[arg-type]
    await applicator.apply(make_automation(), DesiredState(power="on"))
    assert ha.calls == []


@pytest.mark.asyncio
async def test_unavailable_entity_is_updated() -> None:
    ha = FakeHomeAssistant({"switch.dehumidifier": "unavailable"})
    applicator = DeviceApplicator(ha)  # type: ignore[arg-type]
    await applicator.apply(make_automation(), DesiredState(power="off"))
    assert ha.calls == [("off", ["switch.dehumidifier"])]
