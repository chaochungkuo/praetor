from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Set

import httpx


TERMINAL_NORMALIZED_STATUSES: Set[str] = {
    "completed",
    "paused_budget",
    "paused_decision",
    "paused_risk",
    "auth_required",
    "interactive_approval_required",
    "cancelled",
    "failed_transient",
    "failed_permanent",
}


class BridgeClientError(RuntimeError):
    pass


class BridgePollingTimeout(BridgeClientError):
    pass


@dataclass
class BridgeClient:
    base_url: str
    token: str
    timeout_seconds: float = 30.0

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        kwargs.setdefault("headers", self._headers())
        kwargs.setdefault("timeout", self.timeout_seconds)
        with httpx.Client(base_url=self.base_url) as client:
            response = client.request(method, path, **kwargs)
        payload = response.json()
        if response.status_code >= 400 or not payload.get("ok", False):
            error = payload.get("error") or {}
            raise BridgeClientError(
                f"{error.get('code', 'bridge_error')}: {error.get('message', 'unknown error')}"
            )
        return payload["data"]

    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/health")

    def executors(self) -> Dict[str, Any]:
        return self._request("GET", "/executors")

    def create_run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/runs", json=payload)

    def get_run(self, run_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/runs/{run_id}")

    def get_events(self, run_id: str, after_seq: int = 0) -> Dict[str, Any]:
        return self._request("GET", f"/runs/{run_id}/events", params={"after_seq": after_seq})

    def cancel_run(self, run_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/runs/{run_id}/cancel")

    def wait_for_terminal(
        self,
        run_id: str,
        *,
        poll_interval_seconds: float = 1.0,
        timeout_seconds: Optional[float] = None,
        terminal_statuses: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        terminal = set(terminal_statuses or TERMINAL_NORMALIZED_STATUSES)
        started = time.monotonic()
        while True:
            run = self.get_run(run_id)
            normalized = run.get("normalized_status")
            status = run.get("status")
            if normalized in terminal or status in terminal:
                return run
            if timeout_seconds is not None and (time.monotonic() - started) > timeout_seconds:
                raise BridgePollingTimeout(f"Timed out waiting for terminal status: {run_id}")
            time.sleep(poll_interval_seconds)
