"""MCP Server 端到端验证脚本。

以 MCP 客户端身份，通过 stdio 拉起 `mcp_server.py`，完成三件事：
  1. 握手初始化
  2. 列出服务端暴露的 tools / resources
  3. 实际调用工具，验证能取到真实知识库数据

运行：
    cd backend
    .venv/Scripts/python.exe verify_mcp.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BACKEND_DIR = Path(__file__).resolve().parent
SERVER_SCRIPT = BACKEND_DIR / "mcp_server.py"

TIMEOUT = 60


def _text(result) -> str:
    """把 CallToolResult 里的文本内容拼起来。"""
    parts = []
    for item in result.content:
        parts.append(getattr(item, "text", None) or str(item))
    return "\n".join(parts)


async def run() -> int:
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_SCRIPT)],
        cwd=str(BACKEND_DIR),
    )

    print("=" * 62)
    print("MCP 客户端验证")
    print("=" * 62)
    print(f"服务端脚本 : {SERVER_SCRIPT}")
    print(f"解释器     : {sys.executable}")
    print()

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            # ① 握手
            init = await asyncio.wait_for(session.initialize(), timeout=TIMEOUT)
            server_info = init.serverInfo
            print("[1] 握手成功")
            print(f"    server name    : {server_info.name}")
            print(f"    server version : {server_info.version}")
            print(f"    protocol       : {init.protocolVersion}")
            print()

            # ② 列出能力
            tools = await asyncio.wait_for(session.list_tools(), timeout=TIMEOUT)
            print(f"[2] 可用工具（{len(tools.tools)} 个）")
            for tool in tools.tools:
                desc = (tool.description or "").strip().splitlines()[0]
                print(f"    - {tool.name}: {desc[:56]}")
            print()

            try:
                resources = await asyncio.wait_for(session.list_resources(), timeout=TIMEOUT)
                print(f"[3] 可用资源（{len(resources.resources)} 个）")
                for res in resources.resources:
                    print(f"    - {res.uri}")
            except Exception as exc:  # noqa: BLE001
                print(f"[3] 资源列表获取失败：{exc}")
            print()

            # ③ 实际调用
            print("[4] 调用 list_documents")
            listed = await asyncio.wait_for(
                session.call_tool("list_documents", {"user_id": 1}), timeout=TIMEOUT
            )
            listed_text = _text(listed)
            for line in listed_text.splitlines()[:6]:
                print(f"    {line}")
            print()

            print("[5] 调用 search_knowledge(query='退款')")
            searched = await asyncio.wait_for(
                session.call_tool("search_knowledge", {"query": "退款", "user_id": 1}),
                timeout=TIMEOUT,
            )
            searched_text = _text(searched)
            for line in searched_text.splitlines()[:8]:
                print(f"    {line}")
            print()

            print("=" * 62)
            if listed.isError or searched.isError:
                print("结果：调用返回错误")
                return 1
            print("结果：MCP 服务端功能正常，工具可被客户端调用并返回真实数据")
            print("=" * 62)
            return 0


def main() -> int:
    try:
        return asyncio.run(run())
    except asyncio.TimeoutError:
        print("\n[失败] 超时：服务端未在限定时间内响应")
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"\n[失败] {type(exc).__name__}: {exc}")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
