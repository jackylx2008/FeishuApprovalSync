"""获取当前用户可见的飞书审批定义列表。

配置文件：
  common.env 保存 App ID、App Secret 和 OAuth 用户令牌。
  config.yaml 保存接口地址、授权范围、日志级别和输出位置。

首次授权：
  python list_approvals.py --authorize

后续运行：
  python list_approvals.py

输出：
  默认写入 output/approval_definitions.json，日志写入 log/list_approvals.log。
"""

from __future__ import annotations

import argparse
import sys

from feishu_approval_sync.approval_flow import authorize, get_access_token, list_and_save_approvals
from feishu_approval_sync.client import FeishuApiError, FeishuClient
from feishu_approval_sync.config import load_settings
from feishu_approval_sync.oauth_callback import OAuthCallbackError
from feishu_approval_sync.token_store import EnvTokenStore
from logging_config import get_logger, setup_logger


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorize", action="store_true", help="重新执行飞书用户 OAuth 授权")
    args = parser.parse_args()

    try:
        settings = load_settings()
        setup_logger(log_level=settings.log_level)
        logger = get_logger(__name__)
        store = EnvTokenStore(settings.env_file)
        client = FeishuClient(
            app_id=settings.app_id,
            app_secret=settings.app_secret,
            base_url=settings.base_url,
            timeout=settings.timeout,
        )
        try:
            token = authorize(client, settings, store) if args.authorize else get_access_token(client, store)
            if token is None:
                logger.error("尚未完成用户授权，请运行：python list_approvals.py --authorize")
                return 2
            list_and_save_approvals(client, settings, token, logger)
            return 0
        finally:
            client.close()
    except (FeishuApiError, FileNotFoundError, OAuthCallbackError, OSError, ValueError) as exc:
        get_logger(__name__).error("执行失败：%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
