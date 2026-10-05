from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from powersmarts.models import AppConfig, DeviceAutomation

_ENTITY_ID_RE = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")


class ConfigError(ValueError):
    """Raised when stored or submitted configuration is invalid."""


def new_automation_id() -> str:
    return str(uuid4())


def automation_from_dict(raw: dict[str, Any], *, generate_id: bool = False) -> DeviceAutomation:
    automation_id = str(raw.get("id") or "").strip()
    if generate_id or not automation_id:
        automation_id = new_automation_id()

    headers_raw = raw.get("request_headers") or {}
    if not isinstance(headers_raw, dict):
        raise ConfigError("request_headers must be an object")
    request_headers = {str(key): str(value) for key, value in headers_raw.items()}

    automation = DeviceAutomation(
        id=automation_id,
        name=str(raw.get("name") or "").strip(),
        enabled=bool(raw.get("enabled", True)),
        poll_url=str(raw.get("poll_url") or "").strip(),
        poll_interval_seconds=_as_int(raw.get("poll_interval_seconds"), "poll_interval_seconds"),
        target_entities=_as_entity_list(raw.get("target_entities")),
        request_headers=request_headers,
    )
    validate_automation(automation)
    return automation


def validate_automation(automation: DeviceAutomation) -> None:
    if not automation.name:
        raise ConfigError("Name is required")
    if not automation.poll_url:
        raise ConfigError("Poll URL is required")
    parsed = urlparse(automation.poll_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConfigError("Poll URL must be an HTTP or HTTPS URL")
    if automation.poll_interval_seconds < 1:
        raise ConfigError("Poll interval must be a positive number of seconds")
    if not automation.target_entities:
        raise ConfigError("Select at least one target entity")
    for entity_id in automation.target_entities:
        if not _ENTITY_ID_RE.match(entity_id):
            raise ConfigError(f"Invalid entity ID: {entity_id}")


def _as_int(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{field_name} must be an integer") from exc


def _as_entity_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, list):
        items = value
    else:
        raise ConfigError("target_entities must be a list")
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        entity_id = str(item).strip()
        if not entity_id or entity_id in seen:
            continue
        seen.add(entity_id)
        result.append(entity_id)
    return result


def automation_to_dict(automation: DeviceAutomation) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": automation.id,
        "name": automation.name,
        "enabled": automation.enabled,
        "poll_url": automation.poll_url,
        "poll_interval_seconds": automation.poll_interval_seconds,
        "target_entities": list(automation.target_entities),
    }
    if automation.request_headers:
        payload["request_headers"] = dict(automation.request_headers)
    return payload


class ConfigStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> AppConfig:
        if not self.path.exists():
            return AppConfig()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigError(f"Could not read configuration: {exc}") from exc
        if not isinstance(raw, dict):
            raise ConfigError("Configuration must be a JSON object")
        automations_raw = raw.get("automations") or []
        if not isinstance(automations_raw, list):
            raise ConfigError("automations must be a list")
        automations = [automation_from_dict(item) for item in automations_raw]
        return AppConfig(automations=automations)

    def save(self, config: AppConfig) -> None:
        for automation in config.automations:
            validate_automation(automation)
        payload = {"automations": [automation_to_dict(item) for item in config.automations]}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(payload, indent=2) + "\n"
        temp_path = self.path.with_name(f".{self.path.name}.tmp")
        try:
            temp_path.write_text(serialized, encoding="utf-8")
            os.replace(temp_path, self.path)
        except OSError:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise

    def get(self, automation_id: str) -> DeviceAutomation | None:
        for automation in self.load().automations:
            if automation.id == automation_id:
                return automation
        return None

    def upsert(self, automation: DeviceAutomation) -> None:
        validate_automation(automation)
        config = self.load()
        replaced = False
        next_automations: list[DeviceAutomation] = []
        for existing in config.automations:
            if existing.id == automation.id:
                next_automations.append(automation)
                replaced = True
            else:
                next_automations.append(existing)
        if not replaced:
            next_automations.append(automation)
        self.save(AppConfig(automations=next_automations))

    def delete(self, automation_id: str) -> bool:
        config = self.load()
        remaining = [item for item in config.automations if item.id != automation_id]
        if len(remaining) == len(config.automations):
            return False
        self.save(AppConfig(automations=remaining))
        return True
