from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

PowerState = Literal["on", "off"]


@dataclass(slots=True)
class DeviceAutomation:
    id: str
    name: str
    enabled: bool
    poll_url: str
    poll_interval_seconds: int
    target_entities: list[str]
    request_headers: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class DesiredState:
    """Desired device state returned by Powersmarts cloud.

    The first version only uses ``power``. ``mode`` and ``temperature`` are
    reserved so climate/DEVIreg support can be added without a new model.
    """

    power: PowerState | None = None
    mode: str | None = None
    temperature: float | None = None


@dataclass(slots=True)
class EntityRef:
    entity_id: str
    friendly_name: str


@dataclass(slots=True)
class AppConfig:
    automations: list[DeviceAutomation] = field(default_factory=list)
