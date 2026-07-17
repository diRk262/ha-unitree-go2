"""Unitree Go2 integration for Home Assistant."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import (
    DOMAIN, CONF_ROBOT_IP, CONF_AES_KEY, CONF_SERIAL,
    STATIONARY_COMMANDS, STATIONARY_CONTROLLER_COMMANDS,
    MOVEMENT_CONTROLLER_COMMANDS, DOUBLE_CLICK_COMMANDS,
)
from .coordinator import Go2DataCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "camera", "switch", "number", "button", "select"]

MOVE_SCHEMA = vol.Schema({
    vol.Required("x"): vol.Coerce(float),
    vol.Required("y"): vol.Coerce(float),
    vol.Required("yaw"): vol.Coerce(float),
})


def _get_coordinator(hass: HomeAssistant) -> Go2DataCoordinator:
    entries = hass.data.get(DOMAIN, {})
    if not entries:
        raise ValueError("No Unitree Go2 configured")
    return next(iter(entries.values()))


def _make_handler(command: str):
    async def handler(call: ServiceCall) -> None:
        coordinator = _get_coordinator(call.hass)
        await coordinator.async_sport_command(command)
    return handler


def _all_command_names() -> list[str]:
    return (
        list(STATIONARY_COMMANDS)
        + list(STATIONARY_CONTROLLER_COMMANDS)
        + list(MOVEMENT_CONTROLLER_COMMANDS)
        + list(DOUBLE_CLICK_COMMANDS)
    )


def _register_services(hass: HomeAssistant) -> None:
    for cmd in _all_command_names():
        hass.services.async_register(DOMAIN, cmd, _make_handler(cmd))

    async def handle_move(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass)
        await coordinator.async_move(
            x=call.data["x"],
            y=call.data["y"],
            yaw=call.data["yaw"],
        )

    hass.services.async_register(
        DOMAIN, "move", handle_move, schema=MOVE_SCHEMA,
    )

    directions = {
        "move_forward":  (1, 0, 0),
        "move_backward": (-1, 0, 0),
        "move_left":     (0, 1, 0),
        "move_right":    (0, -1, 0),
        "turn_left":     (0, 0, 1),
        "turn_right":    (0, 0, -1),
    }

    for name, (x, y, yaw) in directions.items():
        def _make_dir_handler(dx, dy, dyaw):
            async def handler(call: ServiceCall) -> None:
                coordinator = _get_coordinator(call.hass)
                await coordinator.async_move_direction(dx, dy, dyaw)
            return handler
        hass.services.async_register(DOMAIN, name, _make_dir_handler(x, y, yaw))

DIRECTION_SERVICES = ["move_forward", "move_backward", "move_left", "move_right", "turn_left", "turn_right"]


def _all_service_names() -> list[str]:
    return _all_command_names() + ["move"] + DIRECTION_SERVICES


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = Go2DataCoordinator(
        hass,
        robot_ip=entry.data[CONF_ROBOT_IP],
        aes_key=entry.data[CONF_AES_KEY],
        serial=entry.data.get(CONF_SERIAL, ""),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.services.has_service(DOMAIN, "stand_lock"):
        _register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: Go2DataCoordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_disconnect()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            for cmd in _all_service_names():
                hass.services.async_remove(DOMAIN, cmd)
    return unload_ok
