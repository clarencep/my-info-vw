# CONTRIBUTING.md - 项目约定与贡献指南

## 架构

```
CLI 入口 (info-check.sh → info-check.py)
  └─ Workflow (src/workflows/check.py, LangGraph)
       ├─ ParseAgent      — 解析消息，提取声明和实体
       ├─ SearchQueryAgent — 生成搜索查询
       ├─ SearchAggregator — 多源搜索聚合
       │    ├─ Tavily (src/search/providers/tavily_cli.py)
       │    ├─ Jina   (src/search/providers/jina_cli.py)
       │    ├─ Brave  (src/search/providers/brave_cli.py)
       │    ├─ Bing   (src/search/providers/bing_cli.py)
       │    └─ Baidu  (src/search/providers/baidu_cli.py)
       ├─ VerifierAgent   — 验证搜索结果
       └─ SynthesizerAgent — 生成综合报告

LLM 层:
  src/llm/manager.py — 多 Provider 自动 fallback
  支持 YAML 多模型配置 + .env 单模型回退

前端:
  webapp/ — Next.js 应用

配置:
  config/llm.yaml   — LLM Provider 配置
  config/search.yaml — 搜索 Provider 配置
```

## 配置约定

### 配置路径解析

所有配置文件的路径通过 `src/config/path_utils.py` 统一管理：

- **默认路径**：`<PROJECT_ROOT>/config/<filename>`
- **自定义路径**：设置环境变量 `MY_INFO_VW_CONFIG_DIR` 后，所有配置从该目录查找
- **回退行为**：若 YAML 配置不存在，LLM Manager 自动回退到 `.env` 单模型模式

新增配置文件时，请使用 `src/config/path_utils.get_config_root()` 获取配置根目录，不要硬编码相对路径。

### 添加新的搜索 Provider

1. 在 `src/search/providers/` 下新建 CLI 脚本，遵循 `protocol.py` 定义的 JSONL 协议
2. 在 `config/search.yaml` 中添加 Provider 定义
3. 通过环境变量传递 API Key（在 `env` 字段中使用 `${VAR_NAME}` 语法）

### 添加新的 LLM Provider

1. 编辑 `config/llm.yaml`，在 `providers` 列表中添加条目
2. 将 API Key 存放在环境变量中，通过 `api_key_env` 引用
3. 在 `fallback_order` 中安排优先级

## 编码规范

- Python >= 3.10
- 使用 `uv` 管理依赖
- 代码风格：遵循 Ruff（`ruff check` / `ruff format`）
- 类型提示：鼓励使用，`str | None` 语法（PEP 604）即可
- 测试：使用 pytest，新功能请添加对应测试
- 提交前请确保 `uv run pytest` 通过

## 目录结构

```
my-info-vw/
├── config/              # 配置文件（llm.yaml, search.yaml）
├── src/
│   ├── agents/          # 各阶段 Agent
│   ├── config/          # 配置路径工具
│   ├── llm/             # LLM Manager
│   ├── search/          # 搜索聚合 + Provider
│   │   └── providers/   # 各搜索 Provider CLI
│   └── workflows/       # LangGraph 工作流
├── tests/               # 测试
├── webapp/              # Next.js 前端
├── info-check.py        # CLI 入口
├── info-check.sh        # Shell 入口
├── pyproject.toml       # 项目配置
└── .env                 # 环境变量（不提交）
```
