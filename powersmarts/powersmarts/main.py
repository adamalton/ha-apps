from __future__ import annotations

import logging
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI

from powersmarts.applicator import DeviceApplicator
from powersmarts.engine import PollingEngine
from powersmarts.home_assistant import HomeAssistantClient
from powersmarts.polling import CloudPoller
from powersmarts.storage import ConfigStore
from powersmarts.web import create_web_app

logger = logging.getLogger("powersmarts")


def configure_logging(level_name: str | None = None) -> None:
    name = (level_name or os.environ.get("POWERSMARTS_LOG_LEVEL") or "info").upper()
    level = getattr(logging, name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stdout,
        force=True,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def create_app() -> FastAPI:
    configure_logging()
    data_file = Path(os.environ.get("POWERSMARTS_DATA_FILE", "/data/powersmarts.json"))
    ha_url = os.environ.get("POWERSMARTS_HA_URL", "http://supervisor/core/api")
    token = os.environ.get("SUPERVISOR_TOKEN", "")
    ingress_only = os.environ.get("POWERSMARTS_INGRESS_ONLY") == "1"

    store = ConfigStore(data_file)
    http_client = httpx.AsyncClient()
    home_assistant = HomeAssistantClient(ha_url, token, http_client)
    poller = CloudPoller(http_client)
    applicator = DeviceApplicator(home_assistant)
    engine = PollingEngine(store, poller, applicator)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        logger.info("Starting Powersmarts")
        if not token:
            logger.warning("SUPERVISOR_TOKEN is not set; Home Assistant API calls will fail")
        await engine.start()
        try:
            yield
        finally:
            await engine.stop()
            await http_client.aclose()

    return create_web_app(
        store,
        engine,
        home_assistant,
        ingress_only=ingress_only,
        lifespan=lifespan,
    )


def main() -> None:
    host = os.environ.get("POWERSMARTS_HOST", "0.0.0.0")
    port = int(os.environ.get("POWERSMARTS_PORT", "8099"))
    uvicorn.run(create_app(), host=host, port=port, log_config=None)


if __name__ == "__main__":
    main()
