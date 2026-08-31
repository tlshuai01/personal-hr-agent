"""Shared Boss HTTP client: zp_token, jitter delay, cookie merge, typed errors.

Patterns adapted from zhipin-geek BossClient (rate limit + headers).
"""

from __future__ import annotations

import logging
import random
import time
from collections import deque
from typing import Any

import httpx

LOG = logging.getLogger("boss-bridge.http")

BASE_URL = "https://www.zhipin.com"
CHAT_REFERER = "https://www.zhipin.com/web/geek/chat"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Origin": BASE_URL,
    "Referer": CHAT_REFERER,
    "X-Requested-With": "XMLHttpRequest",
}


class BossHttpError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: int | None = None,
        response: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.response = response or {}


class SessionExpiredError(BossHttpError):
    pass


class RateLimitError(BossHttpError):
    pass


class BossHttpClient:
    """httpx session with anti-bot-friendly delays and zp_token header."""

    def __init__(
        self,
        cookies: dict[str, str],
        *,
        timeout: float = 30.0,
        request_delay: float = 0.8,
    ) -> None:
        self._cookies = dict(cookies)
        self._timeout = timeout
        self._request_delay = request_delay
        self._base_request_delay = request_delay
        self._last_request_time = 0.0
        self._rate_limit_count = 0
        self._recent_request_times: deque[float] = deque(maxlen=12)
        self._http = httpx.Client(
            base_url=BASE_URL,
            headers=dict(DEFAULT_HEADERS),
            cookies=self._cookies,
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "BossHttpClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _rate_limit_delay(self) -> None:
        if self._request_delay <= 0:
            return
        elapsed = time.time() - self._last_request_time
        if elapsed < self._request_delay:
            jitter = max(0.0, random.gauss(0.25, 0.12))
            if random.random() < 0.05:
                jitter += random.uniform(1.5, 3.5)
            time.sleep(self._request_delay - elapsed + jitter)
        now = time.time()
        recent_15s = sum(1 for ts in self._recent_request_times if now - ts <= 15)
        if recent_15s >= 4:
            time.sleep(random.uniform(1.0, 2.5))

    def _mark_request(self) -> None:
        now = time.time()
        self._last_request_time = now
        self._recent_request_times.append(now)

    def _headers(self, *, referer: str | None = None) -> dict[str, str]:
        headers = dict(DEFAULT_HEADERS)
        if referer:
            headers["Referer"] = referer
        bst = str(self._http.cookies.get("bst") or self._cookies.get("bst") or "")
        if bst:
            headers["zp_token"] = bst
        return headers

    def _merge_cookies(self, resp: httpx.Response) -> None:
        for name, value in resp.cookies.items():
            if value:
                self._http.cookies.set(name, value)
                self._cookies[name] = value

    def _handle_payload(self, data: dict[str, Any], action: str) -> dict[str, Any]:
        code = data.get("code", -1)
        if code == 0:
            self._rate_limit_count = 0
            zp = data.get("zpData")
            return zp if isinstance(zp, dict) else ({} if zp is None else {"_raw": zp})

        message = str(data.get("message") or "Unknown error")
        if code == 37:
            raise SessionExpiredError(
                f"{action}: session expired (code=37)", code=code, response=data
            )
        if code == 9:
            self._rate_limit_count += 1
            cooldown = min(60, 10 * (2 ** (self._rate_limit_count - 1)))
            self._request_delay = max(
                self._request_delay, self._base_request_delay * 2
            )
            LOG.warning(
                "rate limited (%s), sleep %.0fs delay→%.1fs",
                action,
                cooldown,
                self._request_delay,
            )
            time.sleep(cooldown)
            raise RateLimitError(
                f"{action}: rate limited (code=9)", code=code, response=data
            )
        if code in (121, 122):
            raise BossHttpError(
                f"{action}: security intercept code={code}. "
                "Need zp_token/bst or browser session.",
                code=code,
                response=data,
            )
        raise BossHttpError(
            f"{action}: {message} (code={code})", code=code, response=data
        )

    def request_json(
        self,
        method: str,
        url: str,
        *,
        action: str = "",
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        referer: str | None = None,
        retries: int = 2,
    ) -> dict[str, Any]:
        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            self._rate_limit_delay()
            kwargs: dict[str, Any] = {
                "headers": self._headers(referer=referer),
                "params": params,
            }
            if json_body is not None:
                kwargs["json"] = json_body
            elif data is not None:
                kwargs["data"] = data
            try:
                resp = self._http.request(method, url, **kwargs)
                self._mark_request()
                self._merge_cookies(resp)
                resp.raise_for_status()
                payload = resp.json()
                if not isinstance(payload, dict):
                    raise BossHttpError(f"{action}: non-object JSON")
                try:
                    return self._handle_payload(payload, action or url)
                except RateLimitError as exc:
                    last_exc = exc
                    if attempt >= retries:
                        raise
                    continue
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_exc = exc
                wait = (2**attempt) + random.uniform(0, 0.5)
                LOG.warning("%s network error: %s; retry in %.1fs", action, exc, wait)
                time.sleep(wait)
        raise BossHttpError(f"{action}: failed after retries: {last_exc}") from last_exc

    def get(
        self,
        url: str,
        *,
        action: str = "",
        params: dict[str, Any] | None = None,
        referer: str | None = None,
    ) -> dict[str, Any]:
        return self.request_json(
            "GET", url, action=action, params=params, referer=referer
        )

    def post_form(
        self,
        url: str,
        data: dict[str, Any],
        *,
        action: str = "",
        referer: str | None = None,
    ) -> dict[str, Any]:
        headers_extra = {"Content-Type": "application/x-www-form-urlencoded"}
        # merge via request_json data=
        self._rate_limit_delay()
        headers = self._headers(referer=referer)
        headers.update(headers_extra)
        resp = self._http.post(url, data=data, headers=headers)
        self._mark_request()
        self._merge_cookies(resp)
        resp.raise_for_status()
        payload = resp.json()
        if not isinstance(payload, dict):
            raise BossHttpError(f"{action}: non-object JSON")
        try:
            return self._handle_payload(payload, action or url)
        except RateLimitError:
            time.sleep(2)
            resp = self._http.post(url, data=data, headers=headers)
            self._mark_request()
            self._merge_cookies(resp)
            payload = resp.json()
            return self._handle_payload(payload, action or url)
