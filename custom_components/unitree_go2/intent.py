"""Voice control intents for Unitree Go2."""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, intent

from .const import (
    DOMAIN,
    STATIONARY_COMMANDS, STATIONARY_CONTROLLER_COMMANDS,
    MOVEMENT_CONTROLLER_COMMANDS, DOUBLE_CLICK_COMMANDS,
)

_LOGGER = logging.getLogger(__name__)

INTENT_COMMAND = "UnitreeGo2Command"
INTENT_ENABLE_COMMANDS = "UnitreeGo2EnableCommands"
INTENT_DISABLE_COMMANDS = "UnitreeGo2DisableCommands"
INTENT_ENABLE_MOVEMENT = "UnitreeGo2EnableMovement"
INTENT_DISABLE_MOVEMENT = "UnitreeGo2DisableMovement"
INTENT_STOP = "UnitreeGo2Stop"
INTENT_MOVE = "UnitreeGo2Move"
INTENT_VISION_LOOK = "UnitreeGo2VisionLook"
INTENT_VISION_DESCRIBE = "UnitreeGo2VisionDescribe"
INTENT_VISION_WATCH = "UnitreeGo2VisionWatch"

VOICE_TO_COMMAND = {
    "sit": "sit",
    "sitz": "sit",
    "platz": "sit",
    "hinsetzen": "sit",
    "sit down": "sit",
    "hello": "hello",
    "hallo": "hello",
    "shake hands": "hello",
    "pfote": "hello",
    "gib pfote": "hello",
    "stretch": "stretch",
    "strecken": "stretch",
    "heart": "heart",
    "herz": "heart",
    "love": "heart",
    "liebe": "heart",
    "greet": "greet",
    "grüßen": "greet",
    "begrüßen": "greet",
    "pose": "pose",
    "endurance": "endurance",
    "ausdauer": "endurance",
    "stand lock": "stand_lock",
    "stand": "stand_lock",
    "aufstehen": "stand_lock",
    "steh auf": "stand_lock",
    "stand up": "stand_lock",
    "hinlegen": "stand_lock",
    "low down": "stand_lock",
    "leg dich": "stand_lock",
    "recovery": "recovery_stand",
    "recovery stand": "recovery_stand",
    "jump": "front_jump",
    "spring": "front_jump",
    "springen": "front_jump",
    "jump forward": "front_jump",
    "pounce": "front_pounce",
    "dance": "dance1",
    "tanz": "dance1",
    "tanzen": "dance1",
    "dance 1": "dance1",
    "tanz 1": "dance1",
    "dance 2": "dance2",
    "tanz 2": "dance2",
    "damp": "damp",
    "damping": "damp",
    "notfall": "damp",
    "handstand": "handstand",
    "erect": "erect",
    "aufrichten": "erect",
    "cross step": "cross_step",
    "bound": "bound",
    "bound gait": "bound",
    "jump gait": "jump_gait",
    "free avoid": "free_avoid",
    "running": "running",
    "rennen": "running",
    "laufen": "running",
    "normal": "normal",
    "classic": "classic",
    "klassisch": "classic",
    "free walk": "free_walk",
    "unlock": "unlock_gait",
    "content": "content",
    "zufrieden": "content",
    "stop move": "stop_move",
}

ALL_COMMANDS = (
    set(STATIONARY_COMMANDS)
    | set(STATIONARY_CONTROLLER_COMMANDS)
    | set(MOVEMENT_CONTROLLER_COMMANDS)
    | set(DOUBLE_CLICK_COMMANDS)
)

DIRECTION_MAP = {
    "forward": (1, 0, 0),
    "vorwärts": (1, 0, 0),
    "vor": (1, 0, 0),
    "backward": (-1, 0, 0),
    "rückwärts": (-1, 0, 0),
    "zurück": (-1, 0, 0),
    "left": (0, 1, 0),
    "links": (0, 1, 0),
    "right": (0, -1, 0),
    "rechts": (0, -1, 0),
    "turn left": (0, 0, 1),
    "dreh links": (0, 0, 1),
    "links drehen": (0, 0, 1),
    "turn right": (0, 0, -1),
    "dreh rechts": (0, 0, -1),
    "rechts drehen": (0, 0, -1),
}


def _get_coordinator(hass: HomeAssistant):
    entries = hass.data.get(DOMAIN, {})
    if not entries:
        return None
    return next(iter(entries.values()))


