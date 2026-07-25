"""
Persistence module for state preservation
"""
from .wal import WriteAheadLog, get_wal

__all__ = ["WriteAheadLog", "get_wal"]
