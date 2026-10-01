"""Repository/runtime bootstrap for the one shared IoT contract."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'packages/iot-contract/python'))
from carbentra_iot_contract import (CAPABILITIES, PRODUCTS, PRESENCE_GATT, canonical, event_identity, timestamp,
                                   validate_command, validate_descriptor, validate_event, validate_switch_ack)
