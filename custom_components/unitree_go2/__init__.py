"""Unitree Go2 integration for Home Assistant."""
from __future__ import annotations

import logging
from pathlib import Path

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import (
    DOMAIN, CONF_ROBOT_IP, CONF_AES_KEY, CONF_SERIAL,
    CONF_ROBOT_NAME, DEFAULT_ROBOT_NAME,
    STATIONARY_COMMANDS, STATIONARY_CONTROLLER_COMMANDS,
    MOVEMENT_CONTROLLER_COMMANDS, DOUBLE_CLICK_COMMANDS,
)
from .coordinator import Go2DataCoordinator
from .intent import async_setup_intents

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

NAVIGATE_SCHEMA = vol.Schema({
    vol.Required("x"): vol.Coerce(float),
    vol.Required("y"): vol.Coerce(float),
    vol.Optional("yaw", default=0.0): vol.Coerce(float),
})

SLAM_SERVICES = [
    "mapping_start", "mapping_stop",
    "localization_start", "localization_stop",
    "navigation_start", "navigation_stop",
    "navigate_to",
]


def _register_slam_services(hass: HomeAssistant) -> None:
    async def handle_mapping_start(call: ServiceCall) -> None:
        await _get_coordinator(hass).async_mapping_start()

    async def handle_mapping_stop(call: ServiceCall) -> None:
        await _get_coordinator(hass).async_mapping_stop()

    async def handle_localization_start(call: ServiceCall) -> None:
        await _get_coordinator(hass).async_localization_start()

    async def handle_localization_stop(call: ServiceCall) -> None:
        await _get_coordinator(hass).async_localization_stop()

    async def handle_navigation_start(call: ServiceCall) -> None:
        await _get_coordinator(hass).async_navigation_start()

    async def handle_navigation_stop(call: ServiceCall) -> None:
        await _get_coordinator(hass).async_navigation_stop()

    async def handle_navigate_to(call: ServiceCall) -> None:
        await _get_coordinator(hass).async_navigate_to(
            x=call.data["x"],
            y=call.data["y"],
            yaw=call.data["yaw"],
        )

    hass.services.async_register(DOMAIN, "mapping_start", handle_mapping_start)
    hass.services.async_register(DOMAIN, "mapping_stop", handle_mapping_stop)
    hass.services.async_register(DOMAIN, "localization_start", handle_localization_start)
    hass.services.async_register(DOMAIN, "localization_stop", handle_localization_stop)
    hass.services.async_register(DOMAIN, "navigation_start", handle_navigation_start)
    hass.services.async_register(DOMAIN, "navigation_stop", handle_navigation_stop)
    hass.services.async_register(DOMAIN, "navigate_to", handle_navigate_to, schema=NAVIGATE_SCHEMA)


def _all_service_names() -> list[str]:
    return _all_command_names() + ["move"] + DIRECTION_SERVICES + SLAM_SERVICES


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

    robot_name = entry.options.get(CONF_ROBOT_NAME, DEFAULT_ROBOT_NAME)

    if not hass.services.has_service(DOMAIN, "stand_lock"):
        _register_services(hass)
        _register_slam_services(hass)
        await async_setup_intents(hass)

    _install_custom_sentences(hass, robot_name)

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    return True


