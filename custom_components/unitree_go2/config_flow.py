"""Config flow for Unitree Go2.

Step 1: User enters Unitree account email + password
Step 2: Devices are fetched from cloud — user picks one (or enters IP manually)
Step 3: Robot IP — auto-discovered via multicast or entered manually
"""
import asyncio
import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_ROBOT_IP,
    CONF_AES_KEY,
    CONF_SERIAL,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_ROBOT_NAME,
    DEFAULT_ROBOT_NAME,
)

_LOGGER = logging.getLogger(__name__)


class UnitreeGo2OptionsFlow(config_entries.OptionsFlow):
    """Handle options for Unitree Go2."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_name = self._config_entry.options.get(
            CONF_ROBOT_NAME, DEFAULT_ROBOT_NAME
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {vol.Optional(CONF_ROBOT_NAME, default=current_name): str}
            ),
        )


class UnitreeGo2ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Unitree Go2."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> UnitreeGo2OptionsFlow:
        return UnitreeGo2OptionsFlow(config_entry)

    def __init__(self) -> None:
        self._devices: list = []
        self._selected_sn: str = ""
        self._selected_key: str = ""
        self._email: str = ""
        self._discovered_ips: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Step 1: Unitree account login."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]

            try:
                from .lib.unitree_webrtc_connect.unitree_cloud import UnitreeCloud

                cloud = UnitreeCloud(region="global", device_type="Go2")
                await self.hass.async_add_executor_job(
                    cloud.login_email, self._email, password
                )
                self._devices = await self.hass.async_add_executor_job(
                    cloud.list_devices
                )

                if not self._devices:
                    errors["base"] = "no_devices"
                else:
                    return await self.async_step_select_device()

            except Exception:
                _LOGGER.exception("Unitree cloud login failed")
                errors["base"] = "auth_failed"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_select_device(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Step 2: Pick a robot from the account."""
        if user_input is not None:
            sn = user_input["device"]
            for dev in self._devices:
                if dev.sn == sn:
                    self._selected_sn = dev.sn
                    self._selected_key = dev.key
                    break

            await self.async_set_unique_id(self._selected_sn)
            self._abort_if_unique_id_configured()

            # Try to discover the robot's IP via multicast
            try:
                from .lib.unitree_webrtc_connect.multicast_scanner import discover_ip_sn

                self._discovered_ips = await self.hass.async_add_executor_job(
                    discover_ip_sn, 3
                )
            except Exception:
                self._discovered_ips = {}

            if self._selected_sn in self._discovered_ips:
                # Auto-discovered — go straight to connection test
                robot_ip = self._discovered_ips[self._selected_sn]
                return await self._test_and_create(robot_ip)

            return await self.async_step_enter_ip()

        device_options = {
            dev.sn: f"{dev.alias or dev.sn} ({dev.model or 'Go2'})"
            for dev in self._devices
        }

        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema(
                {vol.Required("device"): vol.In(device_options)}
            ),
        )

    async def async_step_enter_ip(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Step 3: Enter robot IP manually (auto-discovery failed)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            robot_ip = user_input[CONF_ROBOT_IP]
            try:
                from .lib.unitree_webrtc_connect.webrtc_driver import (
                    UnitreeWebRTCConnection,
                    WebRTCConnectionMethod,
                )

                conn = UnitreeWebRTCConnection(
                    WebRTCConnectionMethod.LocalSTA,
                    ip=robot_ip,
                    aes_128_key=self._selected_key,
                )
                await asyncio.wait_for(conn.connect(), timeout=15)
            except Exception:
                _LOGGER.exception("Connection test failed for %s", robot_ip)
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"Go2 ({self._selected_sn})",
                    data={
                        CONF_ROBOT_IP: robot_ip,
                        CONF_AES_KEY: self._selected_key,
                        CONF_SERIAL: self._selected_sn,
                    },
                )

        return self.async_show_form(
            step_id="enter_ip",
            data_schema=vol.Schema(
                {vol.Required(CONF_ROBOT_IP): str}
            ),
            errors=errors,
            description_placeholders={
                "serial": self._selected_sn,
            },
        )
