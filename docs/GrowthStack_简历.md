# GrowthStack 项目经历（简历用）

> 项目名称：**GrowthStack**。提供精简版（RAG+Agent 侧重）、完整版（覆盖全项目）及简历骨架，可按岗位选用。

---

## 一、完整版（根据整个项目）

> 覆盖：摄取流水线、混合检索与重排、MCP 服务、Dashboard、可观测性、评估体系、Agent 扩展、可插拔架构、测试与持久化。适合需要全面展示项目体量时使用。

**GrowthStack** | [时间段] | [角色：如 独立开发 / 核心开发]

**背景**：企业知识分散于文档与内部系统，大模型无法直接利用私有知识，AI Agent 缺乏可靠检索易产生幻觉。本项目将 RAG 与 Agent 结合，设计并实现了一套模块化、可插拔的「检索增强型 Agent」框架：以 RAG 为 Agent 知识底座，通过 MCP 对外暴露检索工具与 Agent 问答，支持 Copilot/Claude 等直接调用；同时提供 Dashboard 管理、全链路可观测与自动化评估，形成从数据摄入、检索、评测到 Agent 调用的完整闭环。

**目标**：构建「RAG 赋能 Agent」的一体化服务——底层可插拔 RAG（Hybrid Search + Rerank + 智能摄取），中层 MCP 工具与 ReAct Agent，上层 Dashboard 与评测体系；通过多策略评测与三层测试保障检索质量与系统稳定性，便于在不同环境与业务下复用与迭代。

**过程**：
• **智能摄取**：设计五阶段流水线（Load → Split → Transform → Embed → Upsert），PDF 解析转 Markdown、语义切分、可选 LLM 增强（Chunk 重组/元数据注入/图片描述）、双路向量化（Dense + BM25）与幂等写入；SHA256 增量摄取降低重复处理成本，为检索与 Agent 提供高质量知识源
• **混合检索与重排**：实现 Hybrid Search（BM25 + Dense + RRF 融合），粗排召回 + 精排重排两段式架构，支持 Cross-Encoder/LLM Rerank 可插拔切换，精排失败自动回退，平衡查准率与可用性
• **MCP 与 RAG–Agent 桥接**：基于 MCP 标准（JSON-RPC + Stdio）实现知识检索 Server，暴露 query_knowledge_hub、list_collections、get_document_summary、keyword_search、semantic_search、agent_query 等工具；将检索封装为 Agent 可调用工具，ReAct Agent 多步 Thought–Action–Observation 调用检索后综合作答，形成「检索即工具、Agent 即编排」
• **可观测与可视化管理**：设计 Ingestion Trace + Query Trace 双链路追踪，阶段耗时与候选数量可回溯；基于 Streamlit 构建六页面 Dashboard（系统总览、数据浏览、摄取管理、摄取追踪、查询追踪、评估面板），实现 RAG 全生命周期管理与问题定位
• **评估与文档管理**：集成 Ragas + 自定义指标（HitRate/MRR 等），Golden Test Set 回归与多策略对比脚本（dense/bm25/hybrid/rerank/agent）输出 eval_results.csv；DocumentManager 协调 Chroma/BM25/图片/处理记录四路存储，支持列表、详情与协调删除，保障数据一致性
• **可插拔与工程化**：LLM/Embedding/VectorStore/Reranker 等 6 大组件抽象接口 + 工厂 + YAML 配置，4 种 LLM、3 种 Embedding 零代码切换；SQLite 轻量持久化零外部库依赖；Unit/Integration/E2E 三层测试 1200+ 用例，保障迭代稳定

**结果**：RAG 与 Agent 统一通过 MCP 对外服务；MCP 工具调用成功率 100%，检索 P95 延迟 &lt; 1s；支持 4 种 LLM、3 种 Embedding 配置切换；六页面 Dashboard 支撑数据与链路管理；评测框架支持 HitRate@5、MRR@10、NDCG@10 等多策略量化，便于持续优化「RAG 供给质量 → Agent 回答质量」。

**技术栈**：RAG、Retrieval-Augmented Agent、Hybrid Search、BM25、Dense、RRF、Rerank、MCP、ReAct、Chroma、Streamlit、Ragas、SQLite、Python

---

## 二、中文版（精简·RAG+Agent 侧重）

**GrowthStack** | [时间段按实际填写] | [角色：如 独立开发 / 核心开发]

