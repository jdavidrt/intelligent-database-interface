"""DBConnector protocol — thin interface over any relational DB."""

from __future__ import annotations
from typing import Any, Protocol, runtime_checkable
from backend.app.models.envelope import DBProfile


@runtime_checkable
class DBConnector(Protocol):
    """Read-only DB access + introspection.

    Concrete implementations: SoundwaveFileConnector (Days 1-3),
    MySQLConnector (Day 4+).
    """

    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def introspect(self) -> DBProfile: ...
    def execute_read(self, sql: str, limit: int = 200) -> list[dict[str, Any]]: ...
    def explain(self, sql: str) -> bool: ...  # True if the engine accepts the query plan


def get_connector():
    """Return the active DBConnector implementation per settings.connector."""
    from backend.app.config import settings
    if settings.connector == "mysql":
        # Day 4: from .mysql_connector import MySQLConnector; return MySQLConnector()
        raise NotImplementedError("MySQLConnector arrives on Day 4.")
    from .file_connector import SoundwaveFileConnector
    return SoundwaveFileConnector()
