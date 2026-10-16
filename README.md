# BigMemery · 企业级 AI 对话工作台

一个面向**企业内网私有化部署**的 AI 对话与知识问答平台。大模型本地运行、数据不出域，支持多用户账号体系、多会话管理与文档知识库检索增强问答（RAG），回答以 SSE 流式返回；并通过独立的 **MCP Server** 将知识库能力标准化对外暴露。

## 功能特性

- **多用户账号体系** —— 注册 / 登录 / 当前用户，Token 鉴权
- **多会话管理** —— 会话列表、新建、删除，消息历史持久化
- **SSE 流式对话** —— 逐 token 推送，首字即显；`fetch` 流式读取为主，`EventSource` 兜底
- **RAG 知识库问答** —— 向量检索 + 关键词检索混合召回，加权重排后注入系统提示词
- **文档一键入库** —— 支持 PDF / Word / Excel / Markdown / CSV / JSON 等 9 类格式解析
- **引用可溯源** —— 强制回答携带引用标记，无引用则判定为非依据回答并剥离冗余解释
- **MCP Server** —— 以 Model Context Protocol 对外暴露知识库检索能力，可被 Claude Desktop / Cursor / Cline 等客户端直接调用
- **多模型切换** —— 支持 Ollama 与 llama.cpp 两种本地推理后端

## 技术栈

| 层次 | 技术选型 |
| --- | --- |
| 前端 | Vue 3.5（Composition API）· Vite 7 · Element Plus 2.11 · Axios 1.9 |
| 后端 | Python 3.12 · FastAPI 0.116 · Uvicorn 0.35 · Pydantic v2 · SQLAlchemy 2.0 |
| 大模型 | Ollama（qwen2.5 / llama3.1 / mistral）· llama.cpp（OpenAI 兼容） |
| 编排与检索 | LangChain 0.3 · ChromaDB 1.0 |
| 向量化 | Ollama `nomic-embed-text` |
| 数据存储 | SQLite（会话与消息）· MySQL（用户账号）· ChromaDB（向量）· 本地文件系统（知识原文） |
| 鉴权 | 自研 HMAC-SHA256 签名 Token · PBKDF2-SHA256 口令哈希（48 万次迭代） |
| 协议 | SSE（Server-Sent Events）· MCP（Model Context Protocol） |

## 系统架构

```
┌──────────────────────────────────────────────────────────┐
│  前端 · Vue 3 SPA                                        │
│  Element Plus UI  │  Axios + fetch(SSE)  │  本地登录态   │
└───────────────────────────┬──────────────────────────────┘
                            │  HTTP / SSE
┌───────────────────────────┴──────────────────────────────┐
│  后端 · FastAPI                                          │
│  api（路由）→ services（业务）→ db（模型/会话）→ schemas  │
│  HMAC Token 鉴权  │  StreamingResponse 流式  │  文件解析  │
└───────────────────────────┬──────────────────────────────┘
                            │
┌───────────────────────────┴──────────────────────────────┐
│  智能体 · RAG 检索层                                     │
│  LangChain 编排  │  Ollama / llama.cpp  │  混合检索+重排 │
└───────────────────────────┬──────────────────────────────┘
                            │
┌───────────────────────────┴──────────────────────────────┐
│  数据存储层                                              │
│  SQLite（会话/消息）  MySQL（用户）  Chroma（向量）  文件 │
└──────────────────────────────────────────────────────────┘

                 ┌────────────────────────────┐
                 │  MCP Server（独立进程）    │
                 │  复用检索与持久化能力      │
                 │  对外暴露 3 tools + 1 res  │
                 └────────────────────────────┘
```

## 目录结构

