"""
Base Decision Engine Interface for The AI Trading Arena.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import pandas as pd
from arena.config import get_config

@dataclass
class Decision:
    action: str              # "BUY", "SELL", "HOLD"
    symbol: str
    price: float
    quantity: int = 0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    target: Optional[float] = None  # alias
    confidence: float = 0.0
    reason: str = ""
    reasoning: str = ""             # alias
    engine_name: str = "Base"
    metrics: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.target is not None and self.take_profit is None:
            self.take_profit = self.target
        elif self.take_profit is not None and self.target is None:
            self.target = self.take_profit

        if self.reason and not self.reasoning:
            self.reasoning = self.reason
        elif self.reasoning and not self.reason:
            self.reason = self.reasoning

class DecisionEngine:
    """Base class for all AI Arena decision engines."""

    def __init__(self, name: str = "Base", profile_name: str = "balanced"):
        self.name = name
        self.profile_name = profile_name
        cfg = get_config()
        self.risk_profile = cfg.get_risk_profile(profile_name)

    def is_available(self) -> bool:
        """Override to check environment / API key availability."""
        return True

    def decide(self, symbol: str, current_price: float, history_df: Optional[pd.DataFrame] = None, context: Optional[Dict[str, Any]] = None) -> Decision:
        raise NotImplementedError
