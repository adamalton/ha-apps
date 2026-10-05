from __future__ import annotations

from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx

from powersmarts.models import DesiredState, DeviceAutomation


class PollError(Exception):
    """Raised when a poll cannot produce a recognised desired state."""


def redact_url(url: str) -> str:
    """Return a URL without query string or fragment for logs."""
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def parse_desired_state(payload: Any) -> DesiredState:
    if not isinstance(payload, dict):
        raise PollError("response is not a JSON object")
    state = payload.get("state")
    if not isinstance(state, str):
        raise PollError("unrecognised state")
    normalized = state.strip().lower()
    if normalized not in {"on", "off"}:
        raise PollError(f"unrecognised state: {state}")
    return DesiredState(power=normalized)


class CloudPoller:
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        connect_timeout: float = 5.0,
        read_timeout: float = 10.0,
    ) -> None:
        self._client = client
        self._timeout = httpx.Timeout(read_timeout, connect=connect_timeout)

    async def fetch(self, automation: DeviceAutomation) -> DesiredState:
        headers = automation.request_headers or None
        try:
            response = await self._client.get(
                automation.poll_url,
                headers=headers,
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise PollError(f"request failed: {exc.__class__.__name__}") from exc
        if response.status_code < 200 or response.status_code >= 300:
            raise PollError(f"HTTP {response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise PollError("invalid JSON") from exc
        return parse_desired_state(payload)
