# -*- coding: utf-8 -*-
"""
Paper Trading Engine for J1 Trader Indian Stock Market Portal.
Simulates trade execution with persistent JSON storage.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import pytz

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")

PORTFOLIO_FILE = os.path.join(os.path.dirname(__file__), "paper_portfolio.json")
INITIAL_CASH = 100_000  # INR 1,00,000


def _now_ist_str() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")


class PaperTradingEngine:
    """
    Simulated (paper) trading engine with persistent JSON storage.

    Portfolio JSON schema:
    {
        "cash": float,
        "holdings": [
            {
                "symbol": str,
                "nse_name": str,
                "direction": "BUY" | "SELL",
                "entry_price": float,
                "quantity": int,
                "stop_loss": float,
                "target_price": float,
                "signal_type": str,
                "opened_at": str,
                "unrealized_pnl": float,
                "current_price": float
            }
        ],
        "closed_trades": [
            {
                "symbol": str,
                "nse_name": str,
                "direction": str,
                "entry_price": float,
                "exit_price": float,
                "quantity": int,
                "pnl": float,
                "pnl_pct": float,
                "reason": str,
                "opened_at": str,
                "closed_at": str,
                "signal_type": str
            }
        ]
    }
    """

    def __init__(self, portfolio_path: str = PORTFOLIO_FILE):
        self._path = portfolio_path
        self._portfolio: Dict[str, Any] = self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> Dict[str, Any]:
        """Load portfolio from JSON file; initialise if absent or corrupt."""
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                # Ensure all required keys exist
                data.setdefault("cash", INITIAL_CASH)
                data.setdefault("holdings", [])
                data.setdefault("closed_trades", [])
                return data
            except (json.JSONDecodeError, OSError) as exc:
                logger.error("Failed to load portfolio JSON (%s); reinitialising.", exc)

        return {
            "cash": INITIAL_CASH,
            "holdings": [],
            "closed_trades": [],
        }

    def _save(self) -> None:
        """Persist current portfolio state to JSON."""
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as fh:
                json.dump(self._portfolio, fh, indent=2, ensure_ascii=False)
        except OSError as exc:
            logger.error("Failed to save portfolio JSON: %s", exc)

    # ------------------------------------------------------------------
    # Portfolio queries
    # ------------------------------------------------------------------

    def get_portfolio(self) -> Dict[str, Any]:
        """
        Return a summary dict of the paper portfolio.

        Returns:
            {
                cash: float,
                holdings: list,
                total_value: float,
                pnl: float,
                pnl_pct: float,
                trades_today: int,
                win_rate: float  (0-100)
            }
        """
        try:
            holdings = self._portfolio.get("holdings", [])
            closed = self._portfolio.get("closed_trades", [])
            cash = float(self._portfolio.get("cash", INITIAL_CASH))

            holdings_value = sum(
                h.get("current_price", h["entry_price"]) * h["quantity"]
                for h in holdings
            )
            total_value = cash + holdings_value
            pnl = total_value - INITIAL_CASH
            pnl_pct = round((pnl / INITIAL_CASH) * 100, 2)

            today_str = datetime.now(IST).strftime("%Y-%m-%d")
            trades_today = sum(
                1 for t in closed
                if t.get("closed_at", "").startswith(today_str)
            )

            wins = sum(1 for t in closed if t.get("pnl", 0) > 0)
            win_rate = round((wins / len(closed)) * 100, 2) if closed else 0.0

            return {
                "cash": round(cash, 2),
                "holdings": holdings,
                "total_value": round(total_value, 2),
                "pnl": round(pnl, 2),
                "pnl_pct": pnl_pct,
                "trades_today": trades_today,
                "win_rate": win_rate,
            }
        except Exception as exc:
            logger.error("get_portfolio failed: %s", exc)
            return {"cash": 0, "holdings": [], "total_value": 0, "pnl": 0,
                    "pnl_pct": 0, "trades_today": 0, "win_rate": 0}

    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Return all currently open holdings with live unrealized P&L."""
        try:
            return list(self._portfolio.get("holdings", []))
        except Exception as exc:
            logger.error("get_open_positions failed: %s", exc)
            return []

    def get_trade_history(self) -> List[Dict[str, Any]]:
        """Return list of all closed trades (newest first)."""
        try:
            trades = list(self._portfolio.get("closed_trades", []))
            trades.sort(key=lambda t: t.get("closed_at", ""), reverse=True)
            return trades
        except Exception as exc:
            logger.error("get_trade_history failed: %s", exc)
            return []

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Return aggregate performance statistics.

        Returns:
            {
                total_trades: int,
                wins: int,
                losses: int,
                win_rate: float,
                total_pnl: float,
                max_drawdown: float,
                avg_return_pct: float,
                best_trade: dict | None,
                worst_trade: dict | None
            }
        """
        try:
            closed = self._portfolio.get("closed_trades", [])
            if not closed:
                return {
                    "total_trades": 0, "wins": 0, "losses": 0,
                    "win_rate": 0.0, "total_pnl": 0.0,
                    "max_drawdown": 0.0, "avg_return_pct": 0.0,
                    "best_trade": None, "worst_trade": None,
                }

            pnls = [t.get("pnl", 0.0) for t in closed]
            pnl_pcts = [t.get("pnl_pct", 0.0) for t in closed]
            wins = sum(1 for p in pnls if p > 0)
            losses = sum(1 for p in pnls if p <= 0)
            total_pnl = round(sum(pnls), 2)
            win_rate = round((wins / len(closed)) * 100, 2)
            avg_return_pct = round(sum(pnl_pcts) / len(pnl_pcts), 2)

            # Max drawdown: largest peak-to-trough drop in cumulative P&L
            cumulative = 0.0
            peak = 0.0
            max_drawdown = 0.0
            for p in pnls:
                cumulative += p
                if cumulative > peak:
                    peak = cumulative
                drawdown = peak - cumulative
                if drawdown > max_drawdown:
                    max_drawdown = drawdown

            best = max(closed, key=lambda t: t.get("pnl", 0), default=None)
            worst = min(closed, key=lambda t: t.get("pnl", 0), default=None)

            return {
                "total_trades": len(closed),
                "wins": wins,
                "losses": losses,
                "win_rate": win_rate,
                "total_pnl": total_pnl,
                "max_drawdown": round(max_drawdown, 2),
                "avg_return_pct": avg_return_pct,
                "best_trade": best,
                "worst_trade": worst,
            }
        except Exception as exc:
            logger.error("get_performance_stats failed: %s", exc)
            return {"total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0.0,
                    "total_pnl": 0.0, "max_drawdown": 0.0, "avg_return_pct": 0.0,
                    "best_trade": None, "worst_trade": None}

    # ------------------------------------------------------------------
    # Trade execution
    # ------------------------------------------------------------------

    def open_trade(self, signal_dict: Dict[str, Any]) -> bool:
        """
        Execute a paper trade from a signal dict.

        Returns True on success, False if insufficient cash or invalid data.
        """
        try:
            symbol = signal_dict.get("symbol", "").upper()
            entry_price = float(signal_dict.get("entry_price", 0))
            quantity = int(signal_dict.get("quantity", 0))
            direction = signal_dict.get("direction", "BUY").upper()
            stop_loss = float(signal_dict.get("stop_loss", 0))
            target_price = float(signal_dict.get("target_price", 0))

            if not symbol or entry_price <= 0 or quantity <= 0:
                logger.warning("open_trade: invalid signal data %s", signal_dict)
                return False

            cost = entry_price * quantity
            cash = float(self._portfolio.get("cash", 0))

            if cost > cash:
                logger.warning(
                    "open_trade: insufficient cash (need Rs.%.2f, have Rs.%.2f)",
                    cost, cash,
                )
                return False

            position: Dict[str, Any] = {
                "symbol": symbol,
                "nse_name": signal_dict.get("nse_name", f"{symbol} Ltd"),
                "direction": direction,
                "entry_price": round(entry_price, 2),
                "current_price": round(entry_price, 2),
                "quantity": quantity,
                "stop_loss": round(stop_loss, 2),
                "target_price": round(target_price, 2),
                "signal_type": signal_dict.get("signal_type", "SWING"),
                "opened_at": _now_ist_str(),
                "unrealized_pnl": 0.0,
            }

            self._portfolio["cash"] = round(cash - cost, 2)
            self._portfolio.setdefault("holdings", []).append(position)
            self._save()
            logger.info("Opened paper trade: %s x%d @ Rs.%.2f", symbol, quantity, entry_price)
            return True

        except Exception as exc:
            logger.error("open_trade failed: %s", exc)
            return False

    def close_trade(
        self,
        symbol: str,
        exit_price: float,
        reason: str = "MANUAL",
    ) -> Dict[str, Any]:
        """
        Close an open position by symbol.

        Args:
            symbol:     NSE ticker symbol (case-insensitive).
            exit_price: Price at which the position is closed.
            reason:     "TARGET" | "STOP_LOSS" | "MANUAL"

        Returns:
            Dict with trade details and realised P&L, or empty dict on failure.
        """
        try:
            symbol = symbol.upper()
            holdings: List[Dict[str, Any]] = self._portfolio.get("holdings", [])

            idx = next(
                (i for i, h in enumerate(holdings) if h["symbol"] == symbol),
                None,
            )
            if idx is None:
                logger.warning("close_trade: symbol %s not in open positions", symbol)
                return {}

            position = holdings.pop(idx)
            entry_price = float(position["entry_price"])
            quantity = int(position["quantity"])
            direction = position.get("direction", "BUY")

            if direction == "BUY":
                pnl = (exit_price - entry_price) * quantity
            else:  # SELL / short
                pnl = (entry_price - exit_price) * quantity

            pnl = round(pnl, 2)
            pnl_pct = round((pnl / (entry_price * quantity)) * 100, 2)
            proceeds = exit_price * quantity

            self._portfolio["cash"] = round(
                float(self._portfolio.get("cash", 0)) + proceeds, 2
            )

            closed_record: Dict[str, Any] = {
                "symbol": symbol,
                "nse_name": position.get("nse_name", f"{symbol} Ltd"),
                "direction": direction,
                "entry_price": entry_price,
                "exit_price": round(exit_price, 2),
                "quantity": quantity,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "reason": reason.upper(),
                "opened_at": position.get("opened_at", ""),
                "closed_at": _now_ist_str(),
                "signal_type": position.get("signal_type", ""),
            }

            self._portfolio.setdefault("closed_trades", []).append(closed_record)
            self._save()

            logger.info(
                "Closed paper trade: %s @ Rs.%.2f | PnL: Rs.%.2f (%s)",
                symbol, exit_price, pnl, reason,
            )
            return closed_record

        except Exception as exc:
            logger.error("close_trade failed: %s", exc)
            return {}

    # ------------------------------------------------------------------
    # Position management
    # ------------------------------------------------------------------

    def update_positions(self, current_prices_dict: Dict[str, float]) -> None:
        """
        Update unrealized P&L for all open positions and auto-close any
        that have hit their target or stop-loss level.

        Args:
            current_prices_dict: Mapping of {symbol: current_price}
        """
        try:
            holdings: List[Dict[str, Any]] = self._portfolio.get("holdings", [])
            to_close: List[Dict[str, str | float]] = []

            for position in holdings:
                symbol = position["symbol"]
                price = current_prices_dict.get(symbol)
                if price is None:
                    continue

                price = float(price)
                position["current_price"] = round(price, 2)
                entry = float(position["entry_price"])
                qty = int(position["quantity"])
                direction = position.get("direction", "BUY")

                if direction == "BUY":
                    position["unrealized_pnl"] = round((price - entry) * qty, 2)
                else:
                    position["unrealized_pnl"] = round((entry - price) * qty, 2)

                # Auto-close checks
                target = float(position.get("target_price", 0))
                sl = float(position.get("stop_loss", 0))

                if direction == "BUY":
                    if target > 0 and price >= target:
                        to_close.append({"symbol": symbol, "price": price, "reason": "TARGET"})
                    elif sl > 0 and price <= sl:
                        to_close.append({"symbol": symbol, "price": price, "reason": "STOP_LOSS"})
                else:
                    if target > 0 and price <= target:
                        to_close.append({"symbol": symbol, "price": price, "reason": "TARGET"})
                    elif sl > 0 and price >= sl:
                        to_close.append({"symbol": symbol, "price": price, "reason": "STOP_LOSS"})

            # Execute auto-closes (modifies holdings list)
            for item in to_close:
                self.close_trade(item["symbol"], float(item["price"]), str(item["reason"]))

            self._save()

        except Exception as exc:
            logger.error("update_positions failed: %s", exc)
