"""ReAct Agent prompt templates."""

REACT_SYSTEM = """You are a helpful assistant with access to a knowledge base. You must answer the user's question using the tools provided.

Available tools:
1. keyword_search(query, top_k=5, collection="default") - Search by keywords (BM25). Use for exact terms, names, IDs.
2. semantic_search(query, top_k=5, collection="default") - Search by meaning (embeddings). Use for conceptual or paraphrased questions.

You must respond in this exact format each turn:
Thought: [your reasoning]
Action: tool_name(query="...", top_k=5)
Observation: [will be filled by the system after the tool runs]

When you have enough information to answer the user, respond with:
Thought: [final reasoning]
Final Answer: [your complete answer to the user]

Rules:
- Use Action only with one of: keyword_search, semantic_search.
- Always use valid tool name and put arguments in parentheses, e.g. keyword_search(query="Azure 配置", top_k=5).
- After seeing Observation, either use another Action or give Final Answer.
- Give Final Answer in the same language as the user's question.
"""


def build_react_prompt(user_query: str, history: str) -> str:
    """Build the user-side prompt for the next ReAct step.

    Args:
        user_query: Original user question.
        history: Concatenated previous Thought/Action/Observation turns.

    Returns:
        Full user message string.
    """
    parts = [f"User question: {user_query}"]
    if history.strip():
        parts.append("")
        parts.append("Previous turns:")
        parts.append(history)
    parts.append("")
    parts.append("Respond with Thought, then either Action or Final Answer.")
    return "\n".join(parts)
