"""Agent tool registry: sync wrappers for keyword_search and semantic_search."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from src.core.settings import load_settings


@dataclass
class AgentTool:
    """One tool the Agent can call."""

    name: str
    description: str
    func: Callable[..., str]


def _format_results_as_observation(results: List[Any], max_snippets: int = 5, snippet_len: int = 200) -> str:
    """Turn retrieval results into a short observation string for the LLM."""
    if not results:
        return "No results found."
    lines = [f"Found {len(results)} result(s):"]
    for i, r in enumerate(results[:max_snippets]):
        text = (r.text or "")[:snippet_len]
        if len((r.text or "")) > snippet_len:
            text += "..."
        score = getattr(r, "score", None)
        s = f"  {i + 1}. " + (f"[score={score:.2f}] " if score is not None else "") + text
        lines.append(s)
    if len(results) > max_snippets:
        lines.append(f"  ... and {len(results) - max_snippets} more.")
    return "\n".join(lines)


def _run_keyword_search(query: str, top_k: int = 5, collection: str = "default") -> str:
    """Synchronous keyword search; returns observation string."""
    from src.mcp_server.tools.keyword_search import KeywordSearchTool

    tool = KeywordSearchTool(settings=load_settings())
    tool._ensure_initialized(collection)
    processed = tool._query_processor.process(query)
    keywords = processed.keywords
    if not keywords:
        keywords = [q.strip() for q in query.split() if q.strip()][:10]
    if not keywords:
        return "No keywords extracted from query."
    results = tool._sparse_retriever.retrieve(keywords=keywords, top_k=top_k, collection=collection)
    return _format_results_as_observation(results)


def _run_semantic_search(query: str, top_k: int = 5, collection: str = "default") -> str:
    """Synchronous semantic search; returns observation string."""
    from src.mcp_server.tools.semantic_search import SemanticSearchTool

    tool = SemanticSearchTool(settings=load_settings())
    tool._ensure_initialized(collection)
    results = tool._search(query=query, top_k=top_k, collection=collection)
    return _format_results_as_observation(results)


def get_tools() -> List[AgentTool]:
    """Return the list of tools available to the Agent."""
    return [
        AgentTool(
            name="keyword_search",
            description="Search by keywords (BM25). Use for exact terms, names, IDs. Args: query, top_k=5, collection='default'",
            func=_run_keyword_search,
        ),
        AgentTool(
            name="semantic_search",
            description="Search by semantic similarity. Use for conceptual questions. Args: query, top_k=5, collection='default'",
            func=_run_semantic_search,
        ),
    ]


def parse_action(line: str) -> Optional[tuple[str, Dict[str, Any]]]:
    """Parse 'Action: tool_name(arg1="val", arg2=5)' into (tool_name, kwargs).

    Returns None if line does not match.
    """
    line = line.strip()
    if not line.lower().startswith("action:"):
        return None
    rest = line[7:].strip()
    match = re.match(r"(\w+)\s*\((.*)\)\s*$", rest, re.DOTALL)
    if not match:
        return None
    tool_name, args_str = match.group(1), match.group(2).strip()
    if not args_str:
        return (tool_name, {})
    kwargs: Dict[str, Any] = {}
    for part in re.split(r",\s*(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", args_str):
        part = part.strip()
        eq = part.find("=")
        if eq == -1:
            continue
        key = part[:eq].strip()
        val = part[eq + 1 :].strip()
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1].replace('\\"', '"')
        elif val.isdigit():
            val = int(val)
        else:
            try:
                val = int(val)
            except ValueError:
                pass
        kwargs[key] = val
    return (tool_name, kwargs)


def run_tool(tool_name: str, kwargs: Dict[str, Any], collection: str = "default") -> str:
    """Execute a tool by name with given kwargs; collection used as default for search tools."""
    tools = {t.name: t for t in get_tools()}
    if tool_name not in tools:
        return f"Unknown tool: {tool_name}. Available: {list(tools.keys())}"
    t = tools[tool_name]
    query = kwargs.get("query") or kwargs.get("q", "")
    top_k = kwargs.get("top_k", 5)
    coll = kwargs.get("collection", collection)
    try:
        return t.func(query=query, top_k=top_k, collection=coll)
    except Exception as e:
        return f"Tool error: {e}"
