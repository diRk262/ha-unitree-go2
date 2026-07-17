"""Select platform for Unitree Go2."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN, STATIONARY_COMMANDS, STATIONARY_CONTROLLER_COMMANDS,
    MOVEMENT_CONTROLLER_COMMANDS, DOUBLE_CLICK_COMMANDS,
)
from .coordinator import Go2DataCoordinator

_LOGGER = logging.getLogger(__name__)

DISPLAY_NAMES = {
    "stand_lock": "Stand Lock / Low Down",
    "running": "Running Mode",
    "pose": "Pose",
    "normal": "Normal Mode",
    "endurance": "Endurance",
    "free_avoid": "Free Avoid",
    "cross_step": "Cross Step",
    "bound": "Bound Gait",
    "jump_gait": "Jump Gait",
    "handstand": "Hand Stand",
    "erect": "Erect",
    "damp": "Damping Mode (Emergency!)",
    "unlock_gait": "Unlock / Default Gait",
    "classic": "Classic",
    "free_walk": "Free Walk",
    "recovery_stand": "Stand Up From Fall",
    "stretch": "Stretch",
    "hello": "Shake Hands",
    "heart": "Love",
    "greet": "Greet",
    "front_jump": "Jump Forward",
    "sit": "Sit Down",
    "front_pounce": "Pounce",
    "dance1": "Dance 1",
    "dance2": "Dance 2",
    "balance_stand": "Balance Stand",
    "stop_move": "Stop Move",
    "content": "Content",
}

SECTION_HEADERS = [
    "──── Mode Switch ────",
    "── Customised Movements ──",
    "──── Extra ────",
]

ORDERED_COMMANDS = [
    # ── Mode Switch (remote order) ──
    None,
    "damp", "stand_lock", "unlock_gait", "running", "pose", "normal",
    "classic", "free_walk",
    "free_avoid", "cross_step", "bound", "jump_gait",
    "handstand", "erect", "endurance",
    # ── Customised Movements (remote order) ──
    None,
    "recovery_stand", "stretch", "hello", "heart", "greet",
    "front_jump", "sit", "front_pounce", "dance1", "dance2",
    # ── Extra (not on remote) ──
    None,
    "balance_stand", "stop_move", "content",
]

DISPLAY_OPTIONS: list[str] = []
DISPLAY_TO_CMD: dict[str, str] = {}
_header_idx = 0
for item in ORDERED_COMMANDS:
    if item is None:
        DISPLAY_OPTIONS.append(SECTION_HEADERS[_header_idx])
        _header_idx += 1
    else:
        label = DISPLAY_NAMES[item]
        DISPLAY_OPTIONS.append(label)
        DISPLAY_TO_CMD[label] = item


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Go2DataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        Go2CommandSelect(coordinator, entry),
    ])


def _device_info(coordinator: Go2DataCoordinator) -> dict:
    return {
        "identifiers": {(DOMAIN, coordinator.robot_ip)},
        "name": f"Go2 Pro ({coordinator.serial or coordinator.robot_ip})",
        "manufacturer": "Unitree",
        "model": "Go2 Pro",
    }


class Go2CommandSelect(CoordinatorEntity[Go2DataCoordinator], SelectEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "command_select"
    _attr_icon = "mdi:format-list-bulleted"

    def __init__(self, coordinator: Go2DataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"go2_{entry.entry_id}_command_select"
        self._attr_options = ["---"] + DISPLAY_OPTIONS
        self._attr_current_option = "---"

    @property
    def device_info(self):
        return _device_info(self.coordinator)

    @property
    def command_key(self) -> str | None:
        if self._attr_current_option in (None, "---"):
            return None
        return DISPLAY_TO_CMD.get(self._attr_current_option)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.coordinator.command_select = self

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        self.async_write_ha_state()
