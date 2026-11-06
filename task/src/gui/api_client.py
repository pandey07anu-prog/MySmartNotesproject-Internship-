"""
Smart Notes Assistant - Desktop Backend Client
Phase 8: Premium Native Windows Desktop Application

Centralized HTTP client communicating with the local FastAPI service (127.0.0.1:8000).
Implements background threading to prevent GUI freezing and ensures safe main-thread
callback execution via Tkinter.
"""

from __future__ import annotations

import concurrent.futures
import threading
from typing import Any, Callable, Dict, List, Optional

import httpx


class APIClientError(Exception):
    """Base exception for API client operations."""
    def __init__(self, message: str, status_code: Optional[int] = None, detail: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail or message


class APIConnectionError(APIClientError):
    """Raised when connection to backend fails."""
    pass


class APITimeoutError(APIClientError):
    """Raised when request times out."""
    pass


class APIResponseError(APIClientError):
    """Raised when server returns an HTTP 4xx or 5xx status."""
    pass


class NotesApiClient:
    """
    Centralized HTTP client interfacing with the Smart Notes Assistant REST API.
    Provides synchronous operations and non-blocking background dispatching.
    """

    DEFAULT_BASE_URL = "http://127.0.0.1:8000"
    DEFAULT_TIMEOUT = 6.0

    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="NotesAPI")
        self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout)

    def close(self) -> None:
        """Close connection pool and shutdown executor threads."""
        try:
            self._client.close()
        except Exception:
            pass
        self._executor.shutdown(wait=False)

    def _handle_request(self, method: str, path: str, **kwargs) -> Any:
        """Internal helper handling HTTP transmission, timeout, and clean error masking."""
        url = path if path.startswith("/") else f"/{path}"
        try:
            response = self._client.request(method=method, url=url, **kwargs)
        except (httpx.ConnectError, httpx.ConnectTimeout):
            raise APIConnectionError("Unable to connect to the Smart Notes backend daemon at 127.0.0.1:8000.")
        except httpx.TimeoutException:
            raise APITimeoutError("Request to backend daemon timed out.")
        except httpx.RequestError as e:
            raise APIConnectionError(f"Network error during API operation: {e}")

        # Check HTTP status code
        if response.is_success:
            try:
                return response.json()
            except Exception:
                return response.text

        # Error response handling
        status_code = response.status_code
        try:
            err_data = response.json()
            detail = err_data.get("detail", response.text)
        except Exception:
            detail = response.text or f"HTTP {status_code}"

        raise APIResponseError(
            message=f"Backend request failed with status {status_code}: {detail}",
            status_code=status_code,
            detail=str(detail)
        )

    # -----------------------------------------------------------------------
    # API Methods
    # -----------------------------------------------------------------------

    def get_health(self) -> Dict[str, Any]:
        """GET /health - Service health check."""
        return self._handle_request("GET", "/health")

    def classify_text(self, text: str) -> Dict[str, Any]:
        """POST /classify - Model inference and uncertainty detection."""
        return self._handle_request("POST", "/classify", json={"text": text})

    def get_notes(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """GET /notes - Retrieve saved notes, optionally filtered by category."""
        params = {"category": category} if category else None
        return self._handle_request("GET", "/notes", params=params)

    def get_note(self, note_id: str) -> Dict[str, Any]:
        """GET /notes/{id} - Retrieve single note by ID."""
        return self._handle_request("GET", f"/notes/{note_id}")

    def create_note(self, text: str) -> Dict[str, Any]:
        """POST /notes - Create new note with genuine ML classification."""
        return self._handle_request("POST", "/notes", json={"text": text})

    def update_note(self, note_id: str, text: str) -> Dict[str, Any]:
        """PUT /notes/{id} - Update note text and reclassify."""
        return self._handle_request("PUT", f"/notes/{note_id}", json={"text": text})

    def delete_note(self, note_id: str) -> Dict[str, Any]:
        """DELETE /notes/{id} - Delete note (ID never recycled)."""
        return self._handle_request("DELETE", f"/notes/{note_id}")

    def search_notes(
        self,
        query: str,
        method: str = "tfidf",
        top_k: int = 25
    ) -> List[Dict[str, Any]]:
        """GET /search - Query notes collection via TF-IDF or Keyword engine."""
        params = {"query": query, "method": method, "top_k": top_k}
        return self._handle_request("GET", "/search", params=params)

    def load_starter_notes(self) -> Dict[str, Any]:
        """POST /notes/load-starter - Idempotently load starter notes N001-N012."""
        return self._handle_request("POST", "/notes/load-starter")

    # -----------------------------------------------------------------------
    # Non-blocking Threaded Dispatching
    # -----------------------------------------------------------------------

    def execute_async(
        self,
        fn: Callable[..., Any],
        *args,
        on_success: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        tk_root: Optional[Any] = None,
        **kwargs
    ) -> None:
        """
        Execute an API call on a background thread and deliver callbacks back
        to the main Tkinter thread via tk_root.after().
        """
        def _worker():
            try:
                res = fn(*args, **kwargs)
                if on_success:
                    if tk_root and hasattr(tk_root, "after"):
                        tk_root.after(0, on_success, res)
                    else:
                        on_success(res)
            except Exception as exc:
                if on_error:
                    if tk_root and hasattr(tk_root, "after"):
                        tk_root.after(0, on_error, exc)
                    else:
                        on_error(exc)

        self._executor.submit(_worker)
