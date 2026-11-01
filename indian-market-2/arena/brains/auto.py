"""
Auto-Fallback Decision Engine.
Priority cascade:
1. Claude Code (CLI logged in)
2. Anthropic API (ANTHROPIC_API_KEY)
3. Rules Baseline (deterministic ORB/EMA/RSI)
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd

from arena.brains.base import DecisionEngine, Decision
from arena.brains.claude_code import ClaudeCodeEngine
from arena.brains.anthropic_api import AnthropicAPIEngine
from arena.brains.rules import RulesEngine

logger = logging.getLogger("arena.brains.auto")

class AutoFallbackEngine(DecisionEngine):
    """Dynamically chooses best available engine with zero configuration requirement."""

    def __init__(self, profile_name: str = "balanced"):
        super().__init__(name="Auto Engine", profile_name=profile_name)
        self.claude_code = ClaudeCodeEngine(profile_name)
        self.anthropic_api = AnthropicAPIEngine(profile_name)
        self.rules = RulesEngine(profile_name)
        self._active_engine: Optional[DecisionEngine] = None

    def get_selected_engine(self) -> DecisionEngine:
        if self.claude_code.is_available():
            return self.claude_code
        elif self.anthropic_api.is_available():
            return self.anthropic_api
        else:
            return self.rules

    def is_available(self) -> bool:
        return True

    @property
    def current_engine_name(self) -> str:
        return self.get_selected_engine().name

    def decide(self, symbol: str, current_price: float, history_df: Optional[pd.DataFrame] = None, context: Optional[Dict[str, Any]] = None) -> Decision:
        engine = self.get_selected_engine()
        self._active_engine = engine
        decision = engine.decide(symbol, current_price, history_df, context)
        # Tag that auto mode delegated to this engine
        decision.engine_name = f"Auto ({engine.name})"
        return decision
