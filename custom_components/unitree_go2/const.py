DOMAIN = "unitree_go2"

CONF_ROBOT_IP = "robot_ip"
CONF_AES_KEY = "aes_key"
CONF_SERIAL = "serial_number"
CONF_EMAIL = "email"
CONF_PASSWORD = "password"

SCAN_INTERVAL_SECONDS = 5

MODE_CODES = {
    0: "Idle",
    100: "Free Walk",
    1001: "Damping",
    1002: "Balance Stand",
    1003: "Stop Move",
    1004: "Stand Up",
    1005: "Stand Down",
    1006: "Recovery Stand",
    1008: "Move",
    1009: "Sit",
    1013: "Endurance",
    1015: "Normal",
    1016: "Running",
    1091: "Pose",
    2007: "Free Avoid",
    2008: "Bound",
    2009: "Jump",
    2010: "Classic",
    2011: "Hand Stand",
    2016: "Cross Step",
    2017: "Erect",
}

GAIT_CODES = {
    0: "Idle",
    1: "Trot",
    2: "Run",
    3: "Climb",
    4: "Forwardonly",
}
