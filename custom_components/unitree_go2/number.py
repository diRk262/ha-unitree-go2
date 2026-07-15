"""Number platform for Unitree Go2."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
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
        Go2VolumeNumber(coordinator, entry),
        Go2BrightnessNumber(coordinator, entry),
    ])


def _device_info(coordinator: Go2DataCoordinator) -> dict:
    return {
        "identifiers": {(DOMAIN, coordinator.robot_ip)},
        "name": f"Go2 Pro ({coordinator.serial or coordinator.robot_ip})",
        "manufacturer": "Unitree",
        "model": "Go2 Pro",
    }


class Go2VolumeNumber(CoordinatorEntity[Go2DataCoordinator], NumberEntity):
    _attr_has_entity_name = True
    _attr_name = "Lautstärke"
    _attr_icon = "mdi:volume-high"
    _attr_native_min_value = 0
    _attr_native_max_value = 10
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: Go2DataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"go2_{entry.entry_id}_volume_number"

    @property
    def device_info(self):
        return _device_info(self.coordinator)

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("volume", 0)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_volume(int(value))


class Go2BrightnessNumber(CoordinatorEntity[Go2DataCoordinator], NumberEntity):
    _attr_has_entity_name = True
    _attr_name = "Kopflicht"
    _attr_icon = "mdi:brightness-6"
    _attr_native_min_value = 0
    _attr_native_max_value = 10
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: Go2DataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"go2_{entry.entry_id}_brightness_number"

    @property
    def device_info(self):
        return _device_info(self.coordinator)

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("brightness", 0)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_brightness(int(value))
