"""BigMemery MCP Server —— 把项目知识库能力以 MCP 协议对外暴露。

设计说明
--------
本文件是一个**独立的 MCP Server 进程**，不侵入现有 FastAPI 链路：
它复用 `app.services` 里已有的检索与持久化能力，把它们包装成 MCP 工具，
供 Claude Desktop / Cursor / 自研 Agent 等任意 MCP 客户端调用。

暴露的 MCP 能力
---------------
- tools
  - `search_knowledge`  向量 + 关键词混合检索，带重排（走 Chroma + SQLite）
  - `list_documents`    列出知识库文档元数据
  - `get_document`      按 ID 读取文档全文
- resources
  - `knowledge://documents`  知识库文档索引

运行方式
--------
stdio 传输（由客户端以子进程方式拉起，也是默认方式）：

    cd backend
    .venv/Scripts/python.exe mcp_server.py

本地调试（MCP Inspector）：

    npx @modelcontextprotocol/inspector .venv/Scripts/python.exe mcp_server.py

客户端配置示例（Claude Desktop / Cursor 的 mcp 配置）：

    {
      "mcpServers": {
        "bigmemery-knowledge": {
          "command": "<项目路径>/backend/.venv/Scripts/python.exe",
          "args": ["<项目路径>/backend/mcp_server.py"]
        }
      }
    }

注意事项
--------
- stdio 传输下 **stdout 被协议独占**，任何调试输出必须走 stderr，否则会污染报文。
- 必须先 chdir 到 backend 目录：`.env` 里的 `CHAT_SQLITE_URL=sqlite:///./chat.db`
  和 `CHROMA_PERSIST_DIRECTORY=./chroma_db` 都是**相对路径**，依赖当前工作目录。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent

# 必须在导入 app.* 之前 chdir —— config 的 env_file=".env" 与 .env 内的相对路径都依赖 cwd
os.chdir(BACKEND_DIR)
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from app.services.db_service import db_service  # noqa: E402
from app.services.knowledge_service import knowledge_service  # noqa: E402

mcp = FastMCP("bigmemery-knowledge")

DEFAULT_USER_ID = 1


@mcp.tool()
def search_knowledge(query: str, user_id: int = DEFAULT_USER_ID) -> str:
    """在企业知识库中检索与问题相关的资料片段，返回带引用编号的原文。

    检索采用「向量检索 + 关键词检索」混合召回并加权重排，结果已按相关度排序。
    当问题涉及企业内部规范、政策、流程、产品文档等需要依据资料才能回答的内容时，
    应当优先调用本工具，而不是凭通用知识作答。

    Args:
        query: 检索语句。尽量保留用户原话中的关键实体、专有名词与编号。
        user_id: 知识库归属的用户 ID，默认 1（默认管理员账号）。
    """
    chunks = knowledge_service.retrieve_context(user_id, query)
    if not chunks:
        return "未在知识库中检索到相关资料。"

    blocks = [
        f"[{index}] {item.title} | source={item.source} | score={item.rerank_score:.2f}\n{item.content}"
        for index, item in enumerate(chunks, start=1)
    ]
    return "\n\n".join(blocks)


@mcp.tool()
def list_documents(user_id: int = DEFAULT_USER_ID) -> str:
    """列出该用户知识库中的全部文档（仅元数据，不含正文）。

    用于先了解知识库里有哪些资料，再决定是否调用 search_knowledge 深入检索。

    Args:
        user_id: 知识库归属的用户 ID，默认 1。
    """
    items = db_service.list_knowledge(user_id)
    if not items:
        return "知识库为空。"

    return "\n".join(
        f"{item.id} | {item.title} | source={item.source} "
        f"| chunks={item.chunk_count} | status={item.index_status}"
        for item in items
    )


@mcp.tool()
def get_document(document_id: str, user_id: int = DEFAULT_USER_ID) -> str:
    """按文档 ID 读取知识库中某篇文档的完整正文。

    当已知具体文档 ID、需要查看全文而非检索片段时使用。

    Args:
        document_id: 文档 ID，形如 `doc_xxxxxxxxxxxx`，可从 list_documents 获取。
        user_id: 知识库归属的用户 ID，默认 1。
    """
    item = db_service.get_knowledge(user_id, document_id)
    if item is None:
        return f"未找到文档：{document_id}"

    return f"# {item.title}\nsource={item.source}\n\n{item.content or ''}"


@mcp.resource("knowledge://documents")
def knowledge_index() -> str:
    """知识库文档索引，供客户端作为上下文资源读取。"""
    return list_documents()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