async def async_setup_intents(hass: HomeAssistant) -> None:
    intent.async_register(hass, Go2CommandIntent())
    intent.async_register(hass, Go2EnableCommandsIntent())
    intent.async_register(hass, Go2DisableCommandsIntent())
    intent.async_register(hass, Go2EnableMovementIntent())
    intent.async_register(hass, Go2DisableMovementIntent())
    intent.async_register(hass, Go2StopIntent())
    intent.async_register(hass, Go2MoveIntent())
    intent.async_register(hass, Go2VisionLookIntent())
    intent.async_register(hass, Go2VisionDescribeIntent())
    intent.async_register(hass, Go2VisionWatchIntent())


class Go2CommandIntent(intent.IntentHandler):
    intent_type = INTENT_COMMAND
    description = "Execute a Go2 robot command"
    slot_schema = {"command": cv.string}

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        slots = self.async_validate_slots(intent_obj.slots)
        voice_cmd = slots["command"]["value"].strip().lower()

        # Check if it's a direction command first
        dir_coords = DIRECTION_MAP.get(voice_cmd)
        if not dir_coords:
            for key in DIRECTION_MAP:
                if key in voice_cmd:
                    dir_coords = DIRECTION_MAP[key]
                    break
        if dir_coords:
            coordinator = _get_coordinator(intent_obj.hass)
            if coordinator:
                await coordinator.async_move_direction(*dir_coords)
            response = intent_obj.create_response()
            response.async_set_speech("OK")
            return response

        command = VOICE_TO_COMMAND.get(voice_cmd)
        if not command:
            for key in VOICE_TO_COMMAND:
                if key in voice_cmd:
                    command = VOICE_TO_COMMAND[key]
                    break

        if not command or command not in ALL_COMMANDS:
            response = intent_obj.create_response()
            response.async_set_speech(
                f"Unbekannter Befehl: {voice_cmd}"
            )
            return response

        coordinator = _get_coordinator(intent_obj.hass)
        if not coordinator:
            response = intent_obj.create_response()
            response.async_set_speech("Go2 ist nicht konfiguriert.")
            return response

        try:
            await coordinator.async_sport_command(command)
        except Exception as exc:
            response = intent_obj.create_response()
            response.async_set_speech(str(exc))
            return response

        response = intent_obj.create_response()
        response.async_set_speech(f"OK")
        return response


class Go2EnableCommandsIntent(intent.IntentHandler):
    intent_type = INTENT_ENABLE_COMMANDS
    description = "Enable Go2 commands switch"

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        coordinator = _get_coordinator(intent_obj.hass)
        if coordinator and coordinator.stationary_switch:
            await coordinator.stationary_switch.async_turn_on()
        response = intent_obj.create_response()
        response.async_set_speech("Befehle aktiviert.")
        return response


class Go2DisableCommandsIntent(intent.IntentHandler):
    intent_type = INTENT_DISABLE_COMMANDS
    description = "Disable Go2 commands switch"

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        coordinator = _get_coordinator(intent_obj.hass)
        if coordinator and coordinator.stationary_switch:
            await coordinator.stationary_switch.async_turn_off()
        response = intent_obj.create_response()
        response.async_set_speech("Befehle deaktiviert.")
        return response


class Go2EnableMovementIntent(intent.IntentHandler):
    intent_type = INTENT_ENABLE_MOVEMENT
    description = "Enable Go2 movement switch"

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        coordinator = _get_coordinator(intent_obj.hass)
        if coordinator and coordinator.movement_switch:
            await coordinator.movement_switch.async_turn_on()
        response = intent_obj.create_response()
        response.async_set_speech("Bewegung aktiviert.")
        return response


class Go2DisableMovementIntent(intent.IntentHandler):
    intent_type = INTENT_DISABLE_MOVEMENT
    description = "Disable Go2 movement switch"

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        coordinator = _get_coordinator(intent_obj.hass)
        if coordinator and coordinator.movement_switch:
            await coordinator.movement_switch.async_turn_off()
        response = intent_obj.create_response()
        response.async_set_speech("Bewegung deaktiviert.")
        return response


