"""DegradationManager – simple flag‑based feature toggle.

When system load is high (simulated by external trigger), non‑essential endpoints are disabled.

Implements **NFR 2.1 Graceful Degradation**.
"""

import threading

class DegradationManager:
    _degraded = False
    _lock = threading.Lock()

    @classmethod
    def enable_degradation(cls):
        with cls._lock:
            cls._degraded = True

    @classmethod
    def disable_degradation(cls):
        with cls._lock:
            cls._degraded = False

    @classmethod
    def is_degraded(cls) -> bool:
        return cls._degraded

    @classmethod
    def should_degrade_feature(cls, feature_name: str) -> bool:
        # In this simple implementation we degrade everything when flag is set.
        return cls._degraded

    @classmethod
    def disable_non_essential_endpoints(cls):
        # Placeholder – actual disabling is performed via router dependencies.
        cls.enable_degradation()

    @classmethod
    def enable_all_features(cls):
        cls.disable_degradation()
