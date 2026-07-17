"""Sensor platform for Unitree Go2."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import Go2DataCoordinator

SENSOR_DEFINITIONS: list[
    tuple[str, str | None, SensorDeviceClass | None, SensorStateClass | None, str | None]
] = [
    ("battery_percent", "%", SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT, None),
    ("battery_current", "A", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, None),
    ("battery_cycles", None, None, SensorStateClass.TOTAL_INCREASING, None),
    ("battery_temp_1", "°C", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, None),
    ("battery_temp_2", "°C", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, None),
    ("body_temp", "°C", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, None),
    ("motor_temp_max", "°C", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, None),
    ("power_v", "V", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, None),
    ("position_x", "m", None, SensorStateClass.MEASUREMENT, None),
    ("position_y", "m", None, SensorStateClass.MEASUREMENT, None),
    ("position_z", "m", None, SensorStateClass.MEASUREMENT, None),
    ("body_height", "m", None, SensorStateClass.MEASUREMENT, None),
    ("velocity_x", "m/s", SensorDeviceClass.SPEED, SensorStateClass.MEASUREMENT, None),
    ("mode", None, None, None, "mdi:robot"),
    ("lidar_dirty", "%", None, SensorStateClass.MEASUREMENT, "mdi:radar"),
    ("lidar_error", None, None, None, "mdi:alert-circle"),
    ("imu_roll", "°", None, SensorStateClass.MEASUREMENT, None),
    ("imu_pitch", "°", None, SensorStateClass.MEASUREMENT, None),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Go2DataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        Go2Sensor(coordinator, entry, *defn) for defn in SENSOR_DEFINITIONS
    )


class Go2Sensor(CoordinatorEntity[Go2DataCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: Go2DataCoordinator,
        entry: ConfigEntry,
        key: str,
        unit: str | None,
        device_class: SensorDeviceClass | None,
        state_class: SensorStateClass | None,
        icon: str | None,
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_translation_key = key
        self._attr_unique_id = f"go2_{entry.entry_id}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        if icon:
            self._attr_icon = icon

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.coordinator.robot_ip)},
            "name": f"Go2 Pro ({self.coordinator.serial or self.coordinator.robot_ip})",
            "manufacturer": "Unitree",
            "model": "Go2 Pro",
        }

    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._key)
