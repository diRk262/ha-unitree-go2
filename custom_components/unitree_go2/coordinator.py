"""DataUpdateCoordinator for Unitree Go2."""
import asyncio
import io
import json
import logging
import math
from datetime import timedelta

import numpy as np

try:
    from PIL import Image
    _HAS_PILLOW = True
except ImportError:
    _HAS_PILLOW = False

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .lib.unitree_webrtc_connect.webrtc_driver import (
    UnitreeWebRTCConnection,
    WebRTCConnectionMethod,
)
from homeassistant.exceptions import HomeAssistantError

from .lib.unitree_webrtc_connect.constants import RTC_TOPIC, OBSTACLES_AVOID_API

from .const import (
    DOMAIN, SCAN_INTERVAL_SECONDS, MODE_CODES,
    STATIONARY_COMMANDS, STATIONARY_CONTROLLER_COMMANDS,
    MOVEMENT_CONTROLLER_COMMANDS, DOUBLE_CLICK_COMMANDS, BUTTON_START,
    TRICK_COMMANDS,
)

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 5
LIDAR_IMG_SIZE = 800
LIDAR_SCALE = 50
LIDAR_POINT_SIZE = 2
LIDAR_ACCUMULATE_FRAMES = 5


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
        self._last_lidar_frame: bytes | None = None
        self._lidar_points: np.ndarray | None = None
        self._lidar_history: list[np.ndarray] = []
        self.stationary_switch = None
        self.movement_switch = None
        self.command_select = None
        self.move_speed = None
        self.move_duration = None
        self._move_api_enabled = False
        self._last_was_trick = False
        self._last_was_stand_lock = False
        self._slam_status = "idle"
        self._slam_map_image: bytes | None = None
        self._slam_combined: np.ndarray | None = None
        self._slam_frame_count = 0
        self._slam_robot_x = 0.0
        self._slam_robot_y = 0.0
        self._slam_robot_yaw = 0.0
        self._slam_nav_status = ""
        self._slam_log_lines: list[str] = []

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
            "lidar_dirty": 0,
            "lidar_error": 0,
            "lidar_cloud_freq": 0.0,
            "imu_roll": 0.0,
            "imu_pitch": 0.0,
            "imu_yaw": 0.0,
            "brightness": 0,
            "volume": 0,
            "obstacle_avoidance": "unknown",
            "online": False,
            "slam_status": "idle",
            "slam_nav_status": "",
            "slam_x": 0.0,
            "slam_y": 0.0,
            "slam_yaw": 0.0,
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

        self._conn.datachannel.set_decoder(decoder_type="native")

        self._conn.datachannel.pub_sub.subscribe(
            RTC_TOPIC["LOW_STATE"], self._on_low_state
        )
        self._conn.datachannel.pub_sub.subscribe(
            RTC_TOPIC["LF_SPORT_MOD_STATE"], self._on_sport_state
        )
        self._conn.datachannel.pub_sub.subscribe(
            RTC_TOPIC["ULIDAR_STATE"], self._on_lidar_state
        )
        self._conn.datachannel.pub_sub.subscribe(
            RTC_TOPIC["ULIDAR_ARRAY"], self._on_lidar_voxel
        )
        self._conn.datachannel.pub_sub.subscribe(
            RTC_TOPIC["LIDAR_MAPPING_SERVER_LOG"], self._on_slam_log
        )
        self._conn.datachannel.pub_sub.subscribe(
            RTC_TOPIC["LIDAR_MAPPING_ODOM"], self._on_slam_odom
        )
        self._conn.datachannel.pub_sub.subscribe(
            RTC_TOPIC["LIDAR_LOCALIZATION_ODOM"], self._on_slam_odom
        )
        self._conn.datachannel.pub_sub.subscribe(
            RTC_TOPIC["LIDAR_MAPPING_CLOUD_POINT"], self._on_slam_cloud
        )
        # Localization cloud has different format — skip for now

        await self._conn.datachannel.disableTrafficSaving(True)

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
                self._conn.datachannel.pub_sub.unsubscribe(RTC_TOPIC["ULIDAR_ARRAY"])
                self._conn.datachannel.pub_sub.unsubscribe(RTC_TOPIC["LIDAR_MAPPING_SERVER_LOG"])
                self._conn.datachannel.pub_sub.unsubscribe(RTC_TOPIC["LIDAR_MAPPING_ODOM"])
                self._conn.datachannel.pub_sub.unsubscribe(RTC_TOPIC["LIDAR_LOCALIZATION_ODOM"])
                self._conn.datachannel.pub_sub.unsubscribe(RTC_TOPIC["LIDAR_MAPPING_CLOUD_POINT"])
                self._conn.datachannel.pub_sub.unsubscribe(RTC_TOPIC["LIDAR_LOCALIZATION_CLOUD_POINT"])
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

    # ── LiDAR point cloud ────────────────────────────────────────────

    def _on_lidar_voxel(self, msg: dict) -> None:
        try:
            data = msg.get("data", {})
            decoded = data.get("data", {})
            points = decoded.get("points") if isinstance(decoded, dict) else None
            if points is None or not isinstance(points, np.ndarray):
                return
            if len(points) == 0:
                return
            self._lidar_points = points
            self._lidar_history.append(points)
            if len(self._lidar_history) > LIDAR_ACCUMULATE_FRAMES:
                self._lidar_history = self._lidar_history[-LIDAR_ACCUMULATE_FRAMES:]
            combined = np.vstack(self._lidar_history)
            self._render_lidar_topdown(combined)
        except Exception as exc:
            _LOGGER.debug("LIDAR voxel parse error: %s", exc)

    def _render_lidar_topdown(self, points: np.ndarray) -> None:
        """Render point cloud as top-down 2D image (X/Y plane)."""
        if not _HAS_PILLOW:
            return
        try:
            x = points[:, 0]
            y = points[:, 1]
            z = points[:, 2]

            cx = LIDAR_IMG_SIZE // 2
            cy = LIDAR_IMG_SIZE // 2

            robot_x = self._sensor_data.get("position_x", 0.0)
            robot_y = self._sensor_data.get("position_y", 0.0)

            px = ((x - robot_x) * LIDAR_SCALE + cx).astype(np.int32)
            py = (cy - (y - robot_y) * LIDAR_SCALE).astype(np.int32)

            ps = LIDAR_POINT_SIZE
            mask = (px >= 0) & (px < LIDAR_IMG_SIZE - ps) & (py >= 0) & (py < LIDAR_IMG_SIZE - ps)
            px = px[mask]
            py = py[mask]
            z_masked = z[mask]

            img = np.zeros((LIDAR_IMG_SIZE, LIDAR_IMG_SIZE, 3), dtype=np.uint8)
            img[:] = 15

            if len(px) > 0:
                z_min = z_masked.min()
                z_range = z_masked.max() - z_min
                if z_range < 0.01:
                    z_range = 1.0
                z_norm = (z_masked - z_min) / z_range

                r = (z_norm * 255).astype(np.uint8)
                g = ((1 - np.abs(z_norm - 0.5) * 2) * 200).astype(np.uint8)
                b = ((1 - z_norm) * 255).astype(np.uint8)

                for dy in range(ps):
                    for dx in range(ps):
                        img[py + dy, px + dx, 0] = r
                        img[py + dy, px + dx, 1] = g
                        img[py + dy, px + dx, 2] = b

            # Robot marker (green dot)
            ms = 4
            img[cy - ms:cy + ms + 1, cx - ms:cx + ms + 1] = [0, 220, 0]

            # Direction indicator (yaw)
            yaw = self._sensor_data.get("imu_yaw", 0.0)
            arrow_len = 15
            ax = int(cx + np.cos(yaw) * arrow_len)
            ay = int(cy - np.sin(yaw) * arrow_len)
            steps = max(abs(ax - cx), abs(ay - cy), 1)
            for i in range(steps):
                ix = int(cx + (ax - cx) * i / steps)
                iy = int(cy + (ay - cy) * i / steps)
                if 0 <= ix < LIDAR_IMG_SIZE - 1 and 0 <= iy < LIDAR_IMG_SIZE - 1:
                    img[iy:iy + 2, ix:ix + 2] = [0, 255, 100]

            pil_img = Image.fromarray(img)
            buf = io.BytesIO()
            pil_img.save(buf, format="PNG")
            self._last_lidar_frame = buf.getvalue()
        except Exception as exc:
            _LOGGER.debug("LiDAR render error: %s", exc)

    @property
    def last_lidar_frame(self) -> bytes | None:
        return self._last_lidar_frame

    # ── Data callbacks (READ ONLY) ────────────────────────────────────

    def _on_low_state(self, msg: dict) -> None:
        try:
            data = msg.get("data", {})
            if isinstance(data, str):
                data = json.loads(data)

            bms = data.get("bms_state", {})
            if bms:
                self._sensor_data["battery_percent"] = bms.get("soc", 0)
                self._sensor_data["battery_voltage"] = round(
                    bms.get("vol", 0) / 1000, 2
                )
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

            vel = data.get("velocity", [0, 0, 0])
            self._sensor_data["velocity_x"] = round(vel[0], 3) if vel else 0
            self._sensor_data["velocity_y"] = (
                round(vel[1], 3) if len(vel) > 1 else 0
            )

            ec = data.get("error_code", 0)
            self._sensor_data["error_code"] = ec
            self._sensor_data["mode"] = MODE_CODES.get(ec, f"unknown_{ec}")
        except Exception as exc:
            _LOGGER.debug("SPORT_STATE parse error: %s", exc)

    def _on_lidar_state(self, msg: dict) -> None:
        try:
            data = msg.get("data", {})
            if isinstance(data, str):
                data = json.loads(data)

            self._sensor_data["lidar_dirty"] = data.get("dirty_percentage", 0)
            self._sensor_data["lidar_error"] = data.get("error_state", 0)
            freq = round(data.get("cloud_frequency", 0), 1)
            self._sensor_data["lidar_cloud_freq"] = freq
            self._sensor_data["lidar_active"] = freq > 0
        except Exception as exc:
            _LOGGER.debug("LIDAR_STATE parse error: %s", exc)

    # ── Polled values ─────────────────────────────────────────────────

    def _check_connection(self) -> bool:
        if not self._conn or not self._connected:
            return False
        try:
            dc = self._conn.datachannel
            if dc and dc.channel and dc.channel.readyState == "open":
                return True
        except Exception:
            pass
        _LOGGER.info("WebRTC connection lost, will reconnect")
        self._connected = False
        self._sensor_data["online"] = False
        return False

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

        responses = []

        resp = await self._safe_request(RTC_TOPIC["VUI"], {"api_id": 1006})
        responses.append(resp)
        if resp and resp.get("data", {}).get("header", {}).get("status", {}).get("code") == 0:
            try:
                d = json.loads(resp["data"].get("data", "{}"))
                self._sensor_data["brightness"] = d.get("brightness", 0)
            except Exception:
                pass

        resp = await self._safe_request(RTC_TOPIC["VUI"], {"api_id": 1004})
        responses.append(resp)
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
        responses.append(resp)
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

        if all(r is None for r in responses):
            _LOGGER.info("All poll requests failed, marking connection as lost")
            self._connected = False
            self._sensor_data["online"] = False

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

    # ── Movement commands ──────────────────────────────────────────────

    def _check_stationary_allowed(self) -> None:
        stationary_on = self.stationary_switch and self.stationary_switch.is_on
        movement_on = self.movement_switch and self.movement_switch.is_on
        if not stationary_on and not movement_on:
            raise HomeAssistantError(
                "Commands switch is OFF. Enable it first."
            )

    def _check_movement_allowed(self) -> None:
        if not self.movement_switch or not self.movement_switch.is_on:
            raise HomeAssistantError(
                "Movement switch is OFF. Enable it first."
            )

    async def async_led_flash(self) -> None:
        if not self._conn or not self._connected:
            return
        current = self._sensor_data.get("brightness", 0)
        await self._safe_request(
            RTC_TOPIC["VUI"],
            {"api_id": 1005, "parameter": {"brightness": 10}},
        )
        await asyncio.sleep(0.3)
        await self._safe_request(
            RTC_TOPIC["VUI"],
            {"api_id": 1005, "parameter": {"brightness": current}},
        )

    async def async_auto_stand_if_needed(self) -> None:
        if self._last_was_trick:
            _LOGGER.info("Auto-stand: sending stand_lock (L2+A) before next command")
            await self.async_send_button(STATIONARY_CONTROLLER_COMMANDS["stand_lock"])
            await asyncio.sleep(2.0)
            self._last_was_trick = False
            self._last_was_stand_lock = True
        elif self._last_was_stand_lock:
            _LOGGER.info("Auto-normal: sending normal mode (L1+Start) after stand_lock")
            await self.async_send_button(MOVEMENT_CONTROLLER_COMMANDS["normal"])
            await asyncio.sleep(1.0)
            self._last_was_stand_lock = False

    async def async_sport_command(self, command: str, parameter: dict | None = None) -> None:
        if not self._conn or not self._connected:
            raise HomeAssistantError("Robot is not connected")

        if command != "stand_lock":
            await self.async_auto_stand_if_needed()

        if command in STATIONARY_COMMANDS:
            self._check_stationary_allowed()
            api_id = STATIONARY_COMMANDS[command]
            options = {"api_id": api_id}
            if parameter:
                options["parameter"] = parameter
            _LOGGER.info("Sending sport command: %s (api_id=%d)", command, api_id)
            await self._safe_request(RTC_TOPIC["SPORT_MOD"], options)
            if self.stationary_switch:
                self.stationary_switch.reset_timeout()

        elif command in STATIONARY_CONTROLLER_COMMANDS:
            self._check_stationary_allowed()
            keys = STATIONARY_CONTROLLER_COMMANDS[command]
            _LOGGER.info("Sending controller command: %s (keys=%d)", command, keys)
            await self.async_send_button(keys)
            if self.stationary_switch:
                self.stationary_switch.reset_timeout()

        elif command in MOVEMENT_CONTROLLER_COMMANDS:
            self._check_movement_allowed()
            keys = MOVEMENT_CONTROLLER_COMMANDS[command]
            _LOGGER.info("Sending controller command: %s (keys=%d)", command, keys)
            await self.async_send_button(keys)
            if self.movement_switch:
                self.movement_switch.reset_timeout()

        elif command in DOUBLE_CLICK_COMMANDS:
            self._check_movement_allowed()
            keys = DOUBLE_CLICK_COMMANDS[command]
            _LOGGER.info("Sending double-click command: %s (keys=%d)", command, keys)
            await self.async_send_double_click(keys)
            if self.movement_switch:
                self.movement_switch.reset_timeout()

        else:
            raise HomeAssistantError(f"Unknown command: {command}")

        self._last_was_trick = command in TRICK_COMMANDS
        if command == "stand_lock":
            self._last_was_stand_lock = True

    async def async_move(self, x: float, y: float, yaw: float) -> None:
        if not self._conn or not self._connected:
            raise HomeAssistantError("Robot is not connected")
        self._check_movement_allowed()

        x = max(-1.0, min(1.0, x))
        y = max(-1.0, min(1.0, y))
        yaw = max(-1.0, min(1.0, yaw))

        if not self._move_api_enabled:
            await self._safe_request(
                RTC_TOPIC["OBSTACLES_AVOID"],
                {"api_id": OBSTACLES_AVOID_API["USE_REMOTE_COMMAND_FROM_API"],
                 "parameter": {"is_remote_commands_from_api": True}},
            )
            self._move_api_enabled = True

        await self._safe_request(
            RTC_TOPIC["OBSTACLES_AVOID"],
            {"api_id": OBSTACLES_AVOID_API["MOVE"],
             "parameter": {"x": x, "y": y, "yaw": yaw, "mode": 0}},
        )

        if self.movement_switch:
            self.movement_switch.reset_timeout()

    async def async_move_direction(self, x: float, y: float, yaw: float) -> None:
        await self.async_auto_stand_if_needed()
        speed = 0.3
        if self.move_speed is not None:
            speed = self.move_speed.native_value
        duration = 0.5
        if self.move_duration is not None:
            duration = self.move_duration.native_value
        await self.async_move(x=x * speed, y=y * speed, yaw=yaw * speed)
        await asyncio.sleep(duration)
        await self.async_move(x=0, y=0, yaw=0)

    async def async_emergency_stop(self) -> None:
        _LOGGER.warning("EMERGENCY STOP triggered")
        if self._conn and self._connected:
            if self._move_api_enabled:
                await self._safe_request(
                    RTC_TOPIC["OBSTACLES_AVOID"],
                    {"api_id": OBSTACLES_AVOID_API["MOVE"],
                     "parameter": {"x": 0, "y": 0, "yaw": 0, "mode": 0}},
                )
                self._move_api_enabled = False

            wc_data = {"lx": 0.0, "ly": 0.0, "rx": 0.0, "ry": 0.0, "keys": BUTTON_START}
            self._conn.datachannel.pub_sub.publish_without_callback(
                RTC_TOPIC["WIRELESS_CONTROLLER"], wc_data,
            )
            await asyncio.sleep(0.4)
            wc_data["keys"] = 0
            self._conn.datachannel.pub_sub.publish_without_callback(
                RTC_TOPIC["WIRELESS_CONTROLLER"], wc_data,
            )
        if self.movement_switch:
            await self.movement_switch.async_turn_off()
        if self.stationary_switch:
            await self.stationary_switch.async_turn_off()

    async def async_send_button(self, keys: int) -> None:
        if not self._conn or not self._connected:
            raise HomeAssistantError("Robot is not connected")
        _LOGGER.info("Sending wireless controller keys=%d", keys)
        wc_data = {"lx": 0.0, "ly": 0.0, "rx": 0.0, "ry": 0.0, "keys": keys}
        self._conn.datachannel.pub_sub.publish_without_callback(
            RTC_TOPIC["WIRELESS_CONTROLLER"], wc_data,
        )
        await asyncio.sleep(0.4)
        wc_data["keys"] = 0
        self._conn.datachannel.pub_sub.publish_without_callback(
            RTC_TOPIC["WIRELESS_CONTROLLER"], wc_data,
        )

    async def async_send_double_click(self, keys: int) -> None:
        if not self._conn or not self._connected:
            raise HomeAssistantError("Robot is not connected")
        _LOGGER.info("Sending double-click keys=%d", keys)
        wc_zero = {"lx": 0.0, "ly": 0.0, "rx": 0.0, "ry": 0.0, "keys": 0}
        wc_press = {"lx": 0.0, "ly": 0.0, "rx": 0.0, "ry": 0.0, "keys": keys}
        self._conn.datachannel.pub_sub.publish_without_callback(
            RTC_TOPIC["WIRELESS_CONTROLLER"], wc_press,
        )
        await asyncio.sleep(0.1)
        self._conn.datachannel.pub_sub.publish_without_callback(
            RTC_TOPIC["WIRELESS_CONTROLLER"], wc_zero,
        )
        await asyncio.sleep(0.15)
        self._conn.datachannel.pub_sub.publish_without_callback(
            RTC_TOPIC["WIRELESS_CONTROLLER"], wc_press,
        )
        await asyncio.sleep(0.1)
        self._conn.datachannel.pub_sub.publish_without_callback(
            RTC_TOPIC["WIRELESS_CONTROLLER"], wc_zero,
        )

    # ── SLAM / Mapping ───────────────────────────────────────────────

    def _slam_cmd(self, command: str) -> None:
        if not self._conn or not self._connected:
            raise HomeAssistantError("Robot is not connected")
        _LOGGER.info("SLAM command: %s", command)
        self._conn.datachannel.pub_sub.publish_without_callback(
            RTC_TOPIC["LIDAR_MAPPING_CMD"], command,
        )

    def _on_slam_log(self, msg: dict) -> None:
        try:
            data = msg.get("data", "")
            if isinstance(data, dict):
                data = data.get("data", "")
            if not isinstance(data, str):
                data = str(data)
            _LOGGER.info("SLAM log: %s", data)
            self._slam_log_lines.append(data)
            if len(self._slam_log_lines) > 50:
                self._slam_log_lines = self._slam_log_lines[-50:]

            if "mapping/start/success" in data:
                self._slam_status = "mapping"
            elif "mapping/stop/success" in data:
                self._slam_status = "idle"
            elif "localization/get_status/status/1" in data:
                self._slam_status = "localized"
            elif "localization/get_status/status/0" in data:
                self._slam_status = "localizing"
            elif "initialization succeed" in data:
                self._slam_status = "localized"
            elif "initialization failed" in data:
                self._slam_status = "localization_failed"
            elif "navigation/state_transition/REACHED" in data:
                self._slam_nav_status = "reached"
            elif "navigation/state_transition/" in data:
                status = data.split("navigation/state_transition/")[-1].strip().lower()
                self._slam_nav_status = status

            self._sensor_data["slam_status"] = self._slam_status
            self._sensor_data["slam_nav_status"] = self._slam_nav_status
        except Exception as exc:
            _LOGGER.debug("SLAM log parse error: %s", exc)

    def _on_slam_odom(self, msg: dict) -> None:
        try:
            data = msg.get("data", {})
            if isinstance(data, str):
                data = json.loads(data)
            pose = data.get("pose", {}).get("pose", {})
            pos = pose.get("position", {})
            orient = pose.get("orientation", {})
            self._slam_robot_x = round(pos.get("x", 0.0), 3)
            self._slam_robot_y = round(pos.get("y", 0.0), 3)
            qw = orient.get("w", 1.0)
            qx = orient.get("x", 0.0)
            qy = orient.get("y", 0.0)
            qz = orient.get("z", 0.0)
            self._slam_robot_yaw = round(
                math.atan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz)), 3
            )
            self._sensor_data["slam_x"] = self._slam_robot_x
            self._sensor_data["slam_y"] = self._slam_robot_y
            self._sensor_data["slam_yaw"] = self._slam_robot_yaw
        except Exception as exc:
            _LOGGER.debug("SLAM odom parse error: %s", exc)

    def _on_slam_cloud(self, msg: dict) -> None:
        try:
            data = msg.get("data", {})
            binary = data.get("data")
            if not isinstance(binary, (bytes, bytearray)) or len(binary) < 6:
                return

            xmin = data.get("xmin", 0.0)
            xmax = data.get("xmax", 1.0)
            ymin = data.get("ymin", 0.0)
            ymax = data.get("ymax", 1.0)

            arr = np.frombuffer(bytes(binary), dtype=np.uint16)
            n_points = len(arr) // 3
            if n_points == 0:
                return
            arr = arr[:n_points * 3].reshape(n_points, 3)
            x = arr[:, 0].astype(np.float64) / 1000.0 + xmin
            y = arr[:, 1].astype(np.float64) / 1000.0 + ymin

            points = np.column_stack([x, y])
            if self._slam_combined is None:
                self._slam_combined = points
            else:
                self._slam_combined = np.vstack([self._slam_combined, points])
                if len(self._slam_combined) > 50000:
                    idx = np.random.choice(len(self._slam_combined), 40000, replace=False)
                    self._slam_combined = self._slam_combined[idx]
            self._slam_frame_count += 1
            if self._slam_frame_count % 2 == 0:
                self._render_slam_map(self._slam_combined)
        except Exception as exc:
            _LOGGER.warning("SLAM cloud parse error: %s", exc)

    SLAM_MAP_SIZE = 800
    SLAM_MAP_MARGIN = 40

    def _render_slam_map(self, points: np.ndarray) -> None:
        if not _HAS_PILLOW:
            return
        try:
            x = points[:, 0]
            y = points[:, 1]

            rx_w = self._slam_robot_x
            ry_w = self._slam_robot_y

            x_min = min(float(x.min()), rx_w) - 1.0
            x_max = max(float(x.max()), rx_w) + 1.0
            y_min = min(float(y.min()), ry_w) - 1.0
            y_max = max(float(y.max()), ry_w) + 1.0

            x_range = max(x_max - x_min, 1.0)
            y_range = max(y_max - y_min, 1.0)

            sz = self.SLAM_MAP_SIZE
            mg = self.SLAM_MAP_MARGIN
            usable = sz - 2 * mg
            sc = min(usable / x_range, usable / y_range)

            ox = mg + (usable - x_range * sc) / 2
            oy = mg + (usable - y_range * sc) / 2

            px_arr = ((x - x_min) * sc + ox).astype(np.int32)
            py_arr = ((y_max - y) * sc + oy).astype(np.int32)

            img = np.zeros((sz, sz, 3), dtype=np.uint8)
            img[:] = 15

            mask = (px_arr >= 0) & (px_arr < sz) & (py_arr >= 0) & (py_arr < sz)
            px_v = px_arr[mask]
            py_v = py_arr[mask]
            img[py_v, px_v] = [180, 180, 180]

            rx = int((rx_w - x_min) * sc + ox)
            ry = int((y_max - ry_w) * sc + oy)

            ms = 8
            for dy in range(-ms, ms + 1):
                for dx in range(-ms, ms + 1):
                    if dx * dx + dy * dy <= ms * ms:
                        py_r, px_r = ry + dy, rx + dx
                        if 0 <= py_r < sz and 0 <= px_r < sz:
                            img[py_r, px_r] = [0, 255, 0]

            arrow_len = 22
            ax = int(rx + math.cos(self._slam_robot_yaw) * arrow_len)
            ay = int(ry - math.sin(self._slam_robot_yaw) * arrow_len)
            steps = max(abs(ax - rx), abs(ay - ry), 1)
            for i in range(steps):
                ix = int(rx + (ax - rx) * i / steps)
                iy = int(ry + (ay - ry) * i / steps)
                if 0 <= ix < sz and 0 <= iy < sz:
                    for d in range(-1, 2):
                        for e in range(-1, 2):
                            if 0 <= iy+d < sz and 0 <= ix+e < sz:
                                img[iy+d, ix+e] = [0, 255, 80]

            pil_img = Image.fromarray(img)
            buf = io.BytesIO()
            pil_img.save(buf, format="PNG")
            self._slam_map_image = buf.getvalue()
        except Exception as exc:
            _LOGGER.warning("SLAM map render error: %s", exc)

    @property
    def last_slam_map_frame(self) -> bytes | None:
        return self._slam_map_image

    async def async_mapping_start(self) -> None:
        if not self._conn or not self._connected:
            raise HomeAssistantError("Robot is not connected")
        self._slam_combined = None
        self._slam_frame_count = 0
        self._slam_map_image = None
        self._slam_cmd("mapping/start")
        self._slam_status = "mapping"
        self._sensor_data["slam_status"] = self._slam_status

    async def async_mapping_stop(self) -> None:
        if not self._conn or not self._connected:
            raise HomeAssistantError("Robot is not connected")
        self._slam_cmd("mapping/stop")
        self._slam_status = "saving"
        self._sensor_data["slam_status"] = self._slam_status

    async def async_localization_start(self) -> None:
        if not self._conn or not self._connected:
            raise HomeAssistantError("Robot is not connected")
        self._slam_cmd("localization/start")
        self._slam_status = "localizing"
        self._sensor_data["slam_status"] = self._slam_status

    async def async_localization_stop(self) -> None:
        if not self._conn or not self._connected:
            raise HomeAssistantError("Robot is not connected")
        self._slam_cmd("localization/stop")
        self._slam_status = "idle"
        self._sensor_data["slam_status"] = self._slam_status

    async def async_navigation_start(self) -> None:
        if not self._conn or not self._connected:
            raise HomeAssistantError("Robot is not connected")
        self._slam_cmd("navigation/start")

    async def async_navigation_stop(self) -> None:
        if not self._conn or not self._connected:
            raise HomeAssistantError("Robot is not connected")
        self._slam_cmd("navigation/stop")

    async def async_navigate_to(self, x: float, y: float, yaw: float) -> None:
        if not self._conn or not self._connected:
            raise HomeAssistantError("Robot is not connected")
        if self._slam_status != "localized":
            raise HomeAssistantError(
                "Robot is not localized. Start localization first."
            )
        self._slam_cmd("navigation/start")
        await asyncio.sleep(0.5)
        self._slam_cmd(f"navigation/set_goal_pose/{x:.3f}/{y:.3f}/{yaw:.3f}")
        self._slam_nav_status = "navigating"
        self._sensor_data["slam_nav_status"] = self._slam_nav_status

    # ── Coordinator update ────────────────────────────────────────────

    async def _async_update_data(self) -> dict:
        if self._connected:
            self._check_connection()

        if not self._connected:
            try:
                await self.async_connect()
            except Exception as exc:
                raise UpdateFailed(f"Connection failed: {exc}") from exc

        await self._poll_vui_and_obstacles()
        return dict(self._sensor_data)
