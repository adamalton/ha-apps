from __future__ import annotations

import httpx
import pytest

from powersmarts.polling import CloudPoller, PollError
from tests.helpers import make_automation


@pytest.mark.asyncio
async def test_http_failure_raises_poll_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    poller = CloudPoller(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    with pytest.raises(PollError, match="HTTP 500"):
        await poller.fetch(make_automation())


@pytest.mark.asyncio
async def test_timeout_raises_poll_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("connect timed out")

    poller = CloudPoller(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    with pytest.raises(PollError, match="request failed"):
        await poller.fetch(make_automation())


@pytest.mark.asyncio
async def test_invalid_json_raises_poll_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not-json")

    poller = CloudPoller(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    with pytest.raises(PollError, match="invalid JSON"):
        await poller.fetch(make_automation())


@pytest.mark.asyncio
async def test_successful_on_response() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"state": "on"})

    poller = CloudPoller(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    desired = await poller.fetch(make_automation())
    assert desired.power == "on"