```
BigMemery/
├─ backend/
│  ├─ app/
│  │  ├─ api/            # 路由层：auth / chat / knowledge / deps
│  │  ├─ core/           # 配置与安全：config.py / security.py
│  │  ├─ db/             # 数据模型与会话：chat_models / user_models / session
│  │  ├─ schemas/        # 请求响应模型
│  │  ├─ services/       # 业务层：auth / db / llm / knowledge / storage / file_parser
│  │  ├─ main.py         # FastAPI 应用入口
│  │  └─ run.py          # 本地启动脚本
│  ├─ mcp_server.py      # MCP Server（独立进程）
│  ├─ verify_mcp.py      # MCP 端到端验证脚本
│  ├─ requirements.txt
│  └─ .env.example
├─ frontend/
│  ├─ src/
│  │  ├─ api/            # http / auth / chat / knowledge
│  │  ├─ views/          # AuthView / WorkspaceView / KnowledgeBaseView
│  │  ├─ App.vue
│  │  └─ main.js
│  ├─ package.json
│  └─ vite.config.js
└─ README.md
```

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 20+
- MySQL 8.0+
- [Ollama](https://ollama.com/)（或 llama.cpp）

### 1. 准备本地模型

```bash
ollama serve
ollama pull qwen2.5:14b-instruct-q4_k_m
ollama pull nomic-embed-text
```

> `nomic-embed-text` 用于向量化，RAG 检索依赖它，必须拉取。

### 2. 准备 MySQL

```sql
CREATE DATABASE bigmemery_auth CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. 启动后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS / Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # macOS / Linux: cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> 也可以直接运行 `python -m app.run`。

首次启动会自动建表，并创建一个默认管理员账号：

| 用户名 | 密码 |
| --- | --- |
| `admin` | `Admin@123456` |

> ⚠️ 生产环境请务必修改默认口令与 `AUTH_TOKEN_SECRET`。

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 **http://localhost:5173**。

### 5. 使用 MCP Server（可选）

```bash
cd backend
.venv\Scripts\python.exe mcp_server.py       # stdio 传输，由客户端拉起
```

验证服务端是否正常：

```bash
.venv\Scripts\python.exe verify_mcp.py
```

接入 MCP 客户端（以 Cline / Roo Code 为例）：

```json
{
  "mcpServers": {
    "bigmemery-knowledge": {
      "command": "<项目路径>/backend/.venv/Scripts/python.exe",
      "args": ["<项目路径>/backend/mcp_server.py"]
    }
  }
}
```

暴露的 MCP 能力：

| 类型 | 名称 | 说明 |
| --- | --- | --- |
| tool | `search_knowledge` | 混合检索知识库，返回带引用编号的原文 |
| tool | `list_documents` | 列出知识库文档元数据 |
| tool | `get_document` | 按 ID 读取文档全文 |
| resource | `knowledge://documents` | 知识库文档索引 |

## 配置说明

主要环境变量（完整见 `backend/.env.example`）：

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `LOCAL_LLM_PROVIDER` | 推理后端，`ollama` 或 `llamacpp` | `ollama` |
| `DEFAULT_MODEL` | 默认对话模型 | `qwen2.5:14b-instruct-q4_k_m` |
| `AVAILABLE_MODELS` | 可选模型列表（逗号分隔） | — |
| `OLLAMA_BASE_URL` | Ollama 服务地址 | `http://127.0.0.1:11434` |
| `OLLAMA_EMBEDDING_MODEL` | 向量化模型 | `nomic-embed-text` |
| `CHAT_SQLITE_URL` | 会话数据库 | `sqlite:///./chat.db` |
| `MYSQL_*` | 用户库连接信息 | — |
| `CHROMA_PERSIST_DIRECTORY` | 向量库持久化目录 | `./chroma_db` |
| `RAG_TOP_K` | 最终注入提示词的片段数 | `4` |
| `RAG_VECTOR_K` | 向量召回数量 | `8` |
| `RAG_KEYWORD_K` | 关键词召回数量 | `8` |
| `RAG_RERANK_K` | 重排候选数量 | `5` |
| `RAG_MIN_SCORE` | 重排最低分阈值 | `0.18` |
| `AUTH_TOKEN_SECRET` | Token 签名密钥 | 需修改 |
| `AUTH_TOKEN_EXPIRE_MINUTES` | Token 有效期（分钟） | `720` |

## 接口文档

后端启动后访问 **http://127.0.0.1:8000/docs** 查看完整的交互式 API 文档。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/auth/register` | 注册 |
| `POST` | `/api/auth/login` | 登录 |
| `GET` | `/api/auth/me` | 当前用户 |
| `GET` | `/api/models` | 可用模型列表 |
| `GET` | `/api/conversations` | 会话列表 |
| `POST` | `/api/conversations` | 新建会话 |
| `GET` | `/api/conversations/{id}` | 会话详情 |
| `DELETE` | `/api/conversations/{id}` | 删除会话 |
| `POST` | `/api/chat/stream` | **流式对话（SSE）** |
| `GET` | `/api/chat/stream/es` | 流式对话（EventSource 兜底） |
| `GET` | `/api/knowledge` | 知识库列表 |
| `POST` | `/api/knowledge` | 新增知识（文本） |
| `POST` | `/api/knowledge/upload` | 上传文档入库 |
| `GET` | `/api/knowledge/{id}` | 知识详情 |
| `GET` | `/api/knowledge/{id}/download` | 下载原始文件 |
| `DELETE` | `/api/knowledge/{id}` | 删除知识 |
| `GET` | `/health` | 健康检查 |

### SSE 事件协议

`POST /api/chat/stream` 返回 `text/event-stream`，事件类型：

| 事件 | 载荷 | 说明 |
| --- | --- | --- |
| `start` | `{conversation_id, model, use_rag, grounded, sources}` | 开始生成 |
| `delta` | `{delta, full_text}` | 逐 token 推送，`full_text` 为累积全文 |
| `end` | `{full_text, sources, grounded}` | 生成结束 |
| `error` | `{message}` | 发生异常 |

## RAG 检索说明

检索链路采用**混合召回 + 加权重排**：

1. **分块** —— 长文本按 500 字切分，相邻块重叠 80 字
2. **向量召回** —— ChromaDB 相似度检索，取 Top-8
3. **关键词召回** —— TF 对数打分，中文按 1/2/3-gram 混合切词，取 Top-8
4. **融合重排** —— `0.5 × 向量分 + 0.3 × 关键词分 + 0.2 × 词重叠度`，取 Top-5
5. **阈值过滤** —— 低于 `RAG_MIN_SCORE` 的片段丢弃
6. **提示词注入** —— 片段拼入 system prompt，并约束模型只在真正使用时保留 `[n]` 引用

设计动机：纯向量检索对专有名词、编号类查询不敏感；纯关键词检索对语义改写无能为力。两者互补后再重排，能显著提升中文场景的召回质量。

## 安全说明

本项目默认配置面向**本地开发**，部署到生产环境前请务必：

- 修改 `AUTH_TOKEN_SECRET`（默认值仅供开发）
- 修改默认管理员口令 `Admin@123456`
- 通过环境变量注入数据库口令，**不要提交 `.env` 文件**
- 为 MySQL 创建最小权限账号，避免直接使用 `root`
- 按需收敛 `CORS_ORIGINS`

## 常见问题

**Q：检索不到知识库内容？**
确认 `ollama pull nomic-embed-text` 已执行，且 Ollama 服务处于运行状态。若向量库不可用，检索会自动降级为纯关键词模式。

**Q：流式输出变成"转圈半天再一次性出全文"？**
若部署在 Nginx 之后，需关闭该路径的响应缓冲（后端已发送 `X-Accel-Buffering: no`，反向代理侧也需确认）。

**Q：MCP 客户端里看不到工具？**
先运行 `python verify_mcp.py` 确认服务端本身正常；再检查客户端配置里的 `command` 是否指向**虚拟环境内的** `python.exe`。

**Q：Windows 下 MCP 配置路径怎么写？**
JSON 中的路径需用双反斜杠 `\\` 或正斜杠 `/`。

## License

[MIT](https://choosealicense.com/licenses/mit/)
