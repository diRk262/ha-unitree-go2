"""DataUpdateCoordinator for Unitree Go2."""
import asyncio
import io
import json
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .lib.unitree_webrtc_connect.webrtc_driver import (
    UnitreeWebRTCConnection,
    WebRTCConnectionMethod,
)
from .lib.unitree_webrtc_connect.constants import RTC_TOPIC, OBSTACLES_AVOID_API

from .const import DOMAIN, SCAN_INTERVAL_SECONDS, ERROR_CODES

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 5


class Go2DataCoordinator(DataUpdateCoordinator):
    """Manages the WebRTC connection and collects sensor data."""

    def __init__(
        self,
        hass: HomeAssistant,
        robot_ip: str,
        aes_key: str,
        serial: str = "",
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.robot_ip = robot_ip
        self.serial = serial
        self._aes_key = aes_key
        self._conn: UnitreeWebRTCConnection | None = None
        self._connected = False
        self._sensor_data: dict = self._empty_data()
        self._last_frame: bytes | None = None
        self._frame_event = asyncio.Event()

    @staticmethod
    def _empty_data() -> dict:
        return {
            "battery_percent": 0,
            "battery_voltage": 0.0,
            "battery_current": 0.0,
            "battery_cycles": 0,
            "battery_temp_1": 0,
            "battery_temp_2": 0,
            "mcu_temp_1": 0,
            "mcu_temp_2": 0,
            "body_temp": 0,
            "power_v": 0.0,
            "foot_force": [0, 0, 0, 0],
            "motor_temp_max": 0,
            "motor_temp_min": 0,
            "position_x": 0.0,
            "position_y": 0.0,
            "position_z": 0.0,
            "body_height": 0.0,
            "velocity_x": 0.0,
            "velocity_y": 0.0,
            "yaw_speed": 0.0,
            "mode": "unknown",
            "error_code": 0,
            "gait_type": 0,
            "lidar_dirty": 0,
            "lidar_error": 0,
            "lidar_cloud_freq": 0.0,
            "imu_roll": 0.0,
            "imu_pitch": 0.0,
            "imu_yaw": 0.0,
            "brightness": 0,
            "volume": 0,
            "obstacle_avoidance": "unknown",
            "led_color": "unknown",
            "online": False,
        }

    # ── Connection ────────────────────────────────────────────────────

    async def async_connect(self) -> None:
        """Establish WebRTC connection to the robot."""
        self._conn = UnitreeWebRTCConnection(
            WebRTCConnectionMethod.LocalSTA,
            ip=self.robot_ip,
            aes_128_key=self._aes_key,
        )
        await asyncio.wait_for(self._conn.connect(), timeout=30)
        self._connected = True
        self._sensor_data["online"] = True

        self._conn.datachannel.pub_sub.subscribe(
            RTC_TOPIC["LOW_STATE"], self._on_low_state
        )
        self._conn.datachannel.pub_sub.subscribe(
            RTC_TOPIC["LF_SPORT_MOD_STATE"], self._on_sport_state
        )
        self._conn.datachannel.pub_sub.subscribe(
            RTC_TOPIC["ULIDAR_STATE"], self._on_lidar_state
        )

        self._conn.video.switchVideoChannel(True)
        self._conn.video.add_track_callback(self._recv_video)

        _LOGGER.info("Go2 connected at %s", self.robot_ip)

    async def async_disconnect(self) -> None:
        if self._conn and self._connected:
            try:
                self._conn.datachannel.pub_sub.unsubscribe(RTC_TOPIC["LOW_STATE"])
                self._conn.datachannel.pub_sub.unsubscribe(
                    RTC_TOPIC["LF_SPORT_MOD_STATE"]
                )
                self._conn.datachannel.pub_sub.unsubscribe(RTC_TOPIC["ULIDAR_STATE"])
            except Exception:
                pass
            self._connected = False
            self._sensor_data["online"] = False

    # ── Video (receive only) ──────────────────────────────────────────

    async def _recv_video(self, track) -> None:
        try:
            import av
        except ImportError:
            _LOGGER.warning("PyAV not available — camera entity disabled")
            return

        while True:
            try:
                frame = await track.recv()
                img = frame.to_ndarray(format="bgr24")
                out = av.open(io.BytesIO(), mode="w", format="mjpeg")
                stream = out.add_stream("mjpeg", rate=1)
                stream.width = img.shape[1]
                stream.height = img.shape[0]
                stream.pix_fmt = "yuvj420p"
                av_frame = av.VideoFrame.from_ndarray(img, format="bgr24")
                for packet in stream.encode(av_frame):
                    self._last_frame = bytes(packet)
                out.close()
                self._frame_event.set()
            except Exception:
                break

    @property
    def last_frame(self) -> bytes | None:
        return self._last_frame

    # ── Data callbacks (READ ONLY) ────────────────────────────────────

    def _on_low_state(self, msg: dict) -> None:
        try:
            data = msg.get("data", {})
            if isinstance(data, str):
                data = json.loads(data)

            bms = data.get("bms_state", {})
            if bms:
                self._sensor_data["battery_percent"] = bms.get("soc", 0)
                self._sensor_data["battery_current"] = round(
                    bms.get("current", 0) / 1000, 2
                )
                self._sensor_data["battery_cycles"] = bms.get("cycle", 0)
                ntc = bms.get("bq_ntc", [0, 0])
                self._sensor_data["battery_temp_1"] = ntc[0] if ntc else 0
                self._sensor_data["battery_temp_2"] = ntc[1] if len(ntc) > 1 else 0
                mcu = bms.get("mcu_ntc", [0, 0])
                self._sensor_data["mcu_temp_1"] = mcu[0] if mcu else 0
                self._sensor_data["mcu_temp_2"] = mcu[1] if len(mcu) > 1 else 0

            self._sensor_data["power_v"] = round(data.get("power_v", 0), 2)
            self._sensor_data["body_temp"] = data.get("temperature_ntc1", 0)
            self._sensor_data["foot_force"] = data.get("foot_force", [0, 0, 0, 0])

            motors = data.get("motor_state", [])
            if motors:
                temps = [
                    m.get("temperature", 0) for m in motors if isinstance(m, dict)
                ]
                if temps:
                    self._sensor_data["motor_temp_max"] = max(temps)
                    self._sensor_data["motor_temp_min"] = min(temps)

            imu = data.get("imu_state", {})
            if isinstance(imu, dict):
                rpy = imu.get("rpy", [0, 0, 0])
                if len(rpy) >= 3:
                    self._sensor_data["imu_roll"] = round(rpy[0], 2)
                    self._sensor_data["imu_pitch"] = round(rpy[1], 2)
                    self._sensor_data["imu_yaw"] = round(rpy[2], 2)
        except Exception as exc:
            _LOGGER.debug("LOW_STATE parse error: %s", exc)

    def _on_sport_state(self, msg: dict) -> None:
        try:
            data = msg.get("data", {})
            if isinstance(data, str):
                data = json.loads(data)

            pos = data.get("position", [0, 0, 0])
            self._sensor_data["position_x"] = round(pos[0], 3) if pos else 0
            self._sensor_data["position_y"] = (
                round(pos[1], 3) if len(pos) > 1 else 0
            )
            self._sensor_data["position_z"] = (
                round(pos[2], 3) if len(pos) > 2 else 0
            )

            self._sensor_data["body_height"] = round(
                data.get("body_height", 0), 3
            )
            self._sensor_data["yaw_speed"] = round(data.get("yaw_speed", 0), 3)
            self._sensor_data["gait_type"] = data.get("gait_type", 0)

            vel = data.get("velocity", [0, 0, 0])
            self._sensor_data["velocity_x"] = round(vel[0], 3) if vel else 0
            self._sensor_data["velocity_y"] = (
                round(vel[1], 3) if len(vel) > 1 else 0
            )

            ec = data.get("error_code", 0)
            self._sensor_data["error_code"] = ec
            self._sensor_data["mode"] = ERROR_CODES.get(ec, f"unknown_{ec}")
        except Exception as exc:
            _LOGGER.debug("SPORT_STATE parse error: %s", exc)

    def _on_lidar_state(self, msg: dict) -> None:
        try:
            data = msg.get("data", {})
            if isinstance(data, str):
                data = json.loads(data)

            self._sensor_data["lidar_dirty"] = data.get("dirty_percentage", 0)
            self._sensor_data["lidar_error"] = data.get("error_state", 0)
            self._sensor_data["lidar_cloud_freq"] = round(
                data.get("cloud_frequency", 0), 1
            )
        except Exception as exc:
            _LOGGER.debug("LIDAR_STATE parse error: %s", exc)

    # ── Polled values ─────────────────────────────────────────────────

    async def _safe_request(self, topic, options):
        try:
            return await asyncio.wait_for(
                self._conn.datachannel.pub_sub.publish_request_new(topic, options),
                timeout=REQUEST_TIMEOUT,
            )
        except (asyncio.TimeoutError, Exception) as exc:
            _LOGGER.debug("Request timeout/error for %s: %s", topic, exc)
            return None

    async def _poll_vui_and_obstacles(self) -> None:
        if not self._conn or not self._connected:
            return

        resp = await self._safe_request(RTC_TOPIC["VUI"], {"api_id": 1006})
        if resp and resp.get("data", {}).get("header", {}).get("status", {}).get("code") == 0:
            try:
                d = json.loads(resp["data"].get("data", "{}"))
                self._sensor_data["brightness"] = d.get("brightness", 0)
            except Exception:
                pass

        resp = await self._safe_request(RTC_TOPIC["VUI"], {"api_id": 1004})
        if resp and resp.get("data", {}).get("header", {}).get("status", {}).get("code") == 0:
            try:
                d = json.loads(resp["data"].get("data", "{}"))
                self._sensor_data["volume"] = d.get("volume", 0)
            except Exception:
                pass

        resp = await self._safe_request(
            RTC_TOPIC["OBSTACLES_AVOID"],
            {"api_id": OBSTACLES_AVOID_API["SWITCH_GET"]},
        )
        if resp:
            code = resp.get("data", {}).get("header", {}).get("status", {}).get("code", -1)
            raw = resp.get("data", {}).get("data", "")
            if code == 0 and raw:
                try:
                    d = json.loads(raw)
                    self._sensor_data["obstacle_avoidance"] = (
                        "on" if d.get("enable") else "off"
                    )
                except Exception:
                    pass

        resp = await self._safe_request(RTC_TOPIC["VUI"], {"api_id": 1009})
        if resp and resp.get("data", {}).get("header", {}).get("status", {}).get("code") == 0:
            try:
                d = json.loads(resp["data"].get("data", "{}"))
                color = d.get("color", "")
                self._sensor_data["led_color"] = color if color else "off"
            except Exception:
                pass

    # ── Commands ──────────────────────────────────────────────────────

    async def async_set_volume(self, volume: int) -> None:
        if not self._conn or not self._connected:
            return
        await self._safe_request(
            RTC_TOPIC["VUI"],
            {"api_id": 1003, "parameter": {"volume": volume}},
        )
        self._sensor_data["volume"] = volume
        self.async_set_updated_data(dict(self._sensor_data))

    async def async_set_brightness(self, brightness: int) -> None:
        if not self._conn or not self._connected:
            return
        await self._safe_request(
            RTC_TOPIC["VUI"],
            {"api_id": 1005, "parameter": {"brightness": brightness}},
        )
        self._sensor_data["brightness"] = brightness
        self.async_set_updated_data(dict(self._sensor_data))

    async def async_set_obstacle_avoidance(self, enable: bool) -> None:
        if not self._conn or not self._connected:
            return
        await self._safe_request(
            RTC_TOPIC["OBSTACLES_AVOID"],
            {"api_id": OBSTACLES_AVOID_API["SWITCH_SET"], "parameter": {"enable": enable}},
        )
        self._sensor_data["obstacle_avoidance"] = "on" if enable else "off"
        self.async_set_updated_data(dict(self._sensor_data))

    async def async_set_lidar(self, enable: bool) -> None:
        if not self._conn or not self._connected:
            return
        self._conn.datachannel.pub_sub.publish_without_callback(
            RTC_TOPIC["ULIDAR_SWITCH"],
            "ON" if enable else "OFF",
        )
        self._sensor_data["lidar_active"] = enable
        self.async_set_updated_data(dict(self._sensor_data))

    # ── Coordinator update ────────────────────────────────────────────

    async def _async_update_data(self) -> dict:
        if not self._connected:
            try:
                await self.async_connect()
            except Exception as exc:
                raise UpdateFailed(f"Connection failed: {exc}") from exc

        await self._poll_vui_and_obstacles()
        return dict(self._sensor_data)
