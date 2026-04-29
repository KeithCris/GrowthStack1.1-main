"""MCP Tool: keyword_search

Keyword-only search using BM25 (sparse retrieval). Exposed for Agent
and clients that want to use keyword search without semantic retrieval.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from mcp import types

from src.core.response.response_builder import ResponseBuilder, MCPToolResponse
from src.core.settings import load_settings, resolve_path
from src.core.types import RetrievalResult

if TYPE_CHECKING:
    from src.core.settings import Settings

logger = logging.getLogger(__name__)

TOOL_NAME = "keyword_search"
TOOL_DESCRIPTION = """Search the knowledge base by keywords only (BM25).

Use this when you need exact or keyword-based matching, e.g. names,
IDs, or specific terms. Does not use semantic similarity.

Parameters:
- query: Search query (will be tokenized into keywords)
- top_k: Maximum number of results (default: 5)
- collection: Optional collection name (default: default)
"""

TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Search query; will be split into keywords for BM25.",
        },
        "top_k": {
            "type": "integer",
            "description": "Maximum number of results to return.",
            "default": 5,
            "minimum": 1,
            "maximum": 20,
        },
        "collection": {
            "type": "string",
            "description": "Optional collection name to limit the search scope.",
        },
    },
    "required": ["query"],
}


class KeywordSearchTool:
    """MCP Tool for keyword-only (BM25) search."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        response_builder: Optional[ResponseBuilder] = None,
    ) -> None:
        self._settings = settings
        self._response_builder = response_builder or ResponseBuilder()
        self._sparse_retriever = None
        self._query_processor = None
        self._current_collection: Optional[str] = None

    @property
    def settings(self) -> Settings:
        if self._settings is None:
            self._settings = load_settings()
        return self._settings

    def _ensure_initialized(self, collection: str) -> None:
        if self._current_collection == collection and self._sparse_retriever is not None:
            return
        from src.core.query_engine.query_processor import QueryProcessor
        from src.core.query_engine.sparse_retriever import create_sparse_retriever
        from src.ingestion.storage.bm25_indexer import BM25Indexer
        from src.libs.vector_store.vector_store_factory import VectorStoreFactory

        vector_store = VectorStoreFactory.create(
            self.settings,
            collection_name=collection,
        )
        bm25_indexer = BM25Indexer(
            index_dir=str(resolve_path(f"data/db/bm25/{collection}"))
        )
        self._sparse_retriever = create_sparse_retriever(
            settings=self.settings,
            bm25_indexer=bm25_indexer,
            vector_store=vector_store,
        )
        self._sparse_retriever.default_collection = collection
        self._query_processor = QueryProcessor()
        self._current_collection = collection
        logger.info("KeywordSearchTool initialized for collection=%s", collection)

    def _search(
        self,
        query: str,
        top_k: int,
        collection: str,
    ) -> List[RetrievalResult]:
        self._ensure_initialized(collection)
        processed = self._query_processor.process(query)
        keywords = processed.keywords
        if not keywords:
            keywords = [q.strip() for q in query.split() if q.strip()][:10]
        if not keywords:
            return []
        return self._sparse_retriever.retrieve(
            keywords=keywords,
            top_k=top_k,
            collection=collection,
        )

    async def execute(
        self,
        query: str,
        top_k: int = 5,
        collection: Optional[str] = None,
    ) -> types.CallToolResult:
        if not query or not query.strip():
            return types.CallToolResult(
                content=[types.TextContent(type="text", text="query cannot be empty")],
                isError=True,
            )
        effective_collection = collection or "default"
        effective_top_k = min(max(1, top_k), 20)
        try:
            results = await asyncio.to_thread(
                self._search, query.strip(), effective_top_k, effective_collection
            )
            response = self._response_builder.build(
                results=results,
                query=query,
                collection=effective_collection,
            )
            blocks = response.to_mcp_content()
            return types.CallToolResult(content=blocks, isError=response.is_empty and bool(response.metadata.get("error")))
        except Exception as e:
            logger.exception("keyword_search failed: %s", e)
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=f"Error: {e}")],
                isError=True,
            )


_tool_instance: Optional[KeywordSearchTool] = None


def get_tool_instance(settings: Optional[Settings] = None) -> KeywordSearchTool:
    global _tool_instance
    if _tool_instance is None:
        _tool_instance = KeywordSearchTool(settings=settings)
    return _tool_instance


async def keyword_search_handler(
    query: str,
    top_k: int = 5,
    collection: Optional[str] = None,
) -> types.CallToolResult:
    return await get_tool_instance().execute(query=query, top_k=top_k, collection=collection)


def register_tool(protocol_handler: Any) -> None:
    protocol_handler.register_tool(
        name=TOOL_NAME,
        description=TOOL_DESCRIPTION,
        input_schema=TOOL_INPUT_SCHEMA,
        handler=keyword_search_handler,
    )
    logger.info("Registered MCP tool: %s", TOOL_NAME)
