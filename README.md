# FeishuApprovalSync

个人使用的飞书审批同步工具，计划用于自动填报质保审批单、查询审批实例，以及下载质保审批单 PDF。

当前阶段已完成项目基础环境、通用日志配置、飞书用户 OAuth 授权和用户可见审批定义列表查询。

## 本地环境

项目使用 Python 3.12，并将 Conda 环境创建在项目目录的 `.conda` 中：

```powershell
conda env create --prefix .\.conda --file environment.yml
conda activate .\.conda
```

## 配置

1. 将 `common.env.example` 复制为 `common.env`。
2. 在 `common.env` 中填写飞书凭据。
3. 在 `config.yaml` 中维护非敏感应用配置。

`common.env`、`.conda/`、日志和运行产物均不会提交到 Git。

## 获取用户可见审批定义

截图中的审批权限属于用户身份权限，因此首次使用需要本人完成 OAuth 授权：

```powershell
python list_approvals.py --authorize
```

按终端提示在飞书页面确认授权。令牌会保存到本地 `common.env`，以后可直接运行：

```powershell
python list_approvals.py
```

结果默认写入 `output/approval_definitions.json`。

飞书开发者后台需要将 `http://127.0.0.1:8765/callback` 添加到应用的 OAuth 重定向 URL 白名单，且应用版本需要包含对应用户身份权限。

## 日志

入口脚本应通过 `logging_config.py` 初始化日志。默认日志目录为项目下的 `log/`，日志会滚动保存并遮蔽常见凭据字段及环境变量中的密钥值。

```python
from logging_config import get_logger, setup_logger

setup_logger(log_level="INFO")
logger = get_logger(__name__)
```

## 安全开关

`config.yaml` 中的 `app.allow_approval_submission` 默认关闭。审批查询流程验证完成前，不应启用真实审批提交。
