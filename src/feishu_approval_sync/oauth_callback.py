"""用于单用户 OAuth 的本机回调接收器。"""

from __future__ import annotations

import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse


class OAuthCallbackError(RuntimeError):
    """Raised when the local OAuth callback is invalid or times out."""


def wait_for_authorization_code(redirect_uri: str, expected_state: str, timeout: int) -> str:
    parsed = urlparse(redirect_uri)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("OAuth redirect_uri must use local HTTP host 127.0.0.1 or localhost")
    if not parsed.port:
        raise ValueError("OAuth redirect_uri must include a port")

    result: dict[str, str] = {}
    callback_path = parsed.path or "/"

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            request = urlparse(self.path)
            if request.path != callback_path:
                self.send_error(404)
                return
            query = parse_qs(request.query)
            result["code"] = (query.get("code") or [""])[0]
            result["state"] = (query.get("state") or [""])[0]
            result["error"] = (query.get("error") or [""])[0]
            body = "飞书授权结果已收到，可以关闭此页面。"
            encoded = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = HTTPServer((parsed.hostname, parsed.port), CallbackHandler)
    server.timeout = 1
    deadline = time.monotonic() + timeout
    try:
        while time.monotonic() < deadline and not result:
            server.handle_request()
    finally:
        server.server_close()

    if not result:
        raise OAuthCallbackError("等待飞书用户授权超时")
    if result.get("error"):
        raise OAuthCallbackError(f"飞书用户拒绝或取消授权：{result['error']}")
    if result.get("state") != expected_state:
        raise OAuthCallbackError("OAuth state 校验失败")
    if not result.get("code"):
        raise OAuthCallbackError("飞书回调未包含 authorization code")
    return result["code"]
