"""飞书 OAuth 和审批只读 API 客户端。"""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlencode

import httpx

from .token_store import UserToken


class FeishuApiError(RuntimeError):
    """Raised when Feishu returns an unsuccessful response."""


class FeishuClient:
    def __init__(
        self,
        app_id: str,
        app_secret: str,
        base_url: str,
        timeout: float = 30,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_url = base_url.rstrip("/")
        self.http = httpx.Client(timeout=timeout, transport=transport)

    def close(self) -> None:
        self.http.close()

    def build_authorization_url(
        self,
        redirect_uri: str,
        scopes: tuple[str, ...],
        state: str,
    ) -> str:
        query = urlencode(
            {
                "client_id": self.app_id,
                "response_type": "code",
                "redirect_uri": redirect_uri,
                "scope": " ".join(scopes),
                "state": state,
            }
        )
        return f"{self.base_url}/open-apis/authen/v1/authorize?{query}"

    def exchange_authorization_code(self, code: str, redirect_uri: str) -> UserToken:
        payload = self._post(
            "/open-apis/authen/v2/oauth/token",
            {
                "grant_type": "authorization_code",
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )
        return self._parse_token(payload)

    def refresh_user_token(self, refresh_token: str) -> UserToken:
        payload = self._post(
            "/open-apis/authen/v2/oauth/token",
            {
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        return self._parse_token(payload)

    def list_visible_approvals(
        self,
        access_token: str,
        path: str,
        page_size: int = 100,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page_token = ""
        while True:
            params: dict[str, Any] = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token
            response = self.http.get(
                self.base_url + path,
                params=params,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            payload = self._decode_response(response)
            self._raise_for_api_error(payload, response.status_code)
            data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
            page_items = data.get("items") or data.get("approval_list") or data.get("approvals") or []
            if not isinstance(page_items, list):
                raise FeishuApiError("Approval list response has an unexpected item structure")
            items.extend(item for item in page_items if isinstance(item, dict))
            page_token = str(data.get("page_token") or "")
            if not data.get("has_more") or not page_token:
                return items

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        response = self.http.post(self.base_url + path, json=body)
        payload = self._decode_response(response)
        self._raise_for_api_error(payload, response.status_code)
        return payload

    @staticmethod
    def _decode_response(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise FeishuApiError(f"Feishu returned a non-JSON response: HTTP {response.status_code}") from exc
        if not isinstance(payload, dict):
            raise FeishuApiError("Feishu returned an unexpected response structure")
        return payload

    @staticmethod
    def _raise_for_api_error(payload: dict[str, Any], status_code: int = 200) -> None:
        code = payload.get("code", 0)
        if status_code >= 400 or code not in {None, 0}:
            message = payload.get("msg") or payload.get("error") or "unknown error"
            raise FeishuApiError(f"Feishu API failed: HTTP {status_code}, code={code}, message={message}")

    @staticmethod
    def _parse_token(payload: dict[str, Any]) -> UserToken:
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        access_token = str(data.get("access_token") or "")
        if not access_token:
            raise FeishuApiError("OAuth response did not contain an access token")
        return UserToken(
            access_token=access_token,
            refresh_token=str(data.get("refresh_token") or ""),
            expires_at=time.time() + int(data.get("expires_in") or 0),
            scopes=tuple(str(data.get("scope") or "").split()),
        )
