# Review Page

一个面向 Merge Request 检视流程的轻量 Web 页面，负责把 GitLab MR、配置驱动的 Agent 命令和后台串行队列串起来，并提供检视中心与系统设置页，用于维护 Agent、平台、默认模型和默认平台/Agent。

## 当前能力

- 检视中心
  - 提交 MR 检视任务
  - 为平台、Agent、模型设置显式默认值
  - 刷新选中 Agent 的模型列表
  - 查看队列、历史记录、执行日志、最终结果
  - 从历史详情一键重试并回填表单
- 系统设置
  - 维护 Agent 列表和平台列表
  - 新增、编辑、重命名、删除 Agent / 平台
  - 为 Agent 设置默认模型
  - 为 Agent / 平台设置或清空显式默认
  - 在 Agent 编辑弹窗里拉取模型预览、筛选并应用到当前编辑内容
- 后台执行
  - 单线程串行消费待执行任务
  - 启动时会把“pending + running”的遗留任务重置回队列
  - 克隆 MR 源分支代码后，在临时工作目录中执行 Agent 检视命令
- 配置驱动
  - Agent、平台、默认项都持久化在 `config.yaml`
  - Review 记录和日志存储在 SQLite

## 运行流程

1. 前端提交 `mr_url`、`hub_id`、`agent_id`、`model_id`。
2. 后端把任务写入 SQLite 队列，状态为 `pending/queued`。
3. 后台 worker 轮询队列，依次领取任务并标记为 `pending/running`。
4. Hub 解析 MR 地址，获取仓库地址、源分支、目标分支、标题、作者等信息。
5. 服务端执行 `git clone --depth 1 --branch <source_branch>` 拉取代码。
6. Agent 根据 `review_command` 生成实际命令，在仓库目录中执行检视。
7. 结果和日志写回数据库，任务最终变为 `completed/finished` 或 `failed/finished`。

## 快速开始

### 依赖

- Python
- `git`
- 可用的 Agent CLI
- Python 包：`flask`、`gevent`、`requests`、`pyyaml`

安装示例：

```bash
pip install flask gevent requests pyyaml
```

### 启动

项目要求提供配置文件；仓库根目录自带 `config.yaml` 示例。

```bash
python main.py --config config.yaml
```

当前仓库示例配置默认监听：

```text
http://127.0.0.1:31944
```

如果配置里省略 `server.host` / `server.port`，代码默认使用 `127.0.0.1:8091`。

## 页面说明

### 检视中心

- 表单字段为 `MR 地址`、`平台名称`、`Agent 名称`、`模型`。
- 前端会优先选中显式默认值；如果没有显式默认，只会临时预选第一个可用项，页面不会显示默认 tag 或星标。
- “设为默认”只代表写入配置中的显式默认，不代表页面当前预选。
- “更新模型”会刷新当前已存在 Agent 的模型列表，并把结果写回 `config.yaml`。
- 记录列表支持分页、自动刷新、详情弹窗和重试。

### 系统设置

- Agent 列表会显示：
  - Agent 名称
  - 默认模型
  - 模型数
  - 拉模型命令
  - 检视命令
- 平台列表会显示：
  - 平台名称
  - 类型
  - 网页地址
  - API 地址
- 编辑弹窗支持重命名；保存成功后会直接关闭弹窗。
- Agent 弹窗中的“拉取模型”只要求填写“拉模型命令”，不要求先填 Agent 名称。
- Agent 弹窗里拉取到的模型先进入预览选择弹窗；选中后只会应用到当前编辑器，真正持久化要等点“保存/创建”。

## 配置说明

说明：

- UI 文案里展示的是“Agent 名称 / 平台名称”，但配置键和 API 字段仍然使用 `agent_id` / `hub_id`。
- 所有相对路径都相对于项目根目录解析。

### 顶层配置

