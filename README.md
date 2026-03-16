# my-info-vw

AI 驱动的消息核查工具，通过多渠道搜索和验证来判断消息的准确性。

## 架构概览

```
info-check.sh → info-check.py → Workflow (LangGraph)
                                    ├── Parse (消息解析)
                                    ├── SearchQuery (查询生成)
                                    ├── Search (多源搜索)
                                    ├── Verify (结果验证)
                                    └── Synthesize (综合报告)
```

核心组件：

| 组件 | 说明 |
|------|------|
| `info-check.py` | CLI 入口，支持文本/JSONL 输出 |
| `src/workflows/check.py` | LangGraph 工作流编排 |
| `src/agents/` | 各阶段 Agent（解析、查询、验证、综合） |
| `src/llm/manager.py` | 多 LLM Provider 自动 fallback |
| `src/search/` | 多源搜索聚合（Tavily、Jina、Brave、Bing、百度） |
| `src/config/path_utils.py` | 统一配置路径管理 |
| `webapp/` | Next.js 前端 |

## 前置条件

- Python >= 3.10
- [uv](https://docs.astral.sh/uv/)（推荐依赖管理工具）

## 安装

```bash
git clone https://github.com/clarencep/my-info-vw.git
cd my-info-vw
uv sync
```

## 配置

### LLM 配置（二选一）

**方式一：YAML 多模型配置**（推荐）

编辑 `config/llm.yaml`，定义多个 LLM Provider 和 fallback 顺序：

```yaml
providers:
  - name: bigmodel-glm47
    api_base: https://open.bigmodel.cn/api/coding/paas/v4
    api_key_env: BIGMODEL_API_KEY
    models:
      - name: glm-4.7
        temperature: 0.7

fallback_order:
  - bigmodel-glm47/glm-4.7
```

> **命名约定**：每个 LLM Provider 的 `api_key_env` 应使用与 Provider 相关的专属环境变量名（如 `BIGMODEL_API_KEY`），避免多个 Provider 共用 `OPENAI_API_KEY`。请在 `.env` 文件中设置对应的 key。

**方式二：.env 单模型模式**

若 `config/llm.yaml` 不存在，自动回退到 `.env` 中的单模型配置：

```bash
cp .env.example .env
# 编辑 .env 填入你的 API Key
```

### 自定义配置目录

设置 `MY_INFO_VW_CONFIG_DIR` 环境变量可将所有配置文件重定向到自定义目录（适用于容器化部署、集中配置管理等场景）：

```bash
# .env 或环境变量
MY_INFO_VW_CONFIG_DIR=/etc/my-info-vw
```

未设置时，默认使用项目根目录下的 `config/` 目录。

### 搜索配置

编辑 `config/search.yaml` 启用/禁用搜索 Provider 并调整优先级。

## 使用

```bash
# 文本输出
./info-check.sh "马斯克的 Starship 正式发射了"

# 详细输出
./info-check.sh "消息内容" -v

# JSONL 输出（适合程序化消费）
./info-check.sh "消息内容" --jsonl

# JSONL 输出到文件
./info-check.sh "消息内容" --jsonl -o results.jsonl
```

## 测试

```bash
uv run pytest

# 带覆盖率
uv run pytest --cov=src --cov-report=term-missing

# 并行执行
uv run pytest -n auto
```

## 项目约定

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## License

MIT