async def _async_options_updated(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    robot_name = entry.options.get(CONF_ROBOT_NAME, DEFAULT_ROBOT_NAME)
    _install_custom_sentences(hass, robot_name)
    _LOGGER.info("Robot name updated to '%s', sentences regenerated", robot_name)


def _install_custom_sentences(hass: HomeAssistant, robot_name: str) -> None:
    dest_dir = Path(hass.config.config_dir) / "custom_sentences"
    for lang, sentences in _generate_sentences(robot_name).items():
        target = dest_dir / lang
        target.mkdir(parents=True, exist_ok=True)
        (target / "unitree_go2.yaml").write_text(sentences, encoding="utf-8")


def _generate_sentences(name: str) -> dict[str, str]:
    n = name
    return {
        "de": f'''language: "de"
intents:
  UnitreeGo2Command:
    data:
      - sentences:
          - "[{n}] {{command}}"
          - "[{n}] mach {{command}}"
          - "[{n}] mach mal {{command}}"
          - "Roboter {{command}}"
          - "Roboter mach {{command}}"
          - "Hund {{command}}"
          - "Hund mach {{command}}"
        slots:
          command:
            type: "command"
  UnitreeGo2EnableCommands:
    data:
      - sentences:
          - "[{n}] Befehle aktivieren"
          - "[{n}] Befehle an"
          - "[{n}] Befehle einschalten"
          - "Roboter Befehle aktivieren"
          - "Roboter Befehle an"
  UnitreeGo2DisableCommands:
    data:
      - sentences:
          - "[{n}] Befehle deaktivieren"
          - "[{n}] Befehle aus"
          - "[{n}] Befehle ausschalten"
          - "Roboter Befehle deaktivieren"
          - "Roboter Befehle aus"
  UnitreeGo2EnableMovement:
    data:
      - sentences:
          - "[{n}] Bewegung aktivieren"
          - "[{n}] Bewegung an"
          - "[{n}] Bewegung einschalten"
          - "Roboter Bewegung aktivieren"
          - "Roboter Bewegung an"
  UnitreeGo2DisableMovement:
    data:
      - sentences:
          - "[{n}] Bewegung deaktivieren"
          - "[{n}] Bewegung aus"
          - "[{n}] Bewegung ausschalten"
          - "Roboter Bewegung deaktivieren"
          - "Roboter Bewegung aus"
  UnitreeGo2Stop:
    data:
      - sentences:
          - "[{n}] Stop"
          - "[{n}] Stopp"
          - "[{n}] Halt"
          - "[{n}] Notaus"
          - "[{n}] Anhalten"
          - "Roboter Stop"
          - "Roboter Stopp"
          - "Roboter Halt"
          - "Hund Stop"
          - "Hund Stopp"
          - "Hund Halt"
  UnitreeGo2Move:
    data:
      - sentences:
          - "[{n}] (geh|lauf|beweg dich) [nach] {{direction}}"
          - "Roboter (geh|lauf) [nach] {{direction}}"
          - "[{n}] {{direction}}"
        slots:
          direction:
            type: "direction"
lists:
  command:
    wildcard: true
  direction:
    wildcard: true
''',
        "en": f'''language: "en"
intents:
  UnitreeGo2Command:
    data:
      - sentences:
          - "[{n}] {{command}}"
          - "[{n}] do {{command}}"
          - "robot {{command}}"
          - "robot do {{command}}"
          - "dog {{command}}"
          - "dog do {{command}}"
        slots:
          command:
            type: "command"
  UnitreeGo2EnableCommands:
    data:
      - sentences:
          - "[{n}] enable commands"
          - "[{n}] commands on"
          - "[{n}] activate commands"
          - "robot enable commands"
          - "robot commands on"
  UnitreeGo2DisableCommands:
    data:
      - sentences:
          - "[{n}] disable commands"
          - "[{n}] commands off"
          - "[{n}] deactivate commands"
          - "robot disable commands"
          - "robot commands off"
  UnitreeGo2EnableMovement:
    data:
      - sentences:
          - "[{n}] enable movement"
          - "[{n}] movement on"
          - "[{n}] activate movement"
          - "robot enable movement"
          - "robot movement on"
  UnitreeGo2DisableMovement:
    data:
      - sentences:
          - "[{n}] disable movement"
          - "[{n}] movement off"
          - "[{n}] deactivate movement"
          - "robot disable movement"
          - "robot movement off"
  UnitreeGo2Stop:
    data:
      - sentences:
          - "[{n}] stop"
          - "[{n}] halt"
          - "[{n}] emergency stop"
          - "robot stop"
          - "robot halt"
          - "dog stop"
          - "dog halt"
  UnitreeGo2Move:
    data:
      - sentences:
          - "[{n}] (go|move|walk) {{direction}}"
          - "robot (go|move|walk) {{direction}}"
          - "[{n}] {{direction}}"
        slots:
          direction:
            type: "direction"
lists:
  command:
    wildcard: true
  direction:
    wildcard: true
''',
    }


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
