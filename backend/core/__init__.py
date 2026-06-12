"""
Core modules for AIMirror platform
Contains fundamental business logic and domain services
"""

from .behavior_gateway import BehaviorGateway
from .event_normalizer import EventNormalizer

__all__ = [
    "BehaviorGateway",
    "EventNormalizer"
]
