"""Cookie-session HTTP client for acceptance checks (user-perspective, no DB)."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
import http.cookiejar
from typing import Any, Callable, Optional

from .config import AcceptanceConfig


class AcceptanceClient:
    def __init__(self, config: AcceptanceConfig):
        self.config = config
        self._cj = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._cj)
        )

    def login(self) -> bool:
        body = json.dumps(
            {"email": self.config.email, "password": self.config.password}
        ).encode()
        req = urllib.request.Request(
            f"{self.config.base_url_normalized}/api/login",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            self._opener.open(req, timeout=30)
            return True
        except urllib.error.HTTPError as e:
            print(f"LOGIN FAIL: {e.code}")
            return False

    def get_json(self, path: str) -> Any:
        resp = self._get(path)
        return json.loads(resp.read().decode())

    def get_text(self, path: str) -> str:
        return self._get(path).read().decode()

    def _get(self, path: str):
        if not path.startswith("/"):
            path = "/" + path
        req = urllib.request.Request(
            f"{self.config.base_url_normalized}{path}",
            headers={"X-Customer-ID": str(self.config.customer_id)},
        )
        return self._opener.open(req, timeout=self.config.timeout_sec)

    def fetch_main_js(self) -> Optional[str]:
        html = self.get_text("/")
        m = re.search(r"/static/js/main\.([a-f0-9]+)\.js", html)
        if not m:
            return None
        return self.get_text(f"/static/js/main.{m.group(1)}.js")

    def check_js_markers(
        self,
        js: str,
        markers: list[tuple[str, str]],
        *,
        fail_labels: Optional[Callable[[str], bool]] = None,
    ) -> bool:
        """Print marker results; return False if any required marker missing."""
        ok = True
        fail_labels = fail_labels or (lambda _label: True)
        for label, needle in markers:
            if needle in js:
                print(f"  {label}: OK")
            else:
                print(f"  {label}: MISSING ({needle})")
                if fail_labels(label):
                    ok = False
        return ok
