"""
Claude Code Decision Engine: Executes prompts via Claude CLI (`claude -p "..."`).
Allows the user to use Claude Code subscription without needing separate API credits.
"""

import json
import logging
import os
import shutil
import subprocess
from typing import Dict, Any, Optional
import pandas as pd

from arena.brains.base import DecisionEngine, Decision
from arena.config import get_config

logger = logging.getLogger("arena.brains.claude_code")

class ClaudeCodeEngine(DecisionEngine):
    """Bridge to locally installed Claude Code CLI."""

    def __init__(self, profile_name: str = "balanced"):
        super().__init__(name="Claude Code (CLI)", profile_name=profile_name)
        self.cli_path = shutil.which("claude") or shutil.which("claude.cmd")

    def is_available(self) -> bool:
        """Check if Claude CLI is accessible."""
        if not self.cli_path:
            return False
        try:
            res = subprocess.run([self.cli_path, "--version"], capture_output=True, text=True, timeout=3)
            return res.returncode == 0
        except Exception:
            return False

    def decide(self, symbol: str, current_price: float, history_df: Optional[pd.DataFrame] = None, context: Optional[Dict[str, Any]] = None) -> Decision:
        """Execute structured JSON prompt through Claude CLI."""
        if not self.is_available():
            return Decision(
                action="HOLD",
                symbol=symbol,
                quantity=0,
                price=current_price,
                confidence=0.0,
                reason="Claude CLI not detected or not in PATH",
                engine_name=self.name
            )

        # Build prompt
        prompt = (
            f"You are the trading decision engine in Breaking Money AI Trading Arena.\n"
            f"Stock: {symbol}, Current LTP: Rs {current_price:.2f}.\n"
            f"Risk Profile: {self.profile_name} (Max SL: {self.risk_profile.get('stop_loss_pct')}%, TP: {self.risk_profile.get('take_profit_pct')}%).\n"
            f"Context: {json.dumps(context or {})}.\n\n"
            f"Respond ONLY in valid JSON format with keys:\n"
            f'{{"action": "BUY"|"SELL"|"HOLD", "confidence": 0.0-1.0, "stop_loss": float, "take_profit": float, "reason": "brief rationale"}}'
        )

        try:
            cmd = [self.cli_path, "-p", prompt]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if proc.returncode == 0 and proc.stdout:
                out = proc.stdout.strip()
                # Extract JSON if enclosed in markdown
                if "```json" in out:
                    out = out.split("```json")[1].split("```")[0].strip()
                elif "```" in out:
                    out = out.split("```")[1].split("```")[0].strip()
                parsed = json.loads(out)
                action = parsed.get("action", "HOLD").upper()
                return Decision(
                    action=action if action in ["BUY", "SELL", "HOLD"] else "HOLD",
                    symbol=symbol,
                    quantity=0,
                    price=current_price,
                    stop_loss=parsed.get("stop_loss"),
                    take_profit=parsed.get("take_profit"),
                    confidence=float(parsed.get("confidence", 0.7)),
                    reason=parsed.get("reason", "Claude Code CLI analysis"),
                    engine_name=self.name
                )
        except Exception as e:
            logger.warning("Claude Code CLI execution failed: %s", e)

        return Decision(
            action="HOLD",
            symbol=symbol,
            quantity=0,
            price=current_price,
            confidence=0.0,
            reason="Claude Code execution timeout/error; holding",
            engine_name=self.name
        )
