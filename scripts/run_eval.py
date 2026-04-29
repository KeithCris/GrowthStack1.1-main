#!/usr/bin/env python3
"""RAG/Agent 评测脚本：读取 eval_queries.csv，跑 5 种策略，输出 eval_results.csv。

使用前请先：
1. 在 data/eval/eval_queries.csv 中填写 gold_chunk_ids（可从 Dashboard 或单次查询结果中抄录 chunk_id）
2. 确保知识库已摄入数据（默认 collection: default）

用法:
    python scripts/run_eval.py
    python scripts/run_eval.py --queries data/eval/eval_queries.csv --out data/eval/eval_results.csv
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

COLLECTION = "default"
TOP_K = 10
QUERY_TIMEOUT_SEC = 30
STRATEGIES = ["dense_only", "bm25_only", "hybrid_rrf", "hybrid_rrf_rerank", "agent_query"]


def _parse_gold_chunk_ids(s: str) -> list[str]:
    if not s or not str(s).strip():
        return []
    return [x.strip() for x in str(s).replace(";", ",").split(",") if x.strip()]


def hit_at_k(retrieved_ids: list[str], gold_ids: list[str], k: int) -> int:
    if not gold_ids:
        return 0
    top_k = retrieved_ids[:k]
    return 1 if any(g in top_k for g in gold_ids) else 0


def mrr_at_k(retrieved_ids: list[str], gold_ids: list[str], k: int) -> float:
    if not gold_ids:
        return 0.0
    for i, rid in enumerate(retrieved_ids[:k]):
        if rid in gold_ids:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(retrieved_ids: list[str], gold_ids: list[str], k: int) -> float:
    if not gold_ids:
        return 0.0
    dcg = 0.0
    for i, rid in enumerate(retrieved_ids[:k]):
        if rid in gold_ids:
            dcg += 1.0 / math.log2(i + 2)
    if dcg == 0:
        return 0.0
    idcg = 1.0 / math.log2(2)  # single relevant doc
    return dcg / idcg


def _ensure_components(collection: str):
    from src.core.settings import load_settings, resolve_path
    from src.core.query_engine.dense_retriever import create_dense_retriever
    from src.core.query_engine.sparse_retriever import create_sparse_retriever
    from src.core.query_engine.hybrid_search import create_hybrid_search
    from src.core.query_engine.query_processor import QueryProcessor
    from src.core.query_engine.reranker import create_core_reranker
    from src.ingestion.storage.bm25_indexer import BM25Indexer
    from src.libs.embedding.embedding_factory import EmbeddingFactory
    from src.libs.vector_store.vector_store_factory import VectorStoreFactory

    settings = load_settings()
    embedding_client = EmbeddingFactory.create(settings)
    vector_store = VectorStoreFactory.create(settings, collection_name=collection)
    dense_retriever = create_dense_retriever(
        settings=settings,
        embedding_client=embedding_client,
        vector_store=vector_store,
    )
    bm25_indexer = BM25Indexer(index_dir=str(resolve_path(f"data/db/bm25/{collection}")))
    sparse_retriever = create_sparse_retriever(
        settings=settings,
        bm25_indexer=bm25_indexer,
        vector_store=vector_store,
    )
    sparse_retriever.default_collection = collection
    query_processor = QueryProcessor()
    hybrid_search = create_hybrid_search(
        settings=settings,
        query_processor=query_processor,
        dense_retriever=dense_retriever,
        sparse_retriever=sparse_retriever,
    )
    reranker = create_core_reranker(settings=settings)
    return {
        "collection": collection,
        "settings": settings,
        "dense_retriever": dense_retriever,
        "sparse_retriever": sparse_retriever,
        "query_processor": query_processor,
        "hybrid_search": hybrid_search,
        "reranker": reranker,
    }


def run_dense(query: str, top_k: int, comp: dict) -> tuple[list[str], float, bool]:
    start = time.perf_counter()
    try:
        results = comp["dense_retriever"].retrieve(query=query, top_k=top_k)
        elapsed = (time.perf_counter() - start) * 1000
        return [r.chunk_id for r in results], elapsed, True
    except Exception:
        return [], (time.perf_counter() - start) * 1000, False


def run_bm25(query: str, top_k: int, comp: dict) -> tuple[list[str], float, bool]:
    start = time.perf_counter()
    try:
        qp = comp["query_processor"].process(query)
        keywords = qp.keywords or [q.strip() for q in query.split() if q.strip()][:10]
        if not keywords:
            return [], (time.perf_counter() - start) * 1000, False
        results = comp["sparse_retriever"].retrieve(
            keywords=keywords, top_k=top_k, collection=comp["collection"]
        )
        elapsed = (time.perf_counter() - start) * 1000
        return [r.chunk_id for r in results], elapsed, True
    except Exception:
        return [], (time.perf_counter() - start) * 1000, False


def run_hybrid_rrf(query: str, top_k: int, comp: dict) -> tuple[list[str], float, bool]:
    start = time.perf_counter()
    try:
        out = comp["hybrid_search"].search(query=query, top_k=top_k)
        results = out.results if hasattr(out, "results") else out
        elapsed = (time.perf_counter() - start) * 1000
        return [r.chunk_id for r in results], elapsed, True
    except Exception:
        return [], (time.perf_counter() - start) * 1000, False


def run_hybrid_rrf_rerank(query: str, top_k: int, comp: dict) -> tuple[list[str], float, bool]:
    start = time.perf_counter()
    try:
        out = comp["hybrid_search"].search(query=query, top_k=top_k * 2)
        results = out.results if hasattr(out, "results") else out
        if comp["reranker"].is_enabled and results:
            from src.core.types import RetrievalResult
            rr = comp["reranker"].rerank(query=query, results=results, top_k=top_k)
            results = rr.results
        else:
            results = results[:top_k]
        elapsed = (time.perf_counter() - start) * 1000
        return [r.chunk_id for r in results], elapsed, True
    except Exception:
        return [], (time.perf_counter() - start) * 1000, False


def run_agent_query(query: str, comp: dict) -> tuple[list[str], float, bool, int]:
    from src.agent.react_agent import run_agent
    start = time.perf_counter()
    try:
        run_agent(
            query=query,
            collection=comp["collection"],
            max_steps=5,
            settings=comp["settings"],
        )
        elapsed = (time.perf_counter() - start) * 1000
        return [], elapsed, True, 0  # agent_steps 暂不统计，可后续扩展 run_agent 返回
    except Exception:
        return [], (time.perf_counter() - start) * 1000, False, 0


def load_queries(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Run RAG/Agent evaluation")
    parser.add_argument(
        "--queries",
        type=Path,
        default=ROOT / "data" / "eval" / "eval_queries.csv",
        help="Path to eval_queries.csv",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data" / "eval" / "eval_results.csv",
        help="Path to write eval_results.csv",
    )
    parser.add_argument("--collection", default=COLLECTION, help="Collection name")
    args = parser.parse_args()
    collection = args.collection

    if not args.queries.exists():
        print(f"Queries file not found: {args.queries}", file=sys.stderr)
        return 1

    queries = load_queries(args.queries)
    if not queries:
        print("No rows in eval_queries.csv", file=sys.stderr)
        return 1

    print("Initializing components for collection:", collection)
    comp = _ensure_components(collection)

    results_dir = args.out.parent
    results_dir.mkdir(parents=True, exist_ok=True)

    out_rows = []
    for qrow in queries:
        query_id = qrow.get("query_id", "")
        query = qrow.get("query", "").strip()
        gold_chunk_ids = _parse_gold_chunk_ids(qrow.get("gold_chunk_ids", ""))
        if not query:
            continue
        for strategy in STRATEGIES:
            hit_5, mrr_10, ndcg_10 = 0, 0.0, 0.0
            latency_ms, timeout, tool_success = 0.0, 0, 0
            agent_steps = 0
            if strategy == "dense_only":
                ids, latency_ms, tool_success = run_dense(query, TOP_K, comp)
                hit_5 = hit_at_k(ids, gold_chunk_ids, 5)
                mrr_10 = mrr_at_k(ids, gold_chunk_ids, 10)
                ndcg_10 = ndcg_at_k(ids, gold_chunk_ids, 10)
            elif strategy == "bm25_only":
                ids, latency_ms, tool_success = run_bm25(query, TOP_K, comp)
                hit_5 = hit_at_k(ids, gold_chunk_ids, 5)
                mrr_10 = mrr_at_k(ids, gold_chunk_ids, 10)
                ndcg_10 = ndcg_at_k(ids, gold_chunk_ids, 10)
            elif strategy == "hybrid_rrf":
                ids, latency_ms, tool_success = run_hybrid_rrf(query, TOP_K, comp)
                hit_5 = hit_at_k(ids, gold_chunk_ids, 5)
                mrr_10 = mrr_at_k(ids, gold_chunk_ids, 10)
                ndcg_10 = ndcg_at_k(ids, gold_chunk_ids, 10)
            elif strategy == "hybrid_rrf_rerank":
                ids, latency_ms, tool_success = run_hybrid_rrf_rerank(query, TOP_K, comp)
                hit_5 = hit_at_k(ids, gold_chunk_ids, 5)
                mrr_10 = mrr_at_k(ids, gold_chunk_ids, 10)
                ndcg_10 = ndcg_at_k(ids, gold_chunk_ids, 10)
            else:  # agent_query
                _, latency_ms, tool_success, agent_steps = run_agent_query(query, comp)
                timeout = 1 if latency_ms > QUERY_TIMEOUT_SEC * 1000 else 0
            out_rows.append({
                "query_id": query_id,
                "strategy": strategy,
                "top_k": TOP_K,
                "hit_at_5": hit_5,
                "mrr_at_10": round(mrr_10, 4),
                "ndcg_at_10": round(ndcg_10, 4),
                "latency_ms": round(latency_ms, 2),
                "timeout": timeout,
                "tool_success": 1 if tool_success else 0,
                "agent_steps": agent_steps,
                "notes": "",
            })

    fieldnames = [
        "query_id", "strategy", "top_k", "hit_at_5", "mrr_at_10", "ndcg_at_10",
        "latency_ms", "timeout", "tool_success", "agent_steps", "notes",
    ]
    with args.out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"Wrote {len(out_rows)} rows to {args.out}")

    # 简单汇总：按策略聚合
    by_strategy = {}
    for r in out_rows:
        s = r["strategy"]
        if s not in by_strategy:
            by_strategy[s] = {"hit_at_5": [], "mrr_at_10": [], "latency_ms": [], "success": []}
        by_strategy[s]["hit_at_5"].append(r["hit_at_5"])
        by_strategy[s]["mrr_at_10"].append(r["mrr_at_10"])
        by_strategy[s]["latency_ms"].append(r["latency_ms"])
        by_strategy[s]["success"].append(r["tool_success"])
    print("\n--- 按策略汇总 ---")
    for s in STRATEGIES:
        if s not in by_strategy:
            continue
        d = by_strategy[s]
        n = len(d["hit_at_5"])
        if not n:
            continue
        hit_avg = sum(d["hit_at_5"]) / n
        mrr_avg = sum(d["mrr_at_10"]) / n
        lat_avg = sum(d["latency_ms"]) / n
        succ = sum(d["success"]) / n
        if s == "agent_query":
            print(f"  {s}: Latency_avg={lat_avg:.0f}ms Success={succ:.2%} (Hit/MRR 不适用)")
        else:
            print(f"  {s}: HitRate@5={hit_avg:.2%} MRR@10={mrr_avg:.4f} Latency_avg={lat_avg:.0f}ms Success={succ:.2%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
