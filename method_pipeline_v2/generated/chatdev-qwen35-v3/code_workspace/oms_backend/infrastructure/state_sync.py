"""
State synchronizer for NFR 2.3 (State Resynchronization)
Periodically compares and synchronizes state between active and standby components
"""
import asyncio
import time
import hashlib
import json
from typing import Dict, Any, Optional, Callable, Awaitable
from oms_backend.config.settings import get_settings

settings = get_settings()


class StateSynchronizer:
    """
    State synchronization system for NFR 2.3.
    Periodically compares states of active and standby components.
    
    Tactic: Availability > Detect Faults > State Resynchronization
    """
    
    def __init__(self, sync_interval: int = None):
        self.sync_interval = sync_interval or settings.state_sync_interval
        self._active_state: Dict[str, Any] = {}
        self._standby_state: Dict[str, Any] = {}
        self._last_sync_time: float = 0
        self._sync_count: int = 0
        self._mismatch_count: int = 0
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._state_getters: Dict[str, Callable[[], Awaitable[Dict]]] = {}
    
    def register_component(self, name: str, getter: Callable[[], Awaitable[Dict]]) -> None:
        """Register a component state getter for synchronization"""
        self._state_getters[name] = getter
    
    def _compute_checksum(self, state: Dict[str, Any]) -> str:
        """Compute checksum of state for comparison"""
        state_str = json.dumps(state, sort_keys=True, default=str)
        return hashlib.md5(state_str.encode()).hexdigest()
    
    async def _fetch_states(self) -> Dict[str, Dict]:
        """Fetch current states from all registered components"""
        states = {}
        for name, getter in self._state_getters.items():
            try:
                states[name] = await getter()
            except Exception as e:
                states[name] = {"error": str(e)}
        return states
    
    async def _sync_once(self) -> Dict[str, Any]:
        """Perform one synchronization cycle"""
        current_states = await self._fetch_states()
        
        result = {
            "timestamp": time.time(),
            "components": {},
            "mismatches": [],
            "synced": True
        }
        
        for name, state in current_states.items():
            checksum = self._compute_checksum(state)
            
            # Compare with standby state
            standby_checksum = self._compute_checksum(
                self._standby_state.get(name, {})
            )
            
            component_result = {
                "active_checksum": checksum,
                "standby_checksum": standby_checksum,
                "in_sync": checksum == standby_checksum
            }
            
            if checksum != standby_checksum:
                result["mismatches"].append(name)
                self._mismatch_count += 1
                # Update standby to match active (resynchronization)
                self._standby_state[name] = state.copy()
            
            self._active_state[name] = state.copy()
            result["components"][name] = component_result
        
        self._last_sync_time = time.time()
        self._sync_count += 1
        
        return result
    
    async def _sync_loop(self) -> None:
        """Continuous synchronization loop"""
        while self._running:
            try:
                await self._sync_once()
            except Exception as e:
                # Log error but continue sync loop
                pass
            await asyncio.sleep(self.sync_interval)
    
    def start(self) -> None:
        """Start the synchronization background task"""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._sync_loop())
    
    def stop(self) -> None:
        """Stop the synchronization background task"""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
    
    async def force_sync(self) -> Dict[str, Any]:
        """Force an immediate synchronization"""
        return await self._sync_once()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get synchronization statistics"""
        return {
            "sync_count": self._sync_count,
            "mismatch_count": self._mismatch_count,
            "last_sync_time": self._last_sync_time,
            "sync_interval": self.sync_interval,
            "running": self._running,
            "components_registered": len(self._state_getters)
        }
    
    def get_active_state(self, component: str) -> Optional[Dict]:
        """Get current active state for a component"""
        return self._active_state.get(component)
    
    def get_standby_state(self, component: str) -> Optional[Dict]:
        """Get current standby state for a component"""
        return self._standby_state.get(component)


# Global state synchronizer instance
state_synchronizer = StateSynchronizer()
