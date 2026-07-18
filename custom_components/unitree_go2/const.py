DOMAIN = "unitree_go2"

CONF_ROBOT_IP = "robot_ip"
CONF_AES_KEY = "aes_key"
CONF_SERIAL = "serial_number"
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_ROBOT_NAME = "robot_name"
DEFAULT_ROBOT_NAME = "Go2"

SCAN_INTERVAL_SECONDS = 5

MOVEMENT_SWITCH_TIMEOUT = 300  # 5 minutes auto-off

# Wireless controller button bitmasks
BUTTON_R1 = 1
BUTTON_L1 = 2
BUTTON_START = 4
BUTTON_SELECT = 8
BUTTON_L2 = 32
BUTTON_R2 = 16
BUTTON_A = 256
BUTTON_B = 512
BUTTON_X = 1024
BUTTON_Y = 2048
BUTTON_DPAD_UP = 8192
BUTTON_DPAD_DOWN = 32768

# Sport API commands — no remote combo, utility only (rt/api/sport/request)
STATIONARY_COMMANDS = {
    "balance_stand": 1002,
    "stop_move": 1003,
    "content": 1020,
}

# Controller simulation — hold button combo (rt/wirelesscontroller)
# Stationary: require commands switch
STATIONARY_CONTROLLER_COMMANDS = {
    "stand_lock": BUTTON_L2 | BUTTON_A,              # L2+A
    "sit": BUTTON_R1 | BUTTON_B,                # R1+B
    "hello": BUTTON_R2 | BUTTON_B,              # R2+B (Shake Hands)
    "stretch": BUTTON_R2 | BUTTON_A,            # R2+A
    "heart": BUTTON_R2 | BUTTON_Y,              # R2+Y (Love)
    "greet": BUTTON_L1 | BUTTON_A,              # L1+A
    "pose": BUTTON_SELECT,                       # SELECT
    "endurance": BUTTON_L1 | BUTTON_SELECT,      # L1+SELECT
}

# Movement: require movement switch
MOVEMENT_CONTROLLER_COMMANDS = {
    "recovery_stand": BUTTON_L2 | BUTTON_X,     # L2+X
    "front_jump": BUTTON_R1 | BUTTON_A,          # R1+A
    "front_pounce": BUTTON_R1 | BUTTON_X,        # R1+X
    "dance1": BUTTON_L1 | BUTTON_B,              # L1+B
    "dance2": BUTTON_L1 | BUTTON_X,              # L1+X
    "unlock_gait": BUTTON_START,                  # START
    "running": BUTTON_L2 | BUTTON_START,         # L2+START
    "normal": BUTTON_L1 | BUTTON_START,          # L1+START
    "classic": BUTTON_DPAD_UP | BUTTON_START,    # D-Pad Up+START
    "free_walk": BUTTON_DPAD_DOWN | BUTTON_START, # D-Pad Down+START
    "damp": BUTTON_L2 | BUTTON_B,               # L2+B
}

# Double-click commands: require movement switch
DOUBLE_CLICK_COMMANDS = {
    "free_avoid": BUTTON_A,                      # Double Click A
    "cross_step": BUTTON_B,                      # Double Click B
    "bound": BUTTON_X,                           # Double Click X
    "jump_gait": BUTTON_Y,                       # Double Click Y
    "handstand": BUTTON_R1,                      # Double Click R1
    "erect": BUTTON_R2,                          # Double Click R2
}

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
    1017: "Stretch",
    1091: "Pose",
    2007: "Free Avoid",
    2008: "Bound",
    2009: "Jump",
    2010: "Classic",
    2011: "Hand Stand",
    2016: "Cross Step",
    2017: "Erect",
}

TRICK_COMMANDS = {
    "sit", "hello", "stretch", "heart", "greet", "pose",
    "front_jump", "front_pounce", "dance1", "dance2",
    "handstand", "erect", "cross_step", "bound", "jump_gait",
    "free_avoid", "endurance", "content",
}

GAIT_CODES = {
    0: "Idle",
    1: "Trot",
    2: "Run",
    3: "Climb",
    4: "Forwardonly",
}
