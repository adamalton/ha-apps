from __future__ import annotations

from typing import Any

import httpx

from powersmarts.models import EntityRef


class HomeAssistantError(Exception):
    """Raised when a Home Assistant API call fails."""


class HomeAssistantClient:
    """Home Assistant Core API via the Supervisor proxy."""

    def __init__(self, base_url: str, token: str, client: httpx.AsyncClient) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def get_states(self) -> list[dict[str, Any]]:
        payload = await self._request("GET", "/states")
        if not isinstance(payload, list):
            raise HomeAssistantError("Home Assistant states response was not a list")
        return payload

    async def get_state(self, entity_id: str) -> dict[str, Any] | None:
        try:
            payload = await self._request("GET", f"/states/{entity_id}")
        except HomeAssistantError as exc:
            if "404" in str(exc):
                return None
            raise
        if not isinstance(payload, dict):
            raise HomeAssistantError("Home Assistant state response was not an object")
        return payload

    async def list_switches(self) -> list[EntityRef]:
        entities: list[EntityRef] = []
        for item in await self.get_states():
            entity_id = str(item.get("entity_id") or "")
            if not entity_id.startswith("switch."):
                continue
            attributes = item.get("attributes") or {}
            friendly_name = str(attributes.get("friendly_name") or entity_id)
            entities.append(EntityRef(entity_id=entity_id, friendly_name=friendly_name))
        entities.sort(key=lambda entity: (entity.friendly_name.lower(), entity.entity_id))
        return entities

    async def turn_on(self, entity_ids: list[str]) -> None:
        await self._call_service("switch", "turn_on", {"entity_id": entity_ids})

    async def turn_off(self, entity_ids: list[str]) -> None:
        await self._call_service("switch", "turn_off", {"entity_id": entity_ids})

    async def set_temperature(self, entity_id: str, temperature: float) -> None:
        await self._call_service(
            "climate",
            "set_temperature",
            {"entity_id": entity_id, "temperature": temperature},
        )

    async def _call_service(self, domain: str, service: str, data: dict[str, Any]) -> None:
        await self._request("POST", f"/services/{domain}/{service}", json=data)

    async def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self._base_url}{path}"
        try:
            response = await self._client.request(
                method,
                url,
                headers=self._headers,
                json=json,
                timeout=httpx.Timeout(10.0, connect=5.0),
            )
        except httpx.HTTPError as exc:
            raise HomeAssistantError(f"Home Assistant request failed: {exc.__class__.__name__}") from exc
        if response.status_code == 404:
            raise HomeAssistantError(f"Home Assistant returned HTTP 404 for {path}")
        if response.status_code < 200 or response.status_code >= 300:
            raise HomeAssistantError(f"Home Assistant returned HTTP {response.status_code}")
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return None
