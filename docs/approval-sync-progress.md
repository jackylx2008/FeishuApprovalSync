先阅读 docs/approval-sync-progress.md 和当前 git status。应用身份只读权限已获批，请继续获取“工程类-主体质保施工”的全部审批实例。
# 飞书审批同步项目进展记录

更新日期：2026-06-21

## 项目目标

本项目用于个人工作效率提升，计划实现：

1. 获取并识别目标飞书审批定义。
2. 获取“工程类-主体质保施工”审批下的全部审批实例。
3. 根据审批实例编号去重，避免重复处理。
4. 后续实现质保审批单自动填报。
5. 后续实现质保审批单 PDF 下载与归档。

当前阶段只实现和验证只读查询，不执行审批创建、修改、删除或任务处理。

## 已完成工作

### 项目基础环境

- 在项目目录创建了 `.conda` 环境。
- Python 版本固定为 3.12。
- 使用 `environment.yml` 和 `pyproject.toml` 管理依赖。
- 当前主要依赖包括 PyYAML、python-dotenv 和 httpx。
- `.conda/`、日志、运行输出和本地凭据均已加入 `.gitignore`。

### 通用日志

- 修正了项目根目录识别问题。
- 默认日志目录为项目下的 `log/`。
- 支持控制台和滚动文件日志。
- 支持重复初始化而不重复添加本项目 handler。
- 支持遮蔽 App ID、App Secret、Access Token、Refresh Token 等敏感内容。
- 不会主动清除其他库创建的日志 handler。

### 配置与凭据

- 非敏感配置保存在 `config.yaml`。
- 本地凭据保存在 `common.env`。
- `common.env` 不进入 Git。
- `common.env.example` 仅保留空变量示例。

相关环境变量：

```dotenv
FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_USER_ACCESS_TOKEN=
FEISHU_REFRESH_TOKEN=
FEISHU_USER_TOKEN_EXPIRES_AT=
FEISHU_USER_TOKEN_SCOPES=
```

文档中不得记录任何真实 App Secret 或 Token。

## 已验证的飞书认证方式

### 应用身份

使用 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET` 可以成功调用：

```text
POST /open-apis/auth/v3/tenant_access_token/internal
```

并获取 `tenant_access_token`。

该令牌用于只支持应用身份的审批实例接口，但应用必须开通对应的“应用身份”权限。

### 用户身份

“获取用户可见的审批定义列表”接口只接受 `user_access_token`：

```text
GET /open-apis/approval/v4/approvals
```

使用 `tenant_access_token` 调用该接口会返回错误码 `99991663`。

用户令牌配置完成后，真实接口测试已成功：

- HTTP 状态：200。
- 获取到当前用户可发起的审批定义共 68 条。
- 结果写入 `output/approval_definitions.json`。
- `output/` 不进入 Git。

## 目标审批定义

已在用户可见审批定义列表中唯一定位到：

```text
审批名称：工程类-主体质保施工
审批分组：北辰会投
类型：飞书原生审批
```

目标审批的 `approval_code` 已可从本地 `output/approval_definitions.json` 获取。为避免业务标识扩散，本进展文档不记录实际值。

## 当前阻塞

获取目标审批下全部实例需要调用：

```text
GET /open-apis/approval/v4/instances
```

该接口使用 `tenant_access_token`，并要求应用开通以下任一应用身份权限：

- `approval:approval:readonly`（推荐，最小只读权限）
- `approval:approval`
- `approval:instance`

当前真实调用返回：

```text
错误码：99991672
原因：应用尚未开通所需的应用身份权限
```

目前正在申请 `approval:approval:readonly`，权限申请需要管理员审批。权限获批并发布应用版本前，无法继续验证审批实例列表。

## 权限获批后的工作

1. 重新获取 `tenant_access_token`。
2. 使用目标 `approval_code` 调用审批实例列表接口。
3. 按创建时间分段查询，避免接口时间跨度限制。
4. 处理 `page_token` 和 `has_more`，直到拉取全部分页。
5. 使用 `instance_code` 作为唯一键去重。
6. 将实例编号列表写入本地 `output/`。
7. 按实例编号调用详情接口，验证可读取的字段和表单结构。
8. 补充单元测试和真实只读 smoke test。
9. 确认无凭据和业务输出进入 Git 后再提交、推送。

## 幂等与去重约定

飞书审批实例具有唯一的 `instance_code`。后续同步使用该字段作为幂等键：

- 已成功处理的 `instance_code` 不重复处理。
- 失败记录可以保留错误状态并允许重试。
- 不以审批标题、申请人或创建时间作为唯一标识。

## 当前代码入口

获取用户可见审批定义：

```powershell
.\.conda\python.exe list_approvals.py
```

首次或令牌失效后重新授权：

```powershell
.\.conda\python.exe list_approvals.py --authorize
```

默认输出：

```text
output/approval_definitions.json
```

## 测试状态

目前已通过：

- OAuth 授权 URL 与令牌交换单元测试。
- 审批定义列表分页单元测试。
- Flake8 静态检查。
- Python 依赖完整性检查。
- 暂存内容凭据扫描。
- 用户可见审批定义真实接口测试。

审批实例列表真实接口测试需要等待应用身份只读权限获批。

## Git 状态

审批定义列表功能已推送到分支：

```text
codex/list-visible-approvals
```

对应草稿 PR：

```text
https://github.com/jackylx2008/FeishuApprovalSync/pull/1
```

本进展文档创建后尚需根据后续提交安排决定是否加入该 PR。
