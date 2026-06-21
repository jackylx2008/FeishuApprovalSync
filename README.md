# FeishuApprovalSync

个人使用的飞书审批同步工具，计划用于自动填报质保审批单、查询审批实例，以及下载质保审批单 PDF。

当前阶段已完成项目基础环境和通用日志配置，飞书业务接口尚未实现。

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

## 日志

入口脚本应通过 `logging_config.py` 初始化日志。默认日志目录为项目下的 `log/`，日志会滚动保存并遮蔽常见凭据字段及环境变量中的密钥值。

```python
from logging_config import get_logger, setup_logger

setup_logger(log_level="INFO")
logger = get_logger(__name__)
```

## 安全开关

`config.yaml` 中的 `app.allow_approval_submission` 默认关闭。审批查询流程验证完成前，不应启用真实审批提交。
