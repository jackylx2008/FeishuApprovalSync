"""在本地 common.env 中维护 OAuth 用户令牌。"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values, set_key


@dataclass(frozen=True)
class UserToken:
    access_token: str
    refresh_token: str
    expires_at: float
    scopes: tuple[str, ...]

    def is_valid(self, slack_seconds: int = 300) -> bool:
        return bool(self.access_token) and self.expires_at > time.time() + slack_seconds


class EnvTokenStore:
    """Read and atomically update token-related keys through python-dotenv."""

    def __init__(self, env_file: Path) -> None:
        self.env_file = env_file

    def load(self) -> UserToken | None:
        values = dotenv_values(self.env_file)
        access_token = values.get("FEISHU_USER_ACCESS_TOKEN") or ""
        refresh_token = values.get("FEISHU_REFRESH_TOKEN") or ""
        expires_at_raw = values.get("FEISHU_USER_TOKEN_EXPIRES_AT") or "0"
        scopes_raw = values.get("FEISHU_USER_TOKEN_SCOPES") or ""
        if not access_token and not refresh_token:
            return None
        try:
            expires_at = float(expires_at_raw)
        except ValueError:
            expires_at = 0
        return UserToken(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            scopes=tuple(scopes_raw.split()),
        )

    def save(self, token: UserToken) -> None:
        self.env_file.touch(exist_ok=True)
        updates = {
            "FEISHU_USER_ACCESS_TOKEN": token.access_token,
            "FEISHU_REFRESH_TOKEN": token.refresh_token,
            "FEISHU_USER_TOKEN_EXPIRES_AT": str(int(token.expires_at)),
            "FEISHU_USER_TOKEN_SCOPES": " ".join(token.scopes),
        }
        for key, value in updates.items():
            set_key(str(self.env_file), key, value, quote_mode="auto")
            os.environ[key] = value
