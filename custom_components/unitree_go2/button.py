"""Button platform for Unitree Go2."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import Go2DataCoordinator

_LOGGER = logging.getLogger(__name__)

DIRECTION_BUTTONS = [
    ("move_forward", "mdi:arrow-up-bold", 1, 0, 0),
    ("move_backward", "mdi:arrow-down-bold", -1, 0, 0),
    ("move_left", "mdi:arrow-left-bold", 0, 1, 0),
    ("move_right", "mdi:arrow-right-bold", 0, -1, 0),
    ("turn_left", "mdi:rotate-left", 0, 0, 1),
    ("turn_right", "mdi:rotate-right", 0, 0, -1),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Go2DataCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        Go2EmergencyStopButton(coordinator, entry),
        Go2ExecuteCommandButton(coordinator, entry),
    ]
    for key, icon, x, y, yaw in DIRECTION_BUTTONS:
        entities.append(Go2DirectionButton(coordinator, entry, key, icon, x, y, yaw))
    async_add_entities(entities)


def _device_info(coordinator: Go2DataCoordinator) -> dict:
    return {
        "identifiers": {(DOMAIN, coordinator.robot_ip)},
        "name": f"Go2 Pro ({coordinator.serial or coordinator.robot_ip})",
        "manufacturer": "Unitree",
        "model": "Go2 Pro",
    }


class Go2EmergencyStopButton(CoordinatorEntity[Go2DataCoordinator], ButtonEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "emergency_stop"
    _attr_icon = "mdi:stop-circle"

    def __init__(self, coordinator: Go2DataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"go2_{entry.entry_id}_emergency_stop"

    @property
    def device_info(self):
        return _device_info(self.coordinator)

    async def async_press(self) -> None:
        _LOGGER.warning("Emergency stop triggered")
        await self.coordinator.async_emergency_stop()


class Go2ExecuteCommandButton(CoordinatorEntity[Go2DataCoordinator], ButtonEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "execute_command"
    _attr_icon = "mdi:play"

    def __init__(self, coordinator: Go2DataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"go2_{entry.entry_id}_execute_command"

    @property
    def device_info(self):
        return _device_info(self.coordinator)

    async def async_press(self) -> None:
        select = self.coordinator.command_select
        if select is None or select.command_key is None:
            raise HomeAssistantError("No command selected")
        command = select.command_key
        _LOGGER.info("Executing selected command: %s", command)
        await self.coordinator.async_sport_command(command)


class Go2DirectionButton(CoordinatorEntity[Go2DataCoordinator], ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: Go2DataCoordinator, entry: ConfigEntry,
                 key: str, icon: str, x: float, y: float, yaw: float) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"go2_{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_icon = icon
        self._x = x
        self._y = y
        self._yaw = yaw

    @property
    def device_info(self):
        return _device_info(self.coordinator)

    async def async_press(self) -> None:
        await self.coordinator.async_move_direction(self._x, self._y, self._yaw)
