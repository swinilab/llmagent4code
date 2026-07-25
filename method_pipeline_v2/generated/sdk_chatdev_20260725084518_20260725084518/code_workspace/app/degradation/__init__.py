"""
Graceful degradation module
"""
from .degradation_manager import DegradationManager, get_degradation_manager

__all__ = ["DegradationManager", "get_degradation_manager"]
