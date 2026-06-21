"""加载本地环境变量和项目配置。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    project_root: Path
    env_file: Path
    app_id: str
    app_secret: str
    base_url: str
    timeout: float
    log_level: str
    oauth_scopes: tuple[str, ...]
    oauth_redirect_uri: str
    oauth_callback_timeout: int
    approval_list_path: str
    approval_page_size: int
    approval_output_file: Path


def load_settings(project_root: Path | None = None) -> Settings:
    """Load ``common.env`` and ``config.yaml`` with basic validation."""
    root = (project_root or Path.cwd()).resolve()
    env_file = root / "common.env"
    config_file = root / "config.yaml"
    load_dotenv(env_file, override=False)

    raw = _load_yaml(config_file)
    app = _mapping(raw, "app")
    feishu = _mapping(raw, "feishu")
    credentials = _mapping(feishu, "credentials")
    oauth = _mapping(feishu, "oauth")
    approval = _mapping(feishu, "approval")

    app_id = _required_env(str(credentials.get("app_id_env", "FEISHU_APP_ID")))
    app_secret = _required_env(str(credentials.get("app_secret_env", "FEISHU_APP_SECRET")))
    scopes = tuple(str(scope) for scope in oauth.get("scopes", ()))
    if not scopes:
        raise ValueError("feishu.oauth.scopes must not be empty")

    output_file = root / str(approval.get("output_file", "output/approval_definitions.json"))
    return Settings(
        project_root=root,
        env_file=env_file,
        app_id=app_id,
        app_secret=app_secret,
        base_url=str(feishu.get("base_url", "https://open.feishu.cn")).rstrip("/"),
        timeout=float(feishu.get("request_timeout_seconds", 30)),
        log_level=str(app.get("log_level", "INFO")),
        oauth_scopes=scopes,
        oauth_redirect_uri=str(oauth.get("redirect_uri", "http://127.0.0.1:8765/callback")),
        oauth_callback_timeout=int(oauth.get("callback_timeout_seconds", 300)),
        approval_list_path=str(approval.get("list_path", "/open-apis/approval/v4/approvals")),
        approval_page_size=int(approval.get("page_size", 100)),
        approval_output_file=output_file,
    )


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(content, dict):
        raise ValueError(f"Configuration root must be a mapping: {path}")
    return content


def _mapping(value: dict[str, Any], key: str) -> dict[str, Any]:
    child = value.get(key, {})
    if not isinstance(child, dict):
        raise ValueError(f"Configuration section must be a mapping: {key}")
    return child


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Required environment variable is missing: {name}")
    return value