| 键 | 说明 |
| --- | --- |
| `server.host` | 监听地址，缺省为 `127.0.0.1` |
| `server.port` | 监听端口，缺省为 `8091` |
| `database.path` | SQLite 数据目录，不是 sqlite 文件路径；实际数据库文件固定为 `<database.path>/review_page.sqlite3` |
| `logging.path` | 日志目录 |
| `logging.level` | 日志级别，缺省 `INFO` |
| `workspace.temp_root` | 任务执行时的临时工作目录根路径 |
| `queue.poll_interval_seconds` | 队列轮询间隔，最小会按 `0.5` 秒处理 |
| `command_shell` | 全局 Agent 命令执行 shell，可写字符串或映射 |
| `hubs.default` | 显式默认平台，可为空 |
| `agents.default` | 显式默认 Agent，可为空 |

### `command_shell`

`command_shell` 只支持全局配置，不支持在单个 Agent 下单独配置。

支持两种写法：

```yaml
command_shell: bash
```

```yaml
command_shell:
  executable: bash
  args:
  - -lc
```

行为说明：

- 写成字符串时，等价于 `executable=<该字符串>` 且默认 `args=["-lc"]`
- 写成映射但未提供 `args` 时，也会默认补成 `["-lc"]`
- 只有在你显式写了 `args` 时，才完全以你写的参数为准

因此：

```yaml
command_shell: bash
```

最终效果接近：

```bash
bash -lc "<实际命令>"
```

### Agent 配置

```yaml
agents:
  opencode:
    list_models_command: opencode models
    review_command: opencode run --model "{model}" "/review {review_url}"
    models:
    - opencode/big-pickle
    default_model: opencode/big-pickle
    extra_env:
      HTTP_PROXY: http://127.0.0.1:7890
  default: opencode
```

字段说明：

| 键 | 必填 | 说明 |
| --- | --- | --- |
| `list_models_command` | 是 | 拉取模型列表的命令 |
| `review_command` | 是 | 执行检视的命令模板 |
| `models` | 否 | 当前持久化的模型列表 |
| `default_model` | 否 | 当前 Agent 的显式默认模型；必须出现在 `models` 中 |
| `extra_env` | 否 | 执行 Agent 命令时追加的环境变量对象 |

补充说明：

- `review_command` 支持占位符：`{model}`、`{review_url}`、`{workspace_dir}`
- `list_models_command` 的输出按“每行一个模型 ID”解析
- 空行会忽略
- 以 `Available models` 开头的标题行会忽略
- 每行前缀的 `-` 或 `*` 会被剥掉再入库

### 平台配置

当前内置且已注册的 Hub 类型只有 `gitlab`。

```yaml
hubs:
  gitlab_public:
    type: gitlab
    web_base_url: https://gitlab.example.com
    api_base_url: https://gitlab.example.com/api/v4
    private_token: null
    clone_url_preference: http
    verify_ssl: true
    timeout_seconds: 20
  default: gitlab_public
```

字段说明：

| 键 | 必填 | 说明 |
| --- | --- | --- |
| `type` | 是 | 平台类型，当前仅支持 `gitlab` |
| `web_base_url` | 否 | 用于限制平台可接受的 MR host；为空时不做 host 限制 |
| `api_base_url` | `gitlab` 时必填 | GitLab API 基地址 |
| `private_token` | 否 | GitLab 私有 token |
| `clone_url_preference` | 否 | `http` 或 `ssh`，默认 `http` |
| `verify_ssl` | 否 | 是否校验证书，GitLab Hub 读取时缺省按 `true` 处理 |
| `timeout_seconds` | 否 | API 请求超时；系统设置页面要求填写整数 |

## 默认值与预选逻辑

- `agents.default` 和 `hubs.default` 表示“显式默认”。
- 没有显式默认时：
  - 页面不显示默认 tag
  - 下拉选项不显示默认星标
  - 页面为了便于操作，仍可能临时预选第一个可用项
- 创建检视任务时，后端不会再自动 fallback 到第一个平台 / Agent / 模型；请求必须显式传入这三个值。
- 删除当前默认 Agent / 平台时，会直接清空默认，不会自动切换到剩余第一个。

## HTTP API

所有写接口失败时统一返回：

```json
{"error": "具体错误信息"}
```

