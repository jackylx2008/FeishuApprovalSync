"""项目通用日志配置。

默认将日志写入项目根目录的 ``log`` 文件夹，并同时输出到控制台。
日志采用滚动文件，且会自动遮蔽常见凭据字段和当前环境中的敏感值。
"""

from __future__ import annotations

import logging
import os
import platform
import re
import sys
from collections.abc import Iterable
from logging.handlers import RotatingFileHandler
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_LOG_DIR = PROJECT_ROOT / "log"

_SENSITIVE_ENV_NAME_PATTERN = re.compile(
    r"(?:SECRET|TOKEN|PASSWORD|PASSWD|API_KEY|ACCESS_KEY|PRIVATE_KEY|ENCRYPT_KEY)",
    re.IGNORECASE,
)
_SENSITIVE_FIELD_PATTERN = re.compile(
    r"(?i)(\b(?:app_secret|secret|token|password|passwd|api_key|access_key|"
    r"private_key|encrypt_key)\b\s*[:=]\s*)([\"']?)([^\s,;\"'}]+)([\"']?)"
)
_DEFAULT_SECRET_ENV_NAMES = {
    "FEISHU_APP_ID",
    "FEISHU_APP_SECRET",
    "FEISHU_VERIFICATION_TOKEN",
    "FEISHU_ENCRYPT_KEY",
    "FEISHU_USER_ACCESS_TOKEN",
    "FEISHU_TENANT_ACCESS_TOKEN",
}


class RedactingFormatter(logging.Formatter):
    """Formatter that masks configured secret values and credential fields."""

    def __init__(self, fmt: str, secret_values: Iterable[str] = ()) -> None:
        super().__init__(fmt)
        self._secret_values = tuple(
            sorted(
                {value for value in secret_values if value and len(value) >= 4},
                key=len,
                reverse=True,
            )
        )

    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        for secret in self._secret_values:
            rendered = rendered.replace(secret, "***REDACTED***")
        return _SENSITIVE_FIELD_PATTERN.sub(r"\1\2***REDACTED***\4", rendered)


def get_cloudstation_root() -> str:
    """Return the configured CloudStation root for the current platform."""
    explicit_root = os.getenv("CLOUDSTATION_ROOT")
    if explicit_root:
        return str(Path(explicit_root).expanduser())

    system = platform.system().lower()
    platform_env_names = {
        "windows": ("CLOUDSTATION_ROOT_WINDOWS",),
        "darwin": ("CLOUDSTATION_ROOT_MACOS", "CLOUDSTATION_ROOT_DARWIN"),
        "linux": ("CLOUDSTATION_ROOT_LINUX",),
    }
    for env_name in platform_env_names.get(system, ()):
        platform_root = os.getenv(env_name)
        if platform_root:
            return str(Path(platform_root).expanduser())

    return str(Path.home() / "CloudStation")


def resolve_path_markers(path: str | os.PathLike[str]) -> str:
    """Expand user-home and supported CloudStation markers in a path."""
    raw_path = os.fspath(path)
    cloudstation_root = get_cloudstation_root()
    resolved = (
        raw_path.replace("${CLOUDSTATION_ROOT}", cloudstation_root)
        .replace("{CLOUDSTATION_ROOT}", cloudstation_root)
        .replace("%CLOUDSTATION_ROOT%", cloudstation_root)
    )
    return str(Path(resolved).expanduser())


def setup_logger(
    log_level: int | str = logging.INFO,
    log_file: str | os.PathLike[str] | None = None,
    filemode: str = "a",
    *,
    logger_name: str | None = None,
    secret_env_names: Iterable[str] = (),
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> logging.Logger:
    """Configure and return a console-and-file logger.

    ``logger_name=None`` configures the root logger for backward compatibility.
    Existing handlers created by this function are replaced and closed; handlers
    owned by other libraries are left untouched.
    """
    if filemode not in {"a", "w"}:
        raise ValueError("filemode must be 'a' or 'w'")
    if max_bytes <= 0:
        raise ValueError("max_bytes must be greater than zero")
    if backup_count < 0:
        raise ValueError("backup_count must not be negative")

    if log_file is None:
        entry_name = Path(sys.argv[0]).stem or "app"
        log_path = DEFAULT_LOG_DIR / f"{entry_name}.log"
    else:
        log_path = Path(resolve_path_markers(log_file))
        if not log_path.is_absolute():
            log_path = PROJECT_ROOT / log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(logger_name)
    logger.setLevel(_coerce_log_level(log_level))
    _remove_managed_handlers(logger)

    # RotatingFileHandler forces append mode when rotation is enabled. Remove the
    # current file first to provide the documented overwrite behavior.
    if filemode == "w" and log_path.exists():
        log_path.unlink()

    secret_values = _collect_secret_values(secret_env_names)
    formatter = RedactingFormatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        secret_values,
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler._feishu_approval_sync_managed = True  # type: ignore[attr-defined]

    file_handler = RotatingFileHandler(
        log_path,
        mode="a",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler._feishu_approval_sync_managed = True  # type: ignore[attr-defined]

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a logger under the project's active logging configuration."""
    return logging.getLogger(name)


def _collect_secret_values(extra_env_names: Iterable[str]) -> tuple[str, ...]:
    env_names = _DEFAULT_SECRET_ENV_NAMES | {
        name
        for name in os.environ
        if _SENSITIVE_ENV_NAME_PATTERN.search(name)
    }
    env_names.update(extra_env_names)
    return tuple(os.getenv(name, "") for name in env_names)


def _remove_managed_handlers(logger: logging.Logger) -> None:
    for handler in tuple(logger.handlers):
        if getattr(handler, "_feishu_approval_sync_managed", False):
            logger.removeHandler(handler)
            handler.close()


def _coerce_log_level(log_level: int | str) -> int:
    if isinstance(log_level, bool):
        raise TypeError("log_level must be an integer or logging level name")
    if isinstance(log_level, str):
        normalized_level = logging.getLevelName(log_level.upper())
        if isinstance(normalized_level, int):
            return normalized_level
        raise ValueError(f"Unknown log level: {log_level}")
    if isinstance(log_level, int):
        return log_level
    raise TypeError("log_level must be an integer or logging level name")


if __name__ == "__main__":
    demo_logger = setup_logger(log_level=logging.INFO, log_file="log/test_logger.log")
    demo_logger.info("Logger initialized successfully.")
