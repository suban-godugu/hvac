"""Shared BMS gateway layer. Phase 1 is read-only."""

from backend.bms.connection_manager import get_connection_manager, reset_connection_manager
from backend.bms.command_writer import physical_writes_allowed, write_disabled_body, write_point

__all__ = [
    "get_connection_manager",
    "reset_connection_manager",
    "physical_writes_allowed",
    "write_disabled_body",
    "write_point",
]
