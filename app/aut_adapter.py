from __future__ import annotations

import json
import time
from typing import Any, Dict, Tuple

import requests

from config import settings
from .schemas import Action


class RESTAdapter:
    """Execute Actions against a REST API and return observation + latency."""

    _METHOD_MAP: Dict[str, str] = {
        "navigate": "GET",
        "type": "POST",
        "tap": "POST",
        "scroll": "GET",
        "upload": "POST",
    }

    def __init__(self, base_url: str | None = None, timeout: float = 10.0) -> None:
        self.base_url = (base_url or settings.api_base_url).rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()

    def execute(self, action: Action) -> Tuple[str, float]:
        if action.type == "report":
            issue = action.payload.get("issue", "") if action.payload else ""
            return f"Report submitted: {issue}", 0.0

        method = self._METHOD_MAP.get(action.type, "GET")
        url = self._build_url(action.target)
        request_kwargs, cleanup_handles = self._prepare_request_kwargs(action, method)

        start = time.time()
        try:
            response = self._session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **request_kwargs,
            )
            latency = time.time() - start
            observation = self._format_response(response)
        except requests.RequestException as exc:
            latency = time.time() - start
            observation = f"HTTP_ERROR: {exc}"
        finally:
            for handle in cleanup_handles:
                try:
                    handle.close()
                except Exception:
                    pass

        return observation, latency

    def _build_url(self, target: str) -> str:
        if target.startswith(("http://", "https://")):
            return target
        if not target.startswith("/"):
            target = f"/{target}"
        return f"{self.base_url}{target}"

    def _prepare_request_kwargs(self, action: Action, method: str) -> tuple[dict[str, Any], list[Any]]:
        payload = action.payload or {}
        kwargs: dict[str, Any] = {}
        cleanup: list[Any] = []

        headers = payload.get("headers")
        if isinstance(headers, dict):
            kwargs["headers"] = headers

        params = payload.get("params")
        if isinstance(params, dict):
            kwargs["params"] = params

        if method in {"POST", "PUT", "PATCH"}:
            if "json" in payload:
                kwargs["json"] = payload["json"]
            elif payload:
                kwargs["json"] = payload

        if action.type == "upload":
            file_path = payload.get("file_path")
            field_name = payload.get("field", "file")
            if file_path:
                try:
                    handle = open(file_path, "rb")
                    kwargs["files"] = {field_name: handle}
                    cleanup.append(handle)
                except FileNotFoundError:
                    kwargs.setdefault("json", {})["error"] = f"File not found: {file_path}"

        return kwargs, cleanup

    @staticmethod
    def _format_response(response: requests.Response) -> str:
        status = f"{response.status_code} {response.reason}"
        try:
            body = response.json()
            body_preview = json.dumps(body, indent=2)[:500]
        except ValueError:
            body_preview = response.text[:500]
        return f"{status} :: {body_preview}"
