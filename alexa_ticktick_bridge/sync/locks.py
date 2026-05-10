from __future__ import annotations

from pathlib import Path
from typing import TextIO


class RunLock:
    def __init__(self, path: Path) -> None:
        self.path = path.expanduser()
        self._handle: TextIO | None = None

    def __enter__(self) -> RunLock:
        import fcntl

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("w", encoding="utf-8")
        fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        import fcntl

        if self._handle is not None:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
            self._handle.close()
