"""AllStarLink 数据源专属常量。"""

from typing import Dict, List

CONNECTION_PREFIXES: Dict[str, str] = {
    "T": "Transceive",
    "R": "RX Only",
    "L": "Local",
    "P": "Permanent",
}

NODE_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "Hub": ["HUB", "SYSTEM", "NETWORK"],
    "Repeater": [],
}

HARDWARE_KEYWORDS: Dict[str, List[str]] = {
    "Personal Station": ["SHACK", "HOME", "RESIDENCE"],
    "Infrastructure": ["HUB", "NETWORK", "DATA CENTER", "RACK"],
    "Embedded Node": ["PI", "ORANGEPI", "CLEARNODE", "ARM", "RASPBERRY PI"],
}

DEFAULT_LATITUDE: float = 0.0
DEFAULT_LONGITUDE: float = 0.0
DEFAULT_TOTAL_KEYUPS: int = 0
DEFAULT_TOTAL_TX_TIME: int = 0

NODE_TYPE_ALLSTARLINK: str = "allstarlink"
NODE_TYPE_OTHERS: str = "others"

NODE_RANK_UNKNOWN: str = "Unknown"
NODE_RANK_HUB: str = "Hub"
NODE_RANK_REPEATER: str = "Repeater"

HARDWARE_TYPE_UNKNOWN: str = "Unknown"
HARDWARE_TYPE_PERSONAL: str = "Personal Station"
HARDWARE_TYPE_INFRASTRUCTURE: str = "Infrastructure"
HARDWARE_TYPE_EMBEDDED: str = "Embedded Node"

CONNECTION_STATUS_ACTIVE: str = "Active"
CONNECTION_STATUS_INACTIVE: str = "Inactive"
CONNECTION_DIRECTION_UNKNOWN: str = "Unknown"
