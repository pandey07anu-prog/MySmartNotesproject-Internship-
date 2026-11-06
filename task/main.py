"""
Smart Notes Assistant - Desktop Application Entrypoint
Phase 8: Premium Native Windows Desktop Application

Launches the native Windows desktop application:
1. Detects or spawns the local FastAPI backend daemon on 127.0.0.1:8000.
2. Initializes the CustomTkinter desktop interface.
3. Coordinates clean process shutdown upon exit.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> int:
    print("=" * 70)
    print("SMART NOTES ASSISTANT — Starting Native Windows Desktop Application")
    print("=" * 70)

    from src.gui.api_client import NotesApiClient
    from src.gui.app import SmartNotesApp
    from src.gui.backend_manager import BackendLifecycleManager

    # 1. Manage backend lifecycle
    backend_mgr = BackendLifecycleManager(
        host="127.0.0.1",
        port=8000,
        startup_timeout=15.0,
        project_root=PROJECT_ROOT,
    )

    print("[1/2] Connecting to local FastAPI backend service...")
    ready = backend_mgr.ensure_backend_running()
    if not ready:
        print("[ERROR] Failed to start or connect to local FastAPI backend on 127.0.0.1:8000.")
        print("Please verify that port 8000 is available and dependencies are installed.")
        return 1

    if backend_mgr.owns_process:
        print("  - Local Uvicorn child daemon started successfully (PID: {})".format(backend_mgr.process.pid if backend_mgr.process else "N/A"))
    else:
        print("  - Reusing active backend service on http://127.0.0.1:8000")

    # 2. Launch Desktop GUI Application
    print("[2/2] Launching CustomTkinter desktop application window...")
    api_client = NotesApiClient(base_url="http://127.0.0.1:8000", timeout=6.0)

    app = SmartNotesApp(
        api_client=api_client,
        backend_manager=backend_mgr,
    )

    try:
        app.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        print("\nShutting down SMART NOTES...")
        backend_mgr.stop()
        api_client.close()
        print("Shutdown complete.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

