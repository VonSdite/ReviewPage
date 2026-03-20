# Review Page

一个独立的 MR 代码检视插件项目，目标是尽量不入侵 `000LLM_Proxy` 现有实现，同时保持相近的后台页面风格，并为后续脚本接入或页面嵌入预留清晰边界。

## 已实现能力

- 明亮 / 暗黑双主题单页后台
- 输入 MR URL，选择 Hub、AI Agent、模型后加入检视队列
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
- 历史任务支持“重来”
  - 基于原任务参数复制出一条新的待检视记录重新排队
- Agent 注册机制
  - 当前内置 `opencode`
- Hub 注册机制
  - 当前内置 `gitlab`

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

默认配置文件是 [config.yaml](/root/.ww/code/002llm/001review_page/config.yaml)。

重点配置项：

- `hubs.gitlab`
  - `web_base_url`: GitLab 页面地址前缀
  - `api_base_url`: GitLab API 地址前缀
  - `private_token`: 访问私有项目时建议配置
  - `clone_url_preference`: `http` 或 `ssh`
- `agents.opencode`
  - `binary`: CLI 命令名
  - `list_models_command`: 获取模型列表的命令参数
  - `review_command`: 单次执行检视任务的命令模板
  - `prompt_template`: 默认会拼成 `/review {review_url}`
  - `model_list`: 当 CLI 无法列模型时的回退模型列表
- `workspace.temp_root`
  - 临时代码目录根路径
- `plugins.modules`
  - 自定义 Agent / Hub 注册模块

## 扩展方式

项目通过注册机制扩展 Agent 和 Hub。

Agent 需要实现 [review_agent.py](/root/.ww/code/002llm/001review_page/src/domain/review_agent.py)：

- `get_model_catalog()`
- `build_review_command()`

Hub 需要实现 [review_hub.py](/root/.ww/code/002llm/001review_page/src/domain/review_hub.py)：

- `supports_url()`
- `resolve_review_target()`

注册入口位于 [registry.py](/root/.ww/code/002llm/001review_page/src/domain/registry.py)。

你可以在配置里声明：

```yaml
plugins:
  modules:
    - custom_integrations.py
```

然后在 `custom_integrations.py` 里导入注册函数并完成注入。

## 后续接入 `000LLM_Proxy` 的建议

- 保持 `001review_page` 独立运行，先作为插件服务验证完整闭环
- 后续如果要无缝插入，可优先考虑两种方式
  - 反向代理挂载到 `000LLM_Proxy` 某个子路径
  - 通过脚本或模板注入，在主项目导航栏中增加跳转入口

这样能先把业务能力独立稳定下来，再决定最终耦合方式。
