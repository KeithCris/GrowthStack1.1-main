# RAG / Agent 评测计划（简历量化版）

> 目标：给项目产出可写进简历的量化指标（HitRate、MRR、Latency、成功率等）。

---

## 1. 评测目标

- 验证不同检索策略效果差异：`Dense` vs `BM25` vs `Hybrid` vs `Hybrid+Rerank` vs `Agent`。
- 产出可复现的离线指标与线上性能指标。
- 建立坏案例回归机制，支持持续优化。

---

## 2. 数据集设计（Golden Set）

### 2.1 最小规模
- 建议先做 `50` 条问题，后续扩展到 `100~200` 条。

### 2.2 问题类型分布（建议）
- 关键词精确匹配（人名/术语/编号）：30%
- 语义改写问题（同义表达）：30%
- 多约束问题（时间+对象+条件）：25%
- 模糊问题（开放式问法）：15%

### 2.3 标注字段（每题）
- `query_id`
- `query`
- `intent_type`（keyword/semantic/multi-constraint/open）
- `gold_doc_id`（可多值）
- `gold_chunk_id`（可多值）
- `must_have_terms`（可选）

---

## 3. 对比策略

对每条 query 运行以下策略并记录结果：

1. `dense_only`
2. `bm25_only`
3. `hybrid_rrf`
4. `hybrid_rrf_rerank`
5. `agent_query`

---

## 4. 核心指标

## 4.1 检索质量
- `HitRate@K`（K=3/5/10）
- `MRR@10`
- `NDCG@10`
- `Recall@10`

## 4.2 体验性能
- `P50 / P95 Latency`（ms）
- `TimeoutRate`（%）
- `AvgAgentSteps`（仅 agent）

## 4.3 工程稳定性
- `ToolSuccessRate`（MCP 调用成功率）
- `FallbackRate`（rerank fallback 比例）
- `ErrorRate`（异常率）

---

## 5. 记录模板（CSV）

建议文件：`data/eval/eval_queries.csv`

```csv
query_id,query,intent_type,gold_doc_ids,gold_chunk_ids,must_have_terms
Q001,梁一恒的基本信息是什么,keyword,doc_1,chunk_1,"梁一恒;深圳"
Q002,这个人的教育背景如何,semantic,doc_1,chunk_1,"硕士;本科"
Q003,他的工作技能有哪些,multi-constraint,doc_1,chunk_2,"SQL;Python"
```

建议文件：`data/eval/eval_results.csv`

```csv
query_id,strategy,top_k,hit_at_5,mrr_at_10,ndcg_at_10,latency_ms,timeout,tool_success,agent_steps,notes
Q001,dense_only,10,1,1.0,1.0,640,0,1,0,
Q001,bm25_only,10,1,1.0,1.0,210,0,1,0,
Q001,hybrid_rrf,10,1,1.0,1.0,780,0,1,0,
Q001,hybrid_rrf_rerank,10,1,1.0,1.0,1150,0,1,0,
Q001,agent_query,10,1,1.0,1.0,1690,0,1,2,
```

---

## 6. 执行步骤（你可以照着跑）

1. 准备 `data/eval/eval_queries.csv`（先 50 条）。**务必填写 `gold_chunk_ids`**：从 Dashboard 或 `query_knowledge_hub` 单次查询结果里抄录 chunk_id（多个用分号或逗号分隔）。
2. 运行评测脚本（已提供）：
   ```bash
   python scripts/run_eval.py
   # 或指定路径
   python scripts/run_eval.py --queries data/eval/eval_queries.csv --out data/eval/eval_results.csv
   ```
   脚本会按 5 种策略跑完所有 query，并写入 `data/eval/eval_results.csv`，同时在终端打印按策略汇总的 HitRate@5、MRR@10、平均延迟、成功率。
3. 根据 `eval_results.csv` 聚合计算各策略指标（均值），填入下文「结果汇总模板」。
4. 输出一页评测报告（表格+结论）。
5. 固化 20 条 bad case 做回归。

---

## 7. 结果汇总模板（简历可直接引用）

把最终数字填进下面模板：

- 在 `N=__` 条 Golden Query 上，对比 `dense_only / bm25_only / hybrid / hybrid+rerank / agent` 五种策略，`HitRate@5` 从 `__` 提升至 `__`，`MRR@10` 提升 `__%`。
- 在本地部署下，查询 `P95` 延迟为 `__ ms`，MCP 工具调用成功率 `__%`，Agent 平均工具调用步数 `__`。
- 引入 rerank 与多步 Agent 后，复杂问题一次命中率提升 `__%`，bad case 数量下降 `__%`。

---

## 8. 简历建议值（还没跑数据时可用，后续替换）

> 注意：以下是建议区间，面试前尽量替换为你实测值。

- `HitRate@5`：+10% ~ +25%
- `MRR@10`：+8% ~ +20%
- `P95`：< 2.0s（小规模本地）
- `ToolSuccessRate`：> 99%
- `AvgAgentSteps`：1.5 ~ 2.5

---

## 9. 为什么这套评测能打动面试官

- 有基线：不是“只展示功能”，而是明确对比策略。
- 有指标：质量、性能、稳定性三条线齐全。
- 有闭环：bad case 回归体现工程迭代能力。
- 有业务映射：指标可直接对应“检索更准/响应更快/可用性更稳”。

