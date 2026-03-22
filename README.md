# Review Page

一个独立的 MR 代码检视插件项目，目标是保持实现边界清晰、便于独立运行，并为后续脚本接入或页面嵌入预留空间。

## 已实现能力

- 明亮 / 暗黑双主题单页后台
- 输入 MR URL，选择 Hub、AI Agent、模型后加入检视队列
- 模型列表以配置文件为准展示
  - 点击“刷新模型”才会调用 Agent 的列模型命令
  - 刷新成功后会把结果写回 `config.yaml`
- 同一时刻仅执行 1 个检视任务，其他任务按 `pending` 队列排队
- 落库保存检视记录
  - MR 地址
  - Hub
  - Agent
  - 模型
  - 状态
  - 检视结果
  - 执行命令
  - 工作目录
  - 分支信息
- 落库保存执行日志
  - 按行记录 `git clone` 和 Agent 命令输出
- 历史任务支持“重试”
  - 点击后会把 MR 地址自动回填到发起区
  - 如果入口来自详情弹窗，会先关闭弹窗再聚焦回表单
  - Agent 和模型由用户重新选择，再决定是否发起检视
- 当前提供的 Agent
  - `opencode`
- 当前提供的 Hub
  - `gitlab`
- Agent / Hub 的显示名直接使用各自 `id`
  - 不再单独维护 `display_name`

## 技术栈

- Flask
- SQLite
- Jinja2 模板
- 原生 JavaScript

## 快速开始

安装依赖：

```bash
pip install flask gevent requests pyyaml
```

启动服务：

```bash
python main.py
```

默认地址：

```text
http://127.0.0.1:8091
```

## 配置

默认配置文件是 [config.yaml](./config.yaml)。

重点配置项：

- `database.path`
  - 只能写数据目录，例如 `data`
  - 程序会固定在该目录下使用 `review_page.sqlite3`
- `hubs.gitlab`
  - `web_base_url`: GitLab 页面地址前缀
  - `api_base_url`: GitLab API 地址前缀
  - `private_token`: 访问私有项目时建议配置
  - `clone_url_preference`: `http` 或 `ssh`
- `command_shell`
  - 为所有 Agent 命令统一指定外层 shell
  - 适合 Windows 上强制走 Git Bash，例如 `C:/Program Files/Git/bin/bash.exe` + `-lc`
- `agents.opencode`
  - `list_models_command`: 完整列模型命令字符串，例如 `opencode models`
  - `review_command`: 完整检视命令字符串，例如 `opencode run --model "{model}" "/review {review_url}"`
  - `models`: 当前用于页面展示的模型列表，刷新模型后会自动更新这里
- `agents.*` / `hubs.*`
  - 以配置 key 作为唯一标识
  - 前端展示时默认也直接显示这个 key
- `workspace.temp_root`
  - 临时代码目录根路径

## 项目结构

核心目录如下：

- `main.py`
  - 进程入口，解析 `--config`，创建 `Application`
- `src/application`
  - 应用装配、上下文、日志、仓储、服务、控制器初始化
- `src/config`
  - 配置读取与默认值
- `src/domain`
  - Agent / Hub 抽象、领域模型
- `src/integrations`
  - 当前项目里的 Agent 与 Hub 实现
- `src/repositories`
  - SQLite 持久化
- `src/services`
  - 核心业务、后台 worker
- `src/presentation`
  - Flask 路由、Jinja 模板、前端静态资源
- `src/utils`
  - SQLite 连接工厂、子进程执行工具
- `tests`
  - 仓储、服务、Hub、Agent、配置层测试

## 新增 Agent / Hub

如果后续要新增 Agent 或 Hub，维护者直接在代码里增加实现即可。

Agent 需要实现 [review_agent.py](./src/domain/review_agent.py)：

- `get_model_catalog()`
- `build_review_command()`

Hub 需要实现 [review_hub.py](./src/domain/review_hub.py)：

- `supports_url()`
- `resolve_review_target()`

