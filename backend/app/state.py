"""In-memory runtime state shared across routes/services."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock


@dataclass
class RuntimeState:
    chaos_mode: bool = False
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def toggle_chaos_mode(self) -> bool:
        with self._lock:
            self.chaos_mode = not self.chaos_mode
            return self.chaos_mode

    def is_chaos_mode(self) -> bool:
        with self._lock:
            return self.chaos_mode


runtime_state = RuntimeState()
