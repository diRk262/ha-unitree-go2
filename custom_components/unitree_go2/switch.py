"""Switch platform for Unitree Go2."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import Go2DataCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Go2DataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        Go2ObstacleAvoidanceSwitch(coordinator, entry),
        Go2LidarSwitch(coordinator, entry),
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
    _attr_name = "Hinderniserkennung"
    _attr_icon = "mdi:shield-alert"

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
    _attr_name = "LiDAR"
    _attr_icon = "mdi:radar"

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
