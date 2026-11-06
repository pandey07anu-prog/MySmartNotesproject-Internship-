"""
Smart Notes Assistant - Native Desktop GUI Package
Phase 8: Premium Native Windows Desktop Application
"""

from src.gui.api_client import NotesApiClient
from src.gui.app import SmartNotesApp
from src.gui.backend_manager import BackendLifecycleManager
from src.gui.theme import theme_mgr

__all__ = [
    "SmartNotesApp",
    "NotesApiClient",
    "BackendLifecycleManager",
    "theme_mgr",
]