**背景**：企业知识分散于文档与内部系统，单纯大模型无法直接利用私有知识；AI Agent 若缺乏高质量检索能力，易产生幻觉或答非所问。本项目将 RAG 与 Agent 深度结合，以 RAG 作为 Agent 的「知识底座」，设计并实现了一套「检索增强型 Agent」框架 GrowthStack：通过 MCP 协议对外统一暴露检索工具与 Agent 问答能力，使 Copilot、Claude 等 AI 助手既能单步查知识库，也能通过内置 Agent 多步调用检索工具后综合作答。

**目标**：构建「RAG 赋能 Agent」的一体化服务——底层提供可插拔、可观测的 RAG 检索（Hybrid Search + Rerank），上层将检索能力封装为 MCP 工具并接入 ReAct 风格 Agent，实现「先检索、再推理、再回答」的闭环；通过多策略评测（HitRate@5、MRR@10、NDCG@10）持续优化检索质量，保障 Agent 调用的知识来源可靠。

**过程**：
• **RAG 层**：设计并实现 Hybrid Search 混合检索引擎（BM25 + Dense + RRF + 可选 Cross-Encoder Rerank），粗排召回 + 精排重排两段式架构，精排失败自动回退；五阶段摄取流水线（Load → Split → Transform → Embed → Upsert）支撑高质量 Chunk 与双路向量化，为 Agent 提供稳定知识源
• **RAG–Agent 桥接**：基于 MCP 标准（JSON-RPC + Stdio）将检索能力封装为 MCP 工具（query_knowledge_hub、keyword_search、semantic_search），供上层 Agent 或外部 Copilot/Claude 按需调用；同一 Server 内同时暴露单步检索工具与 Agent 入口（agent_query），实现「检索即工具、Agent 即编排」
• **Agent 层**：实现 ReAct 风格 Agent，将 keyword_search / semantic_search 作为可调用工具，支持多步 Thought–Action–Observation 推理；用户通过 agent_query 发起复杂问句时，Agent 自动规划调用检索工具、汇总结果并生成回答，形成「RAG 检索 + Agent 推理」闭环
• 全链路可插拔架构（抽象接口 + 工厂 + YAML 配置），LLM / Embedding / Reranker 等 6 大组件零代码切换，4 种 LLM、3 种 Embedding 后端，满足 Agent 在不同环境下的模型选型与成本控制
• 建立 RAG 与 Agent 联合评测：Golden Query 集 + 五策略（dense_only / bm25_only / hybrid_rrf / hybrid_rrf_rerank / agent_query）自动化跑批，输出 HitRate@5、MRR@10、延迟、工具成功率至 eval_results.csv；三层测试（Unit / Integration / E2E）1200+ 用例，保障检索与 Agent 调用稳定性

**结果**：RAG 检索层与 Agent 层统一通过 MCP 对外服务，在 N=3 条 Golden Query 上五策略对比中 MCP 工具调用成功率 100%，检索端到端延迟 P95 &lt; 1s（hybrid_rrf 约 53–66ms，hybrid_rrf_rerank 约 139–625ms）；Agent 可基于单步/多步检索结果综合作答，支持 4 种 LLM、3 种 Embedding 零配置切换；评测框架可扩展至 HitRate@5、MRR@10、NDCG@10，便于持续优化「RAG 供给质量 → Agent 回答质量」的因果链。

**技术栈**：RAG、Retrieval-Augmented Agent、Hybrid Search、BM25、Dense Retrieval、RRF、Rerank、MCP、ReAct、Chroma、Streamlit、Ragas、Python

---

## 三、英文版（可选）

**GrowthStack** | [Time period] | [Role: e.g. Solo / Core Developer]

**Context**: Enterprise knowledge is scattered across docs and internal systems; LLMs alone cannot access it, and agents without reliable retrieval tend to hallucinate. I designed GrowthStack as a **RAG-augmented Agent** framework: RAG serves as the knowledge backbone for the agent, and both retrieval tools and agent QA are exposed via MCP so Copilot/Claude can either query the knowledge base directly or use the built-in ReAct agent to run multi-step retrieval and then answer.

**Goals**: Build an integrated “RAG powers Agent” service—pluggable, observable RAG at the bottom (Hybrid Search + Rerank), MCP tools and a ReAct-style agent on top that call those tools to “retrieve → reason → respond”; use HitRate@5, MRR@10, NDCG@10 to continuously improve retrieval so agent answers stay grounded.

