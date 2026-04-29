"""ReAct loop: LLM decides tool calls until Final Answer or max_steps."""

from __future__ import annotations

import logging
import re
from typing import Optional

from src.agent.prompts import REACT_SYSTEM, build_react_prompt
from src.agent.tools import parse_action, run_tool
from src.core.settings import load_settings
from src.libs.llm import LLMFactory
from src.libs.llm.base_llm import Message

logger = logging.getLogger(__name__)

# Default max steps to avoid infinite loops
DEFAULT_MAX_STEPS = 5


def _extract_final_answer(content: str) -> Optional[str]:
    """Extract text after 'Final Answer:' in LLM output."""
    if not content:
        return None
    # Case-insensitive, allow for colon variations
    match = re.search(r"Final\s+Answer\s*:\s*(.+)", content, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def _extract_action_line(content: str) -> Optional[str]:
    """Extract the line that starts with 'Action:'."""
    if not content:
        return None
    for line in content.split("\n"):
        line = line.strip()
        if line.lower().startswith("action:"):
            return line
    return None


def run_agent(
    query: str,
    collection: str = "default",
    max_steps: int = DEFAULT_MAX_STEPS,
    settings=None,
) -> str:
    """Run the ReAct agent until Final Answer or max_steps.

    Args:
        query: User question.
        collection: Knowledge base collection name.
        max_steps: Maximum number of tool-call rounds.
        settings: Optional Settings; if None, load from default path.

    Returns:
        Final answer string.
    """
    if settings is None:
        settings = load_settings()
    llm = LLMFactory.create(settings)
    history: str = ""
    last_response = ""

    for step in range(max_steps):
        user_content = build_react_prompt(query, history)
        messages = [
            Message(role="system", content=REACT_SYSTEM),
            Message(role="user", content=user_content),
        ]
        try:
            response = llm.chat(messages)
            last_response = response.content or ""
        except Exception as e:
            logger.exception("LLM call failed: %s", e)
            return f"Agent error: LLM call failed ({e})."
        if not last_response.strip():
            return "Agent error: empty LLM response."

        # Check for Final Answer first
        final = _extract_final_answer(last_response)
        if final is not None:
            logger.info("Agent finished with Final Answer at step %s", step + 1)
            return final

        # Otherwise look for Action
        action_line = _extract_action_line(last_response)
        if action_line is None:
            # No Action and no Final Answer: treat last response as answer or ask to retry
            if step + 1 >= max_steps:
                return last_response.strip()
            history += "\n\n" + last_response + "\n\nObservation: No valid Action or Final Answer. Please give Final Answer or a valid Action."
            continue

        parsed = parse_action(action_line)
        if parsed is None:
            history += "\n\n" + last_response + "\n\nObservation: Could not parse Action. Use format: Action: tool_name(query=\"...\", top_k=5)"
            continue
        tool_name, kwargs = parsed
        observation = run_tool(tool_name, kwargs, collection=collection)
        history += "\n\n" + last_response + "\n\nObservation: " + observation

    # Max steps reached without Final Answer
    final = _extract_final_answer(last_response)
    if final is not None:
        return final
    return last_response.strip() or "Agent reached max steps without a final answer."