### 元数据与设置

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/` | 渲染页面 |
| `GET` | `/api/meta` | 检视中心所需元数据：Agent、平台、显式默认值 |
| `GET` | `/api/settings` | 系统设置页所需数据：Agent、平台、显式默认值、`hub_types` |

### Agent 相关

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/agents/<agent_id>/models/fetch` | 按当前编辑内容预览拉取模型，不直接写配置 |
| `POST` | `/api/agents/<agent_id>/models/refresh` | 刷新已存在 Agent 的模型并写回配置 |
| `POST` | `/api/agents/<agent_id>/default-model` | 设置 Agent 默认模型 |
| `POST` | `/api/settings/agents/<agent_id>` | 新增或保存 Agent；支持重命名 |
| `DELETE` | `/api/settings/agents/<agent_id>` | 删除 Agent |
| `POST` | `/api/settings/agents/<agent_id>/default` | 设置显式默认 Agent |

常用请求体：

```json
{
  "agent_id": "opencode",
  "list_models_command": "opencode models",
  "review_command": "opencode run --model \"{model}\" \"/review {review_url}\"",
  "models": ["opencode/big-pickle"],
  "default_model": "opencode/big-pickle",
  "extra_env": {
    "HTTP_PROXY": "http://127.0.0.1:7890"
  }
}
```

`/api/agents/<agent_id>/models/fetch` 预览拉取时，只要求 `list_models_command`；`review_command` 可为空。

### 平台相关

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/settings/hubs/<hub_id>` | 新增或保存平台；支持重命名 |
| `DELETE` | `/api/settings/hubs/<hub_id>` | 删除平台 |
| `POST` | `/api/settings/hubs/<hub_id>/default` | 设置显式默认平台 |

常用请求体：

```json
{
  "hub_id": "gitlab_public",
  "type": "gitlab",
  "web_base_url": "https://gitlab.example.com",
  "api_base_url": "https://gitlab.example.com/api/v4",
  "private_token": "",
  "clone_url_preference": "http",
  "verify_ssl": true,
  "timeout_seconds": 20
}
```

### 检视任务

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/reviews?page=1&page_size=50` | 分页获取检视记录，`page_size` 最大 `200` |
| `POST` | `/api/reviews` | 创建检视任务 |
| `GET` | `/api/reviews/<review_id>` | 获取检视详情和完整日志 |

创建任务请求体：

```json
{
  "mr_url": "https://gitlab.example.com/group/project/-/merge_requests/123",
  "hub_id": "gitlab_public",
  "agent_id": "opencode",
  "model_id": "opencode/big-pickle"
}
```

## 项目结构

```text
.
├─ main.py
├─ config.yaml
├─ src
│  ├─ application
│  ├─ config
│  ├─ domain
│  ├─ integrations
│  │  ├─ agents
│  │  └─ hubs
│  ├─ presentation
│  │  ├─ static
│  │  └─ templates
│  ├─ repositories
│  ├─ services
│  └─ utils
└─ tests
```

目录职责：

- `src/application`
  - 应用装配、日志初始化、worker 启停
- `src/config`
  - `config.yaml` 读取、路径解析和持久化
- `src/integrations/agents`
  - 配置驱动 Agent，负责模型拉取和命令构造
- `src/integrations/hubs`
  - 平台实现；当前仅内置 GitLab Hub
- `src/presentation`
  - Flask 路由、Jinja 模板、前端静态资源
- `src/repositories`
  - SQLite 读写和 review/log 持久化
- `src/services`
  - 检视编排、设置管理、后台队列 worker
- `tests`
  - 覆盖配置、Agent、Hub、仓库、服务和进程相关行为

## 开发与测试

运行全部测试：

```bash
python -m pytest tests
```

本地开发建议至少关注：

- `tests/test_config_manager.py`
- `tests/test_config_driven_agent.py`
- `tests/test_gitlab_hub.py`
- `tests/test_review_repository.py`
- `tests/test_review_service.py`

## 当前限制

- 当前仅内置 `gitlab` Hub。
- 队列执行为单线程串行模式。
- 删除已被待执行或执行中任务引用的 Agent / 平台时，没有额外的前置保护；已有记录会保留原引用，后续任务可能失败。
- `command_shell` 目前只支持全局配置，不支持按 Agent 单独覆盖。
