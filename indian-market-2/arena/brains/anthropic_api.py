"""
Anthropic API Decision Engine: Direct API calls using ANTHROPIC_API_KEY.
"""

import json
import logging
import os
from typing import Dict, Any, Optional
import pandas as pd
import requests

from arena.brains.base import DecisionEngine, Decision
from arena.config import get_config

logger = logging.getLogger("arena.brains.anthropic_api")

class AnthropicAPIEngine(DecisionEngine):
    """Bridge to Anthropic Claude 3.5 Sonnet / Haiku via REST API."""

    def __init__(self, profile_name: str = "balanced"):
        super().__init__(name="Anthropic API (Claude 3.5)", profile_name=profile_name)
        cfg = get_config()
        self.api_key = cfg.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.model = "claude-3-5-sonnet-20241022"
        self.api_url = "https://api.anthropic.com/v1/messages"

    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 10)

    def decide(self, symbol: str, current_price: float, history_df: Optional[pd.DataFrame] = None, context: Optional[Dict[str, Any]] = None) -> Decision:
        if not self.is_available():
            return Decision(
                action="HOLD",
                symbol=symbol,
                quantity=0,
                price=current_price,
                confidence=0.0,
                reason="ANTHROPIC_API_KEY missing or invalid in .env / environment",
                engine_name=self.name
            )

        system_prompt = (
            "You are an expert quantitative trader managing an intraday trading portfolio in the Indian Stock Market (NSE).\n"
            "Analyze the given setup and respond STRICTLY with a valid JSON object with the following schema:\n"
            '{"action": "BUY"|"SELL"|"HOLD", "confidence": float (0.0 to 1.0), "stop_loss": float, "take_profit": float, "reason": "concise rationale"}\n'
            "No markdown wrapping outside the JSON, no explanations before or after."
        )

        user_prompt = (
            f"Stock: {symbol}\n"
            f"Current Price: Rs {current_price:.2f}\n"
            f"Risk Profile: {self.profile_name} (Stop Loss: {self.risk_profile.get('stop_loss_pct')}%, Target: {self.risk_profile.get('take_profit_pct')}%)\n"
            f"Context: {json.dumps(context or {})}\n"
        )

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        payload = {
            "model": self.model,
            "max_tokens": 200,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt}
            ]
        }

        try:
            resp = requests.post(self.api_url, headers=headers, json=payload, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                content_text = data["content"][0]["text"].strip()
                if "```json" in content_text:
                    content_text = content_text.split("```json")[1].split("```")[0].strip()
                elif "```" in content_text:
                    content_text = content_text.split("```")[1].split("```")[0].strip()

                parsed = json.loads(content_text)
                action = parsed.get("action", "HOLD").upper()
                return Decision(
                    action=action if action in ["BUY", "SELL", "HOLD"] else "HOLD",
                    symbol=symbol,
                    quantity=0,
                    price=current_price,
                    stop_loss=parsed.get("stop_loss"),
                    take_profit=parsed.get("take_profit"),
                    confidence=float(parsed.get("confidence", 0.8)),
                    reason=parsed.get("reason", "Anthropic Claude analysis"),
                    engine_name=self.name
                )
            else:
                logger.warning("Anthropic API returned status %s: %s", resp.status_code, resp.text)
        except Exception as e:
            logger.error("Anthropic API request failed: %s", e)

        return Decision(
            action="HOLD",
            symbol=symbol,
            quantity=0,
            price=current_price,
            confidence=0.0,
            reason="Anthropic API request failed; safe HOLD",
            engine_name=self.name
        )