实际接入时，直接在 `src/integrations` 下增加实现文件，并在 [src/integrations/__init__.py](./src/integrations/__init__.py) 里接上即可。

## 后续集成建议

- 保持 `001review_page` 独立运行，先作为插件服务验证完整闭环
- 后续如果要无缝插入，可优先考虑两种方式
  - 反向代理挂载到某个子路径
  - 通过脚本或模板注入，在目标系统导航栏中增加跳转入口

这样能先把业务能力独立稳定下来，再决定最终耦合方式。

## 走读顺序

如果你想把项目完整读透，建议按下面顺序：

1. 入口和装配
   - [main.py](./main.py)
   - [src/application/application.py](./src/application/application.py)
   - [src/application/app_context.py](./src/application/app_context.py)
2. 配置和运行时资源
   - [config.yaml](./config.yaml)
   - [src/config/config_manager.py](./src/config/config_manager.py)
3. 抽象和组织方式
   - [src/domain/review_agent.py](./src/domain/review_agent.py)
   - [src/domain/review_hub.py](./src/domain/review_hub.py)
   - [src/domain/review_models.py](./src/domain/review_models.py)
   - [src/domain/registry.py](./src/domain/registry.py)
   - [src/integrations/__init__.py](./src/integrations/__init__.py)
4. 当前实现
   - [src/integrations/agents/opencode_agent.py](./src/integrations/agents/opencode_agent.py)
   - [src/integrations/hubs/gitlab_hub.py](./src/integrations/hubs/gitlab_hub.py)
5. 持久化和后台执行
   - [src/repositories/review_repository.py](./src/repositories/review_repository.py)
   - [src/services/review_service.py](./src/services/review_service.py)
   - [src/services/review_queue_worker.py](./src/services/review_queue_worker.py)
   - [src/utils/database.py](./src/utils/database.py)
   - [src/utils/process.py](./src/utils/process.py)
6. Web 层和前端
   - [src/presentation/web_controller.py](./src/presentation/web_controller.py)
   - [src/presentation/app_factory.py](./src/presentation/app_factory.py)
   - [src/presentation/templates/base_page.html](./src/presentation/templates/base_page.html)
   - [src/presentation/templates/review.html](./src/presentation/templates/review.html)
   - `src/presentation/static/css/review-base.css`
   - `src/presentation/static/css/review.css`
   - `src/presentation/static/js/review.js`
7. 测试
   - [tests/test_config_manager.py](./tests/test_config_manager.py)
   - [tests/test_review_repository.py](./tests/test_review_repository.py)
   - [tests/test_review_service.py](./tests/test_review_service.py)
   - [tests/test_opencode_agent.py](./tests/test_opencode_agent.py)
   - [tests/test_gitlab_hub.py](./tests/test_gitlab_hub.py)

## 实现细节总览

### 1. 启动链路

- `python main.py`
  - 在 [main.py](./main.py) 里解析命令行参数，默认读取项目根目录的 `config.yaml`
- `Application(config_path)`
  - 在 [src/application/application.py](./src/application/application.py) 中完成整套依赖装配
  - 装配顺序是：配置 -> 日志 -> 上下文 -> 仓储 -> 集成注册 -> 服务 -> 控制器 -> 退出钩子
- `run()`
  - 优先用 `gevent.pywsgi.WSGIServer`
  - 如果环境里没装 `gevent`，回退到 Flask 自带开发服务器

### 2. 配置模型

- [src/config/config_manager.py](./src/config/config_manager.py) 不再维护整份 `DEFAULT_CONFIG`
- 配置文件按原样读取，各 getter 自己负责默认值
- `database.path` 只表示目录，最终数据库固定为 `database.path/review_page.sqlite3`
- `agents.default` 和 `hubs.default` 决定页面初始默认选择项
- `agents.<id>` / `hubs.<id>` 的 key 本身就是系统标识，也直接作为页面显示名

### 3. Agent / Hub 组织方式

- [src/domain/registry.py](./src/domain/registry.py) 维护两个全局注册表
  - `_AGENT_FACTORIES`
  - `_HUB_FACTORIES`
