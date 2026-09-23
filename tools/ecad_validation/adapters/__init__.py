"""Open-source validation tool adapters."""

from .base import Adapter, AdapterRequest, AdapterResult, Capability
from .capabilities import detect_capabilities

__all__ = [
    "Adapter",
    "AdapterRequest",
    "AdapterResult",
    "Capability",
    "detect_capabilities",
]
