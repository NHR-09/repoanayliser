from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def smoke() -> None:
    root = Path(__file__).resolve().parents[1]
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(root / "server.py")],
        cwd=root,
    )
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            tools = await session.list_tools()
            result = await session.call_tool("list_repositories", {"limit": 1})
            print(json.dumps({
                "tool_count": len(tools.tools),
                "tools": [tool.name for tool in tools.tools],
                "call_is_error": result.is_error,
                "structured_result": result.structured_content is not None,
            }))


if __name__ == "__main__":
    asyncio.run(smoke())
