"""Unitree Go2 integration for Home Assistant."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_ROBOT_IP, CONF_AES_KEY, CONF_SERIAL
from .coordinator import Go2DataCoordinator

PLATFORMS = ["sensor", "binary_sensor", "camera", "switch", "number"]


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
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: Go2DataCoordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_disconnect()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