class Go2StopIntent(intent.IntentHandler):
    intent_type = INTENT_STOP
    description = "Emergency stop the Go2 robot"

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        coordinator = _get_coordinator(intent_obj.hass)
        if coordinator:
            await coordinator.async_emergency_stop()
        response = intent_obj.create_response()
        response.async_set_speech("Gestoppt!")
        return response


class Go2MoveIntent(intent.IntentHandler):
    intent_type = INTENT_MOVE
    description = "Move the Go2 robot in a direction"
    slot_schema = {"direction": cv.string}

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        slots = self.async_validate_slots(intent_obj.slots)
        direction = slots["direction"]["value"].strip().lower()

        coords = DIRECTION_MAP.get(direction)
        if not coords:
            for key in DIRECTION_MAP:
                if key in direction:
                    coords = DIRECTION_MAP[key]
                    break

        if not coords:
            response = intent_obj.create_response()
            response.async_set_speech(f"Unbekannte Richtung: {direction}")
            return response

        coordinator = _get_coordinator(intent_obj.hass)
        if not coordinator:
            response = intent_obj.create_response()
            response.async_set_speech("Go2 ist nicht konfiguriert.")
            return response

        try:
            await coordinator.async_move_direction(*coords)
        except Exception as exc:
            response = intent_obj.create_response()
            response.async_set_speech(str(exc))
            return response

        response = intent_obj.create_response()
        response.async_set_speech("OK")
        return response


class Go2VisionLookIntent(intent.IntentHandler):
    intent_type = INTENT_VISION_LOOK
    description = "Detect objects the Go2 sees, fall back to Florence-2 if nothing found"

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        coordinator = _get_coordinator(intent_obj.hass)
        response = intent_obj.create_response()
        if not coordinator:
            response.async_set_speech("Go2 ist nicht konfiguriert.")
            return response
        if not coordinator.vision_url:
            response.async_set_speech("Vision Server ist nicht konfiguriert.")
            return response
        try:
            await coordinator.async_vision_detect()
            summary = coordinator.data.get("vision_detected_objects", "")
            if summary and summary != "none":
                speech = f"Ich sehe {summary}."
            else:
                await coordinator.async_vision_describe()
                description = coordinator.data.get("vision_last_description_full", "")
                if not description:
                    description = coordinator.data.get("vision_last_description", "")
                speech = description or "Ich kann gerade nichts erkennen."
            response.async_set_speech(speech)
            intent_obj.hass.async_create_task(coordinator.async_speak_text(speech))
        except Exception as exc:
            response.async_set_speech(f"Fehler: {exc}")
        return response


class Go2VisionDescribeIntent(intent.IntentHandler):
    intent_type = INTENT_VISION_DESCRIBE
    description = "Get a detailed Florence-2 description of what the Go2 sees"

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        coordinator = _get_coordinator(intent_obj.hass)
        response = intent_obj.create_response()
        if not coordinator:
            response.async_set_speech("Go2 ist nicht konfiguriert.")
            return response
        if not coordinator.vision_url:
            response.async_set_speech("Vision Server ist nicht konfiguriert.")
            return response
        try:
            await coordinator.async_vision_describe()
            description = coordinator.data.get("vision_last_description_full", "")
            if not description:
                description = coordinator.data.get("vision_last_description", "Keine Beschreibung verfügbar.")
            response.async_set_speech(description)
            intent_obj.hass.async_create_task(coordinator.async_speak_text(description))
        except Exception as exc:
            response.async_set_speech(f"Fehler: {exc}")
        return response


class Go2VisionWatchIntent(intent.IntentHandler):
    intent_type = INTENT_VISION_WATCH
    description = "Toggle the Go2 vision watch mode"
    slot_schema = {"action": cv.string}

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        slots = self.async_validate_slots(intent_obj.slots)
        action = slots["action"]["value"].strip().lower()
        coordinator = _get_coordinator(intent_obj.hass)
        response = intent_obj.create_response()
        if not coordinator:
            response.async_set_speech("Go2 ist nicht konfiguriert.")
            return response

        enable = action in ("an", "ein", "on", "start", "aktivieren", "einschalten")
        try:
            if enable:
                await coordinator.async_vision_watch_start()
                response.async_set_speech("Wachmodus aktiviert.")
            else:
                await coordinator.async_vision_watch_stop()
                response.async_set_speech("Wachmodus deaktiviert.")
        except Exception as exc:
            response.async_set_speech(f"Fehler: {exc}")
        return response
