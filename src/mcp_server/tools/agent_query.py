"""MCP Tool: agent_query

Single entry point that runs the embedded ReAct Agent to answer
the user question by calling keyword_search and semantic_search as needed.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

from mcp import types

from src.agent.react_agent import run_agent
from src.core.settings import load_settings

if TYPE_CHECKING:
    from src.core.settings import Settings

logger = logging.getLogger(__name__)

TOOL_NAME = "agent_query"
TOOL_DESCRIPTION = """Answer a question using the knowledge base via an internal Agent.

The Agent can call keyword_search and semantic_search multiple times
and then synthesize a final answer. Use this for complex or multi-step questions.

Parameters:
- query: The user's question in natural language
- collection: Optional collection name (default: default)
- max_steps: Max tool-call rounds (default: 5)
"""

TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "The user's question to answer using the knowledge base.",
        },
        "collection": {
            "type": "string",
            "description": "Optional collection name.",
        },
        "max_steps": {
            "type": "integer",
            "description": "Maximum number of tool-call rounds.",
            "default": 5,
            "minimum": 1,
            "maximum": 10,
        },
    },
    "required": ["query"],
}


async def agent_query_handler(
    query: str,
    collection: Optional[str] = None,
    max_steps: int = 5,
) -> types.CallToolResult:
    """Run the embedded Agent and return the final answer."""
    if not query or not query.strip():
        return types.CallToolResult(
            content=[types.TextContent(type="text", text="query cannot be empty")],
            isError=True,
        )
    effective_collection = collection or "default"
    effective_max_steps = min(max(1, max_steps), 10)
    try:
        settings = load_settings()
        result = await asyncio.to_thread(
            run_agent,
            query=query.strip(),
            collection=effective_collection,
            max_steps=effective_max_steps,
            settings=settings,
        )
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=result)],
            isError=False,
        )
    except Exception as e:
        logger.exception("agent_query failed: %s", e)
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"Agent error: {e}")],
            isError=True,
        )


def register_tool(protocol_handler: Any) -> None:
    protocol_handler.register_tool(
        name=TOOL_NAME,
        description=TOOL_DESCRIPTION,
        input_schema=TOOL_INPUT_SCHEMA,
        handler=agent_query_handler,
    )
    logger.info("Registered MCP tool: %s", TOOL_NAME)
