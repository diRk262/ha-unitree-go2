"""Switch platform for Unitree Go2."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MOVEMENT_SWITCH_TIMEOUT
from .coordinator import Go2DataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Go2DataCoordinator = hass.data[DOMAIN][entry.entry_id]
    stationary_switch = Go2StationarySwitch(coordinator, entry)
    movement_switch = Go2MovementSwitch(coordinator, entry, stationary_switch)
    coordinator.stationary_switch = stationary_switch
    coordinator.movement_switch = movement_switch
    async_add_entities([
        Go2ObstacleAvoidanceSwitch(coordinator, entry),
        Go2LidarSwitch(coordinator, entry),
        stationary_switch,
        movement_switch,
    ])


def _device_info(coordinator: Go2DataCoordinator) -> dict:
    return {
        "identifiers": {(DOMAIN, coordinator.robot_ip)},
        "name": f"Go2 Pro ({coordinator.serial or coordinator.robot_ip})",
        "manufacturer": "Unitree",
        "model": "Go2 Pro",
    }


class Go2ObstacleAvoidanceSwitch(CoordinatorEntity[Go2DataCoordinator], SwitchEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "obstacle_avoidance"
    _attr_icon = "mdi:shield-alert"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: Go2DataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"go2_{entry.entry_id}_obstacle_avoidance_switch"

    @property
    def device_info(self):
        return _device_info(self.coordinator)

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        val = self.coordinator.data.get("obstacle_avoidance", "unknown")
        if val == "unknown":
            return None
        return val == "on"

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_obstacle_avoidance(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_obstacle_avoidance(False)


class Go2LidarSwitch(CoordinatorEntity[Go2DataCoordinator], SwitchEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "lidar"
    _attr_icon = "mdi:radar"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: Go2DataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"go2_{entry.entry_id}_lidar_switch"

    @property
    def device_info(self):
        return _device_info(self.coordinator)

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("lidar_active", False)

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_lidar(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_lidar(False)


class Go2StationarySwitch(CoordinatorEntity[Go2DataCoordinator], SwitchEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "commands_enabled"
    _attr_icon = "mdi:dog-side"

    def __init__(self, coordinator: Go2DataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"go2_{entry.entry_id}_commands_enabled"
        self._is_on = False
        self._timeout_cancel = None

    @property
    def device_info(self):
        return _device_info(self.coordinator)

    @property
    def is_on(self) -> bool:
        return self._is_on

    def reset_timeout(self) -> None:
        if self._timeout_cancel is not None:
            self._timeout_cancel()
        if self._is_on:
            self._timeout_cancel = async_call_later(
                self.hass, MOVEMENT_SWITCH_TIMEOUT, self._auto_off
            )

    @callback
    def _auto_off(self, _now) -> None:
        _LOGGER.info("Commands switch auto-off after %ds inactivity", MOVEMENT_SWITCH_TIMEOUT)
        self._is_on = False
        self._timeout_cancel = None
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs) -> None:
        self._is_on = True
        self.reset_timeout()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self._is_on = False
        if self._timeout_cancel is not None:
            self._timeout_cancel()
            self._timeout_cancel = None
        self.async_write_ha_state()


class Go2MovementSwitch(CoordinatorEntity[Go2DataCoordinator], SwitchEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "movement_enabled"
    _attr_icon = "mdi:robot"

    def __init__(self, coordinator: Go2DataCoordinator, entry: ConfigEntry, stationary_switch: Go2StationarySwitch) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"go2_{entry.entry_id}_movement_enabled"
        self._is_on = False
        self._timeout_cancel = None
        self._stationary_switch = stationary_switch

    @property
    def device_info(self):
        return _device_info(self.coordinator)

    @property
    def is_on(self) -> bool:
        return self._is_on

    def reset_timeout(self) -> None:
        if self._timeout_cancel is not None:
            self._timeout_cancel()
        if self._is_on:
            self._timeout_cancel = async_call_later(
                self.hass, MOVEMENT_SWITCH_TIMEOUT, self._auto_off
            )

    @callback
    def _auto_off(self, _now) -> None:
        _LOGGER.info("Movement switch auto-off after %ds inactivity", MOVEMENT_SWITCH_TIMEOUT)
        self._is_on = False
        self._timeout_cancel = None
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs) -> None:
        self._is_on = True
        if not self._stationary_switch.is_on:
            await self._stationary_switch.async_turn_on()
        self.reset_timeout()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self._is_on = False
        if self._timeout_cancel is not None:
            self._timeout_cancel()
            self._timeout_cancel = None
        self.async_write_ha_state()
