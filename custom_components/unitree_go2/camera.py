"""Camera platform for Unitree Go2."""
from __future__ import annotations

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import Go2DataCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Go2DataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        Go2Camera(coordinator, entry),
        Go2LidarCamera(coordinator, entry),
    ])


class Go2Camera(Camera):
    _attr_has_entity_name = True
    _attr_translation_key = "camera"
    _attr_is_streaming = True

    def __init__(
        self, coordinator: Go2DataCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__()
        self._coordinator = coordinator
        self._attr_unique_id = f"go2_{entry.entry_id}_camera"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._coordinator.robot_ip)},
            "name": f"Go2 Pro ({self._coordinator.serial or self._coordinator.robot_ip})",
            "manufacturer": "Unitree",
            "model": "Go2 Pro",
        }

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        return self._coordinator.last_frame


class Go2LidarCamera(Camera):
    _attr_has_entity_name = True
    _attr_translation_key = "lidar_map"
    _attr_is_streaming = True
    _attr_icon = "mdi:radar"

    def __init__(
        self, coordinator: Go2DataCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__()
        self._coordinator = coordinator
        self._attr_unique_id = f"go2_{entry.entry_id}_lidar_camera"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._coordinator.robot_ip)},
            "name": f"Go2 Pro ({self._coordinator.serial or self._coordinator.robot_ip})",
            "manufacturer": "Unitree",
            "model": "Go2 Pro",
        }

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        return self._coordinator.last_lidar_frame
