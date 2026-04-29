"""MCP Tool: semantic_search

Semantic (embedding) search only. Exposed for Agent and clients
that want dense retrieval without BM25.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from mcp import types

from src.core.response.response_builder import ResponseBuilder
from src.core.settings import load_settings
from src.core.types import RetrievalResult

if TYPE_CHECKING:
    from src.core.settings import Settings

logger = logging.getLogger(__name__)

TOOL_NAME = "semantic_search"
TOOL_DESCRIPTION = """Search the knowledge base by semantic similarity (embeddings).

Use this for conceptual or paraphrased questions where keyword match
may miss relevant content. Does not use BM25 keywords.

Parameters:
- query: Natural language search query
- top_k: Maximum number of results (default: 5)
- collection: Optional collection name (default: default)
"""

TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Natural language query for semantic similarity search.",
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


class SemanticSearchTool:
    """MCP Tool for semantic-only (dense) search."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        response_builder: Optional[ResponseBuilder] = None,
    ) -> None:
        self._settings = settings
        self._response_builder = response_builder or ResponseBuilder()
        self._embedding_client = None
        self._dense_retriever = None
        self._current_collection: Optional[str] = None

    @property
    def settings(self) -> Settings:
        if self._settings is None:
            self._settings = load_settings()
        return self._settings

    def _ensure_initialized(self, collection: str) -> None:
        if self._current_collection == collection and self._dense_retriever is not None:
            return
        from src.core.query_engine.dense_retriever import create_dense_retriever
        from src.libs.embedding.embedding_factory import EmbeddingFactory
        from src.libs.vector_store.vector_store_factory import VectorStoreFactory

        if self._embedding_client is None:
            self._embedding_client = EmbeddingFactory.create(self.settings)
        vector_store = VectorStoreFactory.create(
            self.settings,
            collection_name=collection,
        )
        self._dense_retriever = create_dense_retriever(
            settings=self.settings,
            embedding_client=self._embedding_client,
            vector_store=vector_store,
        )
        self._current_collection = collection
        logger.info("SemanticSearchTool initialized for collection=%s", collection)

    def _search(
        self,
        query: str,
        top_k: int,
        collection: str,
    ) -> List[RetrievalResult]:
        self._ensure_initialized(collection)
        return self._dense_retriever.retrieve(
            query=query,
            top_k=top_k,
            filters=None,
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
            return types.CallToolResult(
                content=blocks,
                isError=response.is_empty and bool(response.metadata.get("error")),
            )
        except Exception as e:
            logger.exception("semantic_search failed: %s", e)
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=f"Error: {e}")],
                isError=True,
            )


_tool_instance: Optional[SemanticSearchTool] = None


def get_tool_instance(settings: Optional[Settings] = None) -> SemanticSearchTool:
    global _tool_instance
    if _tool_instance is None:
        _tool_instance = SemanticSearchTool(settings=settings)
    return _tool_instance


async def semantic_search_handler(
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
        handler=semantic_search_handler,
    )
    logger.info("Registered MCP tool: %s", TOOL_NAME)
