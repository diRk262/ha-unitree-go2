import aioice


class Connection(aioice.Connection):
    local_username = aioice.utils.random_string(4)
    local_password = aioice.utils.random_string(22)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.local_username = Connection.local_username
        self.local_password = Connection.local_password


aioice.Connection = Connection  # type: ignore

import aiortc
from packaging.version import Version

if Version(aiortc.__version__) == Version("1.10.0"):
    X509_DIGEST_ALGORITHMS = {"sha-256": "SHA256"}
    aiortc.rtcdtlstransport.X509_DIGEST_ALGORITHMS = X509_DIGEST_ALGORITHMS
elif Version(aiortc.__version__) >= Version("1.11.0"):
    from cryptography.hazmat.primitives import hashes
    X509_DIGEST_ALGORITHMS = {"sha-256": hashes.SHA256()}
    aiortc.rtcdtlstransport.X509_DIGEST_ALGORITHMS = X509_DIGEST_ALGORITHMS

from .webrtc_driver import UnitreeWebRTCConnection  # noqa: E402
from .webrtc_datachannel import WebRTCDataChannel  # noqa: E402
from .constants import (  # noqa: E402
    WebRTCConnectionMethod,
    DATA_CHANNEL_TYPE,
    RTC_TOPIC,
    OBSTACLES_AVOID_API,
)
from .unitree_cloud import (  # noqa: E402
    UnitreeCloud,
    UnitreeCloudError,
    RobotDevice,
)
from .unitree_auth import (  # noqa: E402
    AesKeyRequiredError,
    AesKeyRejectedError,
    DataChannelTimeoutError,
    LocalSignalingPortError,
    NoSdpAnswerError,
    RobotBusyError,
)
from .multicast_scanner import discover_ip_sn  # noqa: E402

__all__ = [
    "UnitreeWebRTCConnection",
    "WebRTCConnectionMethod",
    "WebRTCDataChannel",
    "DATA_CHANNEL_TYPE",
    "RTC_TOPIC",
    "OBSTACLES_AVOID_API",
    "UnitreeCloud",
    "UnitreeCloudError",
    "RobotDevice",
    "discover_ip_sn",
    "AesKeyRequiredError",
    "AesKeyRejectedError",
    "DataChannelTimeoutError",
    "LocalSignalingPortError",
    "NoSdpAnswerError",
    "RobotBusyError",
]
