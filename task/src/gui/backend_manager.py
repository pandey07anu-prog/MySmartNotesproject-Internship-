"""
Smart Notes Assistant - Backend Daemon Lifecycle Manager
Phase 8: Premium Native Windows Desktop Application

Responsible for:
1. Detecting if the local FastAPI backend service is already operational on 127.0.0.1:8000.
2. Spawning a local Uvicorn child process if not already running.
3. Polling /health with bounded timeout until healthy.
4. Tracking process ownership and shutting down only the child process it spawned.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import httpx

from src.data_ingestion import get_project_root


class BackendLifecycleManager:
    """
    Manages the lifecycle of the local FastAPI backend daemon for the desktop GUI.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        startup_timeout: float = 15.0,
        project_root: Optional[Path] = None,
    ):
        self.host = host
        self.port = port
        self.startup_timeout = startup_timeout
        self.project_root = project_root or get_project_root()
        self.base_url = f"http://{self.host}:{self.port}"
        self.process: Optional[subprocess.Popen] = None
        self.owns_process: bool = False

    def is_healthy(self) -> bool:
        """Query /health to determine if a responsive backend is already active."""
        try:
            with httpx.Client(timeout=1.5) as client:
                resp = client.get(f"{self.base_url}/health")
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("status") == "healthy"
        except Exception:
            return False
        return False

    def ensure_backend_running(self) -> bool:
        """
        Verify whether backend is active; if not, launch a child Uvicorn instance
        and poll until healthy. Returns True on success, False on failure.
        """
        if self.is_healthy():
            self.owns_process = False
            return True

        # Launch child process
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.project_root)
        env["PYTHONIOENCODING"] = "utf-8"

        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "src.api:app",
            "--host",
            self.host,
            "--port",
            str(self.port),
            "--log-level",
            "warning",
        ]

        try:
            # On Windows, use CREATE_NO_WINDOW if available to prevent black console popups
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

            self.process = subprocess.Popen(
                cmd,
                cwd=str(self.project_root),
                env=env,
                creationflags=creation_flags,
            )
            self.owns_process = True
        except Exception as e:
            self.process = None
            self.owns_process = False
            return False

        # Wait for readiness
        start_time = time.perf_counter()
        while time.perf_counter() - start_time < self.startup_timeout:
            if self.is_healthy():
                return True
            # Check if process terminated prematurely
            if self.process.poll() is not None:
                self.owns_process = False
                return False
            time.sleep(0.3)

        # Timeout reached without health confirmation
        self.stop()
        return False

    def stop(self) -> None:
        """Safely terminate child process if owned."""
        if self.owns_process and self.process is not None:
            try:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3.0)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            except Exception:
                pass
            finally:
                self.process = None
                self.owns_process = False

