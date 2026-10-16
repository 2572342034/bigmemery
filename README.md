# BigMemery Enterprise AI Workspace

一个基于 `Vue 3 + Vite + Element Plus` 和 `FastAPI + LangChain` 的企业风格 AI 对话工作台，具备以下能力：

- `SQLite` 持久化聊天会话与消息历史
- `MySQL` 存储用户账号并提供登录注册
- `Chroma` 作为本地 `RAG` 向量数据库
- `Ollama / llama.cpp` 本地模型接入
- `SSE` 流式输出
- 会话列表、新增/删除对话、知识库管理

## 目录结构

```text
BigMemery/
├─ backend/
│  ├─ app/
│  │  ├─ api/
│  │  │  ├─ auth.py
│  │  │  ├─ chat.py
│  │  │  ├─ deps.py
│  │  │  └─ knowledge.py
│  │  ├─ core/
│  │  │  ├─ config.py
│  │  │  └─ security.py
│  │  ├─ db/
│  │  │  ├─ chat_models.py
│  │  │  ├─ session.py
│  │  │  └─ user_models.py
│  │  ├─ schemas/
│  │  │  ├─ auth.py
│  │  │  ├─ chat.py
│  │  │  ├─ conversation.py
│  │  │  └─ knowledge.py
│  │  ├─ services/
│  │  │  ├─ auth_service.py
│  │  │  ├─ db_service.py
│  │  │  ├─ knowledge_service.py
│  │  │  └─ llm_service.py
│  │  └─ main.py
│  ├─ .env
│  ├─ .env.example
│  ├─ chat.db
│  └─ requirements.txt
├─ frontend/
│  ├─ src/
│  │  ├─ api/
│  │  │  ├─ auth.js
│  │  │  ├─ chat.js
│  │  │  ├─ http.js
│  │  │  └─ knowledge.js
│  │  ├─ views/
│  │  │  ├─ AuthView.vue
│  │  │  └─ WorkspaceView.vue
│  │  ├─ App.vue
│  │  ├─ main.js
│  │  └─ styles.css
│  ├─ package.json
│  └─ vite.config.js
└─ README.md
```

## 后端能力

### 1. SQLite 聊天持久化

- 聊天会话表：`chat_conversations`
- 聊天消息表：`chat_messages`
- 知识文档元数据表：`knowledge_documents`
- 默认数据库：`backend/chat.db`

### 2. MySQL 用户体系

- 用户表：`users`
- 登录接口：`POST /api/auth/login`
- 注册接口：`POST /api/auth/register`
- 当前用户接口：`GET /api/auth/me`
- 启动时会自动创建一个默认管理员账号

默认管理员：

- 用户名：`admin`
- 密码：`Admin@123456`

### 3. Chroma RAG

- 写入知识：`POST /api/knowledge`
- 查询知识列表：`GET /api/knowledge`
- 删除知识：`DELETE /api/knowledge/{document_id}`
- 聊天时按当前用户维度检索知识片段并自动拼接到系统提示词

### 4. SSE 流式聊天

- 主接口：`POST /api/chat/stream`
- `EventSource` 兜底：`GET /api/chat/stream/es`

## 前端能力

- 登录 / 注册双入口
- 企业风格工作台布局
- 左侧会话列表
- 中间聊天主区
- 右侧知识运营面板
- 知识库抽屉管理
- `Authorization Bearer` 鉴权
- `fetch` 流式读取，失败时回退 `EventSource`

## 环境变量

重点配置如下：

```env
# LLM
LOCAL_LLM_PROVIDER=ollama
DEFAULT_MODEL=qwen2.5:14b-instruct-q4_k_m
AVAILABLE_MODELS=qwen2.5:14b-instruct-q4_k_m,llama3.1:8b-instruct-q4_k_m,mistral:7b-instruct-q4_k_m,qwen2.5:7b-instruct-q4_k_m
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# SQLite
CHAT_SQLITE_URL=sqlite:///./chat.db

# MySQL
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=123456
MYSQL_DATABASE=bigmemery_auth

# Chroma
CHROMA_PERSIST_DIRECTORY=./chroma_db
CHROMA_COLLECTION_NAME=bigmemery_knowledge
RAG_TOP_K=4

# Auth
AUTH_TOKEN_SECRET=change-this-secret-in-production
AUTH_TOKEN_EXPIRE_MINUTES=720
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=Admin@123456
DEFAULT_ADMIN_DISPLAY_NAME=System Admin
```

## 启动步骤

### 1. 准备本地模型

```bash
ollama serve
ollama pull qwen2.5:14b-instruct-q4_k_m
ollama pull nomic-embed-text
```

### 2. 准备 MySQL

先创建数据库：

```sql
CREATE DATABASE bigmemery_auth CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. 安装后端依赖

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

### 4. 启动后端

```bash
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev
```

## 常用接口

### 登录

```bash
curl -X POST "http://127.0.0.1:8000/api/auth/login" ^
  -H "Content-Type: application/json" ^
  -d "{\"username\":\"admin\",\"password\":\"Admin@123456\"}"
```

### 新建知识条目

```bash
curl -X POST "http://127.0.0.1:8000/api/knowledge" ^
  -H "Authorization: Bearer <token>" ^
  -H "Content-Type: application/json" ^
  -d "{\"title\":\"退款规范\",\"source\":\"SOP\",\"content\":\"退款申请须在 7 天内提交。\"}"
```

### 发起流式聊天

```bash
curl -N -X POST "http://127.0.0.1:8000/api/chat/stream" ^
  -H "Authorization: Bearer <token>" ^
  -H "Content-Type: application/json" ^
  -H "Accept: text/event-stream" ^
  -d "{\"conversation_id\":\"conv_xxx\",\"message\":\"总结退款规范\",\"model\":\"qwen2.5:14b-instruct-q4_k_m\",\"use_rag\":true}"
```

## 本次改造说明

- 原先内存型会话存储已替换为 `SQLite`
- 新增了 `MySQL` 用户认证体系
- 新增了 `Chroma` 知识库和 RAG 检索
- 前端新增登录页与企业风格工作台
- SSE 接口已加入鉴权支持

## 验证说明

我已经完成代码改造，并做了：

- Python 语法级检查

我没有完成的部分：

- 当前本地虚拟环境尚未安装新增依赖 `pymysql` 和 `chromadb`
- 前端 `vite build` 在当前受限环境里触发了本地权限问题，没有拿到完整构建结果
- 我没有实际重启你的 FastAPI / Vite / MySQL / Ollama 进程进行端到端联调
