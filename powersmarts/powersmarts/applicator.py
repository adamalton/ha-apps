from __future__ import annotations

import logging

from powersmarts.home_assistant import HomeAssistantClient, HomeAssistantError
from powersmarts.models import DesiredState, DeviceAutomation

logger = logging.getLogger("powersmarts")


class DeviceApplicator:
    """Apply a desired state to Home Assistant entities."""

    def __init__(self, home_assistant: HomeAssistantClient) -> None:
        self._home_assistant = home_assistant

    async def apply(self, automation: DeviceAutomation, desired: DesiredState) -> None:
        if desired.power is None:
            logger.debug("[%s] No power state to apply", automation.name)
            return
        await self._apply_power(automation, desired.power)

    async def _apply_power(self, automation: DeviceAutomation, power: str) -> None:
        needing_update: list[str] = []
        for entity_id in automation.target_entities:
            if not entity_id.startswith("switch."):
                logger.warning(
                    "[%s] Skipping %s; this version only controls switch entities",
                    automation.name,
                    entity_id,
                )
                continue
            try:
                state = await self._home_assistant.get_state(entity_id)
            except HomeAssistantError:
                logger.exception("[%s] Could not read %s", automation.name, entity_id)
                continue
            if state is None:
                logger.warning("[%s] %s is missing from Home Assistant", automation.name, entity_id)
                continue
            current = str(state.get("state") or "")
            if current == power:
                logger.debug("[%s] %s already %s", automation.name, entity_id, power)
                continue
            needing_update.append(entity_id)

        if not needing_update:
            return

        logger.info("[%s] Turning %s %s", automation.name, ", ".join(needing_update), power)
        if power == "on":
            await self._home_assistant.turn_on(needing_update)
        else:
            await self._home_assistant.turn_off(needing_update)
