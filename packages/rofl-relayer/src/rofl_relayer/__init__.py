"""
ROFL Relayer package.

Automated cross-chain message relay service for the Hashi bridge.
"""

from .config import RelayerConfig
from .event_processor import EventProcessor, PingEvent
from .relayer import ROFLRelayer

__all__ = ["RelayerConfig", "ROFLRelayer", "EventProcessor", "PingEvent"]
__version__ = "0.1.0"