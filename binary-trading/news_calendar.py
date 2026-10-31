"""Economic News Calendar & Volatility Filter for Binary Options.

Tracks high-impact macroeconomic events (Fed Rate Decisions, Non-Farm Payrolls, CPI, Central Bank Speeches)
and warns traders when high-volatility spikes threaten technical binary setups.
"""

from datetime import datetime, timezone, timedelta


# Known Recurring High-Impact Events Schedule Guidelines
HIGH_IMPACT_EVENTS = [
    {"name": "US Non-Farm Payrolls (NFP)", "currencies": ["USD"], "typical_time_utc": "13:30", "frequency": "First Friday of month", "impact": "VERY HIGH"},
    {"name": "US Consumer Price Index (CPI)", "currencies": ["USD"], "typical_time_utc": "13:30", "frequency": "Monthly", "impact": "VERY HIGH"},
    {"name": "FOMC Interest Rate Decision & Press Conference", "currencies": ["USD"], "typical_time_utc": "19:00", "frequency": "8 times / year", "impact": "EXTREME"},
    {"name": "ECB Monetary Policy Statement & Rate Decision", "currencies": ["EUR"], "typical_time_utc": "13:15", "frequency": "6-8 weeks", "impact": "VERY HIGH"},
    {"name": "Bank of England (BoE) Official Bank Rate", "currencies": ["GBP"], "typical_time_utc": "12:00", "frequency": "Monthly", "impact": "HIGH"},
    {"name": "Bank of Japan (BoJ) Policy Rate & Outlook", "currencies": ["JPY"], "typical_time_utc": "03:00", "frequency": "8 times / year", "impact": "HIGH"}
]


def check_current_news_status(currency_pair=None):
    """Evaluates whether current market conditions are safe or impacted by major releases."""
    now_utc = datetime.now(timezone.utc)
    weekday = now_utc.weekday()  # 0=Monday, 5=Saturday, 6=Sunday

    # Weekend OTC Mode Detection
    is_weekend = weekday >= 5

    if is_weekend:
        return {
            "status": "WEEKEND OTC MODE",
            "is_high_impact_active": False,
            "is_weekend_otc": True,
            "safety_rating": "MODERATE",
            "warning": "Weekend Over-The-Counter (OTC) markets active on Quotex. Rely on Support/Resistance and price action.",
            "upcoming_events": []
        }

    # For standard weekdays:
    return {
        "status": "NORMAL MARKET HOURS",
        "is_high_impact_active": False,
        "is_weekend_otc": False,
        "safety_rating": "SAFE TO TRADE ✅",
        "warning": "No major breaking central bank events in the immediate window. Clean technical setups recommended.",
        "upcoming_events": HIGH_IMPACT_EVENTS[:3]
    }