- 当前项目里的实现由 [src/integrations/__init__.py](./src/integrations/__init__.py) 接入
- `Application._setup_integrations()` 会根据配置里的 `enabled` 过滤出真正启用的 Agent / Hub 实例

### 4. 当前 Agent

- [src/integrations/agents/opencode_agent.py](./src/integrations/agents/opencode_agent.py)
- 关键职责：
  - 平时从配置里的 `models` 读取前端展示模型
  - 点击刷新模型时执行 `list_models_command`，并把结果写回配置文件
  - 根据 `review_command` 生成一次性检视命令
- `get_model_catalog()`
  - 不主动打命令，只返回当前配置里的模型列表
- `refresh_model_catalog()`
  - 主动执行列模型命令，并持久化刷新结果
- `build_review_command()`
  - 会把 `{model}`、`{review_url}`、`{workspace_dir}` 填进命令字符串，再按 shell 风格拆分成参数数组

### 5. 当前 Hub

- [src/integrations/hubs/gitlab_hub.py](./src/integrations/hubs/gitlab_hub.py)
- 关键职责：
  - 校验 MR URL 是否属于当前 GitLab 域名
  - 解析 MR 地址中的项目路径和 IID
  - 调 GitLab API 读取 MR 信息和仓库信息
  - 产出 `MergeRequestTarget`
- `MergeRequestTarget` 在 [src/domain/review_models.py](./src/domain/review_models.py) 中定义
  - 包含 `repo_url`、`source_branch`、`target_branch`、`title`、`author_name` 等执行检视所需信息

### 6. 数据库模型

- [src/repositories/review_repository.py](./src/repositories/review_repository.py)
- 两张表：
  - `review_records`
    - 任务主表
    - 核心字段有：`mr_url`、`hub_id`、`agent_id`、`model_id`、`status`、`runtime_state`
    - 还会记录命令、工作目录、结果、错误、分支、标题、作者、时间戳
  - `review_logs`
    - 按行保存执行日志
    - 使用 `(review_id, sequence)` 保证单任务内日志有序
- 状态语义：
  - `status`
    - `pending` / `completed` / `failed`
  - `runtime_state`
    - `queued` / `running` / `finished`
- 队列顺序按 `created_at ASC, id ASC`

### 7. 后台执行模型

- [src/services/review_queue_worker.py](./src/services/review_queue_worker.py)
  - 常驻后台线程
  - 单线程串行执行，天然保证“同一时刻只跑一个任务”
  - 新任务创建后会 `wake_up()`
  - 启动时会先把意外中断遗留的 `running` 任务重置回 `queued`
- [src/services/review_service.py](./src/services/review_service.py)
  - 是整个项目的业务核心
  - 负责：
    - 生成页面元数据
    - 创建任务
    - 分页查询任务
    - 查询详情
    - 执行下一个任务

### 8. 单个检视任务的执行过程

在 [src/services/review_service.py](./src/services/review_service.py) 的 `_execute_review()` 中，顺序如下：

1. 从队列中取出一条 `pending + queued` 任务
2. 根据 `hub_id` / `agent_id` 找到运行时实例
3. 在 `workspace.temp_root` 下创建临时工作目录
4. 调 Hub 解析 MR，拿到仓库地址和分支
5. 把命令、仓库、分支、标题、作者等上下文写回数据库
6. 执行 `git clone --depth 1 --branch <source_branch>`
7. 在临时仓库目录里执行 Agent 命令
8. 把所有 stdout/stderr 合并输出逐行写入 `review_logs`
9. 成功则 `mark_review_completed()`，失败则 `mark_review_failed()`
10. 无论成功失败，都会删除整个临时目录

这里实际执行外部命令用的是 [src/utils/process.py](./src/utils/process.py)：

- `format_command()`
  - 用于生成可读的命令行字符串，写入数据库和日志
- `stream_command()`
  - 启动子进程
  - 实时消费 stdout
  - 按行回调给 `append_log()`
  - 最终返回退出码和完整输出