**Approach**:
• **RAG layer**: Hybrid search (BM25 + Dense + RRF, optional Cross-Encoder rerank), two-stage retrieve-then-rerank with fallback; five-stage ingestion pipeline for high-quality chunks and dual indexing, providing a stable knowledge source for the agent
• **RAG–Agent bridge**: MCP-compliant server (JSON-RPC, Stdio) exposes retrieval as tools (query_knowledge_hub, keyword_search, semantic_search) and a single agent entry (agent_query), so “retrieval as tools, agent as orchestrator”
• **Agent layer**: ReAct-style agent with keyword_search / semantic_search as callable tools; multi-step Thought–Action–Observation for complex questions, combining retrieval results and generating answers in a RAG + Agent loop
• Pluggable pipeline (abstract interfaces, factory, YAML) for 6 components; 4 LLM and 3 Embedding backends, zero-code switch for different agent environments
• Joint RAG + Agent evaluation: golden query set, five strategies, automated batch → eval_results.csv (HitRate@5, MRR@10, latency, tool success); 1200+ tests (Unit / Integration / E2E) for retrieval and agent stability

**Results**: RAG and agent served through one MCP surface; on N=3 golden queries, MCP tool success rate 100%, retrieval P95 &lt; 1s (e.g. hybrid_rrf ~53–66ms, hybrid_rrf_rerank ~139–625ms). Agent answers from single- or multi-step retrieval; 4 LLM / 3 Embedding backends config-driven; evaluation ready for HitRate@5, MRR@10, NDCG@10 to optimize the “RAG quality → agent answer quality” chain.

**Tech**: RAG, Retrieval-Augmented Agent, Hybrid Search, BM25, Dense Retrieval, RRF, Rerank, MCP, ReAct, Chroma, Streamlit, Ragas, Python

---

## 四、量化结果填写说明

| 指标 | 当前来源 | 建议 |
|------|----------|------|
| N（Golden Query 数） | eval_queries.csv 行数 | 扩充到 20–50 条后更新 N |
| HitRate@5 / MRR@10 / NDCG@10 | 需在 eval_queries.csv 中填写 gold_chunk_ids 后重跑 `python scripts/run_eval.py` | 跑出结果后替换「评测框架可扩展至…」为具体数值，如「HitRate@5 达 92%，MRR@10 提升 18%」 |
| 工具调用成功率 | 实测 15/15 = 100% | 保持或随样本量更新 |
| 延迟 P95 / 平均延迟 | 来自 eval_results.csv（当前 hybrid_rrf 约 53–66ms，rerank 约 139–625ms） | 样本增多后可改为 P95 &lt; 800ms 等 |
| 测试用例数 | 项目约 1200+ | 可写 1200+ 或实际 `pytest --co -q` 数量 |

将「结果」段中的数字按上表替换为你的实测值后，即可直接用于简历与面试表述。

---

## 五、简历骨架（整份简历结构）

> 以下为可复用的简历框架，将「项目经历」替换为上文「一、完整版」或「二、中文版」内容即可。

```
────────────────────────────────────────
[姓名]  |  手机：__________  邮箱：__________
────────────────────────────────────────

【教育背景】
[学校]  [专业]  [学历]  [起止时间]
（可选：主修课程、荣誉）

【专业技能】
• 语言与框架：Python、[按岗位补充：FastAPI / PyTorch / LangChain 等]
• RAG / LLM：检索增强生成、混合检索（BM25 + Dense）、Rerank、MCP、Agent
• 工程与工具：Git、YAML 配置、单元/集成/E2E 测试、Streamlit
• 其他：[按岗位补充]

【项目经历】

  GrowthStack  |  [起止时间]  |  [角色]

  背景：[粘贴「一、完整版」或「二、中文版」的背景段]

  目标：[粘贴目标段]

  过程：
  • [粘贴过程 bullet 1]
  • [粘贴过程 bullet 2]
  • …

  结果：[粘贴结果段]

  技术栈：[粘贴技术栈]

  ────────────────────────────────────────
  （其他项目同上格式）
  ────────────────────────────────────────

【其他】
• 获奖 / 论文 / 开源贡献 / 自我评价（选填）
────────────────────────────────────────
```
