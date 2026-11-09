"""Simulator HTTP API client with retries, connection pooling, and error handling."""
import logging
import time
from typing import Any, Dict, Iterator, List, Optional
import httpx

logger = logging.getLogger("controller.client")


class SimulatorClient:
    """Robust HTTP client for the simulator."""

    def __init__(self, base_url: str, timeout: float = 120.0, max_retries: int = 3):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = httpx.Client(base_url=self.base_url, timeout=self.timeout)

    def close(self):
        self.client.close()

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        last_exc = None
        for attempt in range(self.max_retries):
            try:
                resp = self.client.request(method, url, **kwargs)
                # If server returns 5xx, retry with short backoff
                if 500 <= resp.status_code < 600 and attempt < self.max_retries - 1:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                return resp
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
                last_exc = e
                if attempt < self.max_retries - 1:
                    time.sleep(0.5 * (2 ** attempt))
                else:
                    raise
        raise last_exc or RuntimeError("Request failed after retries")

    def get_state(self) -> Dict[str, Any]:
        resp = self._request("GET", "/sim/state")
        resp.raise_for_status()
        return resp.json()

    def advance(self, minutes: int) -> Dict[str, Any]:
        resp = self._request("POST", "/sim/advance", json={"minutes": minutes})
        resp.raise_for_status()
        return resp.json()

    def get_chunks(self, kind: str = "events", after: int = -1) -> List[Dict[str, Any]]:
        resp = self._request("GET", "/events/chunks", params={"kind": kind, "after": after})
        resp.raise_for_status()
        return resp.json()

    def stream_chunk_lines(self, chunk_num: int) -> Iterator[str]:
        """Stream NDJSON lines from chunk endpoint."""
        url = f"{self.base_url}/events/chunks/{chunk_num}"
        with self.client.stream("GET", url) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                line = line.strip()
                if line:
                    yield line

    def get_workflows(self) -> List[Dict[str, Any]]:
        resp = self._request("GET", "/workflows")
        resp.raise_for_status()
        return resp.json()

    def get_workflow(self, wid: str) -> Dict[str, Any]:
        resp = self._request("GET", f"/workflows/{wid}")
        resp.raise_for_status()
        return resp.json()

    def get_config(self, wid: str) -> Dict[str, Any]:
        resp = self._request("GET", f"/workflows/{wid}/config")
        resp.raise_for_status()
        return resp.json()

    def auto_apply(self, wid: str, body: Dict[str, Any]) -> httpx.Response:
        return self._request("PUT", f"/workflows/{wid}/config", json=body)

    def request_approval(self, body: Dict[str, Any]) -> httpx.Response:
        return self._request("POST", "/approvals", json=body)

    def get_approval(self, aid: str) -> Dict[str, Any]:
        resp = self._request("GET", f"/approvals/{aid}")
        resp.raise_for_status()
        return resp.json()

    def list_approvals(self, workflow_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        params = {}
        if workflow_id:
            params["workflow_id"] = workflow_id
        if status:
            params["status"] = status
        resp = self._request("GET", "/approvals", params=params)
        resp.raise_for_status()
        return resp.json()

    def apply_approval(self, wid: str, aid: str) -> httpx.Response:
        return self._request("POST", f"/workflows/{wid}/apply", json={"approval_id": aid})

    def suggest_fixes(self, wid: str, problem: str) -> Dict[str, Any]:
        resp = self._request("POST", "/llm/suggest-fixes", json={"workflow_id": wid, "problem": problem})
        resp.raise_for_status()
        return resp.json()

    def run_validation(self, wid: str, pv: str, n: int = 200) -> Dict[str, Any]:
        resp = self._request("POST", "/validation/runs", json={"workflow_id": wid, "prompt_version": pv, "n": n})
        resp.raise_for_status()
        return resp.json()