### 9. Web API 层

- [src/presentation/web_controller.py](./src/presentation/web_controller.py)
- 页面和接口如下：
  - `GET /`
    - 返回主页面
  - `GET /api/meta`
    - 返回 Hub / Agent / 模型元数据和默认选择项
  - `POST /api/agents/<agent_id>/models/refresh`
    - 执行列模型命令，并把结果写回配置文件
  - `GET /api/reviews`
    - 返回分页列表
  - `POST /api/reviews`
    - 创建新任务
  - `GET /api/reviews/<id>`
    - 返回详情和完整日志

### 10. 前端页面实现

- 模板在 [src/presentation/templates/review.html](./src/presentation/templates/review.html)
  - 上半部分是发起检视表单
  - 下半部分是分页表格
  - 详情通过 modal 弹窗展示
- 页面骨架在 [src/presentation/templates/base_page.html](./src/presentation/templates/base_page.html)
  - 注入主题启动脚本、基础样式和业务脚本
- 前端行为在 `src/presentation/static/js/review.js`
  - 初始化时先拉 `/api/meta` 和 `/api/reviews`
  - 模型选择旁边提供“刷新模型”按钮，点击后会刷新并重载当前 Agent 的模型列表
  - 表单提交走 `POST /api/reviews`
  - 表格支持手动刷新和可开关自动刷新
  - 分页器支持上一页、下一页、跳页、每页条数切换
  - 点击“查看详情”会拉详情接口并打开弹窗
  - 点击“重试”会把 MR 地址回填到上方表单；如果来自详情弹窗，会先关闭弹窗再聚焦回表单
- 样式在：
  - `src/presentation/static/css/review-base.css`
  - `src/presentation/static/css/review.css`

### 11. 测试覆盖点

- [tests/test_config_manager.py](./tests/test_config_manager.py)
  - 配置默认值、数据库目录语义、模型列表回写
- [tests/test_review_repository.py](./tests/test_review_repository.py)
  - 建任务、认领任务、写日志、完成任务、分页
- [tests/test_review_service.py](./tests/test_review_service.py)
  - 分页元数据、失败清理临时目录
- [tests/test_opencode_agent.py](./tests/test_opencode_agent.py)
  - 配置模型读取、刷新模型、命令构造
- [tests/test_gitlab_hub.py](./tests/test_gitlab_hub.py)
  - GitLab MR 解析、域名校验

## 推荐的实际走读方法

如果你想真的把细节吃透，而不是只看概览，我建议你这样读：

1. 先读 [main.py](./main.py) 和 [src/application/application.py](./src/application/application.py)，把启动顺序记住。
2. 再读 [config.yaml](./config.yaml) 和 [src/config/config_manager.py](./src/config/config_manager.py)，搞清楚每个运行时资源从哪来。
3. 接着读 [src/domain/registry.py](./src/domain/registry.py)、[src/domain/review_agent.py](./src/domain/review_agent.py)、[src/domain/review_hub.py](./src/domain/review_hub.py)，理解扩展点边界。
4. 然后读当前实现 [src/integrations/agents/opencode_agent.py](./src/integrations/agents/opencode_agent.py) 和 [src/integrations/hubs/gitlab_hub.py](./src/integrations/hubs/gitlab_hub.py)，搞清楚“模型列表怎么来”“MR 怎么解析”。
5. 之后读 [src/repositories/review_repository.py](./src/repositories/review_repository.py)，先把数据库状态机和表结构吃透。
6. 再读 [src/services/review_service.py](./src/services/review_service.py) 和 [src/services/review_queue_worker.py](./src/services/review_queue_worker.py)，这是业务最核心的部分。
7. 最后读 [src/presentation/web_controller.py](./src/presentation/web_controller.py)、[src/presentation/templates/review.html](./src/presentation/templates/review.html)、`src/presentation/static/js/review.js`，把接口和页面行为连起来。
8. 每读完一层，就去对照对应测试文件，看作者期待的行为是什么。
