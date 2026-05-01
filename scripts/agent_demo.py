#!/usr/bin/env python3
"""Demo script for the embedded ReAct Agent.

Runs the agent locally without MCP: useful for testing and debugging.

Usage:
    python scripts/agent_demo.py --query "YANG的基本信息是什么"
    python scripts/agent_demo.py --query "What is RAG?" --collection default
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.react_agent import run_agent
from src.core.settings import load_settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Run embedded Agent (no MCP)")
    parser.add_argument("--query", "-q", required=True, help="User question")
    parser.add_argument("--collection", "-c", default="default", help="Collection name")
    parser.add_argument("--max-steps", type=int, default=5, help="Max tool-call rounds")
    args = parser.parse_args()

    settings = load_settings()
    print("Running Agent...")
    result = run_agent(
        query=args.query,
        collection=args.collection,
        max_steps=args.max_steps,
        settings=settings,
    )
    print("\n--- Final Answer ---\n")
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
