"""Feishu client unit tests without external API calls."""

from __future__ import annotations

import json
import time
import unittest
from urllib.parse import parse_qs, urlparse

import httpx

from feishu_approval_sync.client import FeishuClient


class FeishuClientTests(unittest.TestCase):
    def test_authorization_url_and_code_exchange(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            self.assertEqual(body["grant_type"], "authorization_code")
            self.assertEqual(body["code"], "authorization-code")
            self.assertNotIn("authorization-code", request.url.query.decode())
            return httpx.Response(
                200,
                json={
                    "access_token": "access-secret",
                    "refresh_token": "refresh-secret",
                    "expires_in": 7200,
                    "scope": "serviceaccount:approval:approvals:read",
                },
            )

        client = self._client(handler)
        try:
            url = client.build_authorization_url(
                "http://127.0.0.1:8765/callback",
                ("scope-a",),
                "state-value",
            )
            query = parse_qs(urlparse(url).query)
            self.assertEqual(query["scope"], ["scope-a"])
            self.assertEqual(query["state"], ["state-value"])
            token = client.exchange_authorization_code(
                "authorization-code",
                "http://127.0.0.1:8765/callback",
            )
        finally:
            client.close()
        self.assertEqual(token.access_token, "access-secret")
        self.assertGreater(token.expires_at, time.time())

    def test_approval_list_paginates(self) -> None:
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            self.assertEqual(request.headers["Authorization"], "Bearer secret-token")
            if calls == 1:
                return httpx.Response(
                    200,
                    json={"code": 0, "data": {"items": [{"approval_code": "A"}], "has_more": True, "page_token": "next"}},
                )
            return httpx.Response(
                200,
                json={"code": 0, "data": {"items": [{"approval_code": "B"}], "has_more": False}},
            )

        client = self._client(handler)
        try:
            approvals = client.list_visible_approvals("secret-token", "/open-apis/approval/v4/approvals")
        finally:
            client.close()
        self.assertEqual([item["approval_code"] for item in approvals], ["A", "B"])

    @staticmethod
    def _client(handler: object) -> FeishuClient:
        return FeishuClient(
            "app-id",
            "app-secret",
            "https://open.feishu.cn",
            transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
        )


if __name__ == "__main__":
    unittest.main()
