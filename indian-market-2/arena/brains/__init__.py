"""
Decision Engines Module: Factory for instantiating trading brains.
"""

from typing import Optional
from arena.brains.base import DecisionEngine, Decision
from arena.brains.rules import RulesEngine
from arena.brains.claude_code import ClaudeCodeEngine
from arena.brains.anthropic_api import AnthropicAPIEngine
from arena.brains.auto import AutoFallbackEngine

def get_engine(brain_name: Optional[str] = None, profile_name: str = "balanced") -> DecisionEngine:
    name = (brain_name or "auto").lower().strip()
    if name in ["claude-code", "claudecode", "cli"]:
        return ClaudeCodeEngine(profile_name)
    elif name in ["claude-api", "anthropic-api", "api"]:
        return AnthropicAPIEngine(profile_name)
    elif name in ["rules", "baseline", "orb"]:
        return RulesEngine(profile_name)
    else:
        return AutoFallbackEngine(profile_name)

__all__ = [
    "DecisionEngine",
    "Decision",
    "RulesEngine",
    "ClaudeCodeEngine",
    "AnthropicAPIEngine",
    "AutoFallbackEngine",
    "get_engine"
]
