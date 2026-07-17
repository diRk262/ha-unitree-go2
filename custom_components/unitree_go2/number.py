"""Number platform for Unitree Go2."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
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
    speed_slider = Go2MoveSpeedNumber(coordinator, entry)
    duration_slider = Go2MoveDurationNumber(coordinator, entry)
    coordinator.move_speed = speed_slider
    coordinator.move_duration = duration_slider
    async_add_entities([
        Go2VolumeNumber(coordinator, entry),
        Go2BrightnessNumber(coordinator, entry),
        speed_slider,
        duration_slider,
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
    _attr_translation_key = "volume"
    _attr_icon = "mdi:volume-high"
    _attr_entity_category = EntityCategory.CONFIG
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
    _attr_translation_key = "brightness"
    _attr_icon = "mdi:brightness-6"
    _attr_entity_category = EntityCategory.CONFIG
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


class Go2MoveSpeedNumber(CoordinatorEntity[Go2DataCoordinator], NumberEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "move_speed"
    _attr_icon = "mdi:speedometer"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 0.1
    _attr_native_max_value = 1.0
    _attr_native_step = 0.1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: Go2DataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"go2_{entry.entry_id}_move_speed"
        self._speed = 0.3

    @property
    def device_info(self):
        return _device_info(self.coordinator)

    @property
    def native_value(self) -> float:
        return self._speed

    async def async_set_native_value(self, value: float) -> None:
        self._speed = round(value, 1)
        self.async_write_ha_state()


class Go2MoveDurationNumber(CoordinatorEntity[Go2DataCoordinator], NumberEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "move_duration"
    _attr_icon = "mdi:timer-outline"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 0.1
    _attr_native_max_value = 3.0
    _attr_native_step = 0.1
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = "s"

    def __init__(self, coordinator: Go2DataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"go2_{entry.entry_id}_move_duration"
        self._duration = 0.5

    @property
    def device_info(self):
        return _device_info(self.coordinator)

    @property
    def native_value(self) -> float:
        return self._duration

    async def async_set_native_value(self, value: float) -> None:
        self._duration = round(value, 1)
        self.async_write_ha_state()
