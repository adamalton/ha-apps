from __future__ import annotations

import asyncio
import logging

from powersmarts.applicator import DeviceApplicator
from powersmarts.models import DeviceAutomation
from powersmarts.polling import CloudPoller, PollError, redact_url
from powersmarts.storage import ConfigStore

logger = logging.getLogger("powersmarts")


class PollingEngine:
    """Run one cancellable poll task per enabled automation."""

    def __init__(
        self,
        store: ConfigStore,
        poller: CloudPoller,
        applicator: DeviceApplicator,
    ) -> None:
        self._store = store
        self._poller = poller
        self._applicator = applicator
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._running = False

    async def start(self) -> None:
        self._running = True
        await self.reload()

    async def stop(self) -> None:
        self._running = False
        await self._cancel_tasks()

    async def reload(self) -> None:
        config = self._store.load()
        logger.info("Loaded %s automations", len(config.automations))
        await self._cancel_tasks()
        if not self._running:
            return
        for automation in config.automations:
            if not automation.enabled:
                logger.info("[%s] Disabled; not polling", automation.name)
                continue
            self._tasks[automation.id] = asyncio.create_task(
                self._run_automation(automation),
                name=f"powersmarts-{automation.id}",
            )

    async def process_automation(self, automation: DeviceAutomation) -> None:
        url = redact_url(automation.poll_url)
        logger.debug("[%s] Polling %s", automation.name, url)
        try:
            desired = await self._poller.fetch(automation)
        except PollError as exc:
            logger.error("[%s] poll failed: %s", automation.name, exc)
            return
        except Exception:
            logger.exception("[%s] poll failed", automation.name)
            return

        if desired.power is not None:
            logger.debug("[%s] Desired state: %s", automation.name, desired.power)
        try:
            await self._applicator.apply(automation, desired)
        except Exception:
            logger.exception("[%s] Home Assistant update failed", automation.name)

    async def _run_automation(self, automation: DeviceAutomation) -> None:
        interval = max(1, automation.poll_interval_seconds)
        while True:
            await self.process_automation(automation)
            try:
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                raise

    async def _cancel_tasks(self) -> None:
        tasks = list(self._tasks.values())
        self._tasks.clear()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
