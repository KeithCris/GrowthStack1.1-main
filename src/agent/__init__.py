"""Embedded ReAct Agent for multi-step knowledge retrieval.

This package provides an in-process Agent that can call keyword_search
and semantic_search tools to answer user questions.
"""

from src.agent.react_agent import run_agent

__all__ = ["run_agent"]
