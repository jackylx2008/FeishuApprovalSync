"""获取用户可见审批定义列表的编排逻辑。"""

from __future__ import annotations

import json
import logging
import secrets
import webbrowser
from pathlib import Path

from .client import FeishuClient
from .config import Settings
from .oauth_callback import wait_for_authorization_code
from .token_store import EnvTokenStore, UserToken


def authorize(client: FeishuClient, settings: Settings, store: EnvTokenStore) -> UserToken:
    state = secrets.token_urlsafe(32)
    authorization_url = client.build_authorization_url(
        settings.oauth_redirect_uri,
        settings.oauth_scopes,
        state,
    )
    print("请在浏览器中完成飞书用户授权：")
    print(authorization_url)
    print("等待授权完成……")
    webbrowser.open(authorization_url)
    code = wait_for_authorization_code(
        settings.oauth_redirect_uri,
        state,
        settings.oauth_callback_timeout,
    )
    token = client.exchange_authorization_code(code, settings.oauth_redirect_uri)
    store.save(token)
    return token


def get_access_token(client: FeishuClient, store: EnvTokenStore) -> UserToken | None:
    token = store.load()
    if token is None:
        return None
    if token.is_valid():
        return token
    if token.refresh_token:
        refreshed = client.refresh_user_token(token.refresh_token)
        store.save(refreshed)
        return refreshed
    return None


def list_and_save_approvals(
    client: FeishuClient,
    settings: Settings,
    token: UserToken,
    logger: logging.Logger,
) -> list[dict[str, object]]:
    approvals = client.list_visible_approvals(
        token.access_token,
        settings.approval_list_path,
        settings.approval_page_size,
    )
    _write_json(settings.approval_output_file, approvals)
    logger.info("获取审批定义完成：count=%d", len(approvals))
    logger.info("审批定义结果已写入：%s", settings.approval_output_file)
    return approvals


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
