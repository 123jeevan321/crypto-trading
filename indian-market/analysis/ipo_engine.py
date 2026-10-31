"""
IPO Intelligence & Allotment Optimization Engine (Jeevan Trader)
Calculates exact mathematical allotment probabilities and ROI for:
- 3 Family Demat Accounts (User Jeevan + Sister + Brother)
- Retail 1-Lot Strategy vs sHNI (Small HNI: 2L-10L) Strategy
- Mainboard NSE IPOs only (No SME)
"""

import logging

logger = logging.getLogger(__name__)

class IPOEngine:
    """
    Solves the exact multi-account allocation problem:
    Given 3 family PAN accounts (Jeevan, Sister, Brother),
    evaluates Retail vs sHNI vs bHNI subscription numbers and GMP,
    and returns the highest expected value (EV) action.
    """

    def __init__(self, num_accounts=3):
        self.num_accounts = num_accounts  # Jeevan + Sister + Brother

    def analyze_allotment_probability(self, ipo_data):
        """
        Calculates mathematical allotment probability for:
        1. Retail 1-lot across 3 PAN accounts
        2. Single account Retail max application
        3. sHNI (Small HNI: ₹2L to ₹10L)
        """
        sub = ipo_data.get("subscription", {})
        retail_sub = sub.get("retail", 0.0)
        shni_sub = sub.get("nii_shni", 0.0)
        gmp_pct = ipo_data.get("gmp_percent", 0.0)
        gmp_rs = ipo_data.get("gmp_rs", 0)
        lot_size = ipo_data.get("lot_size", 1)
        min_inv = ipo_data.get("min_investment", 15000)

        # 1. Retail Allotment Probability Per Account
        if retail_sub <= 1.0:
            p_single_retail = 1.0  # 100% full allotment if undersubscribed!
        else:
            # SEBI Rule: In oversubscribed retail, 1 lot per unique PAN via lottery
            p_single_retail = 1.0 / retail_sub

        # 3 Family Accounts Retail Cumulative Probability:
        # P(at least 1 allotment across N accounts) = 1 - (1 - P)^N
        if p_single_retail >= 1.0:
            p_3_accounts_retail = 1.0
            expected_lots_retail = 3.0  # All 3 accounts get 1 lot!
        else:
            p_3_accounts_retail = 1.0 - ((1.0 - p_single_retail) ** self.num_accounts)
            expected_lots_retail = self.num_accounts * p_single_retail

        # 2. sHNI (Small HNI) Allotment Probability
        # sHNI requires min investment of ₹2,00,000 (usually 14 lots)
        # SEBI allotment rule for sHNI: Also lottery for minimum lot (1 lot) if oversubscribed!
        if shni_sub <= 1.0 and shni_sub > 0:
            p_shni = 1.0
        elif shni_sub > 1.0:
            p_shni = 1.0 / shni_sub
        else:
            p_shni = 0.5  # placeholder before subscription begins

        # Profit Calculations
        profit_per_lot = gmp_rs * lot_size
        investment_3_retail = min_inv * self.num_accounts  # e.g. ~₹45,000

        # Expected Value
        expected_profit_3_retail = expected_lots_retail * profit_per_lot
        expected_profit_shni = p_shni * profit_per_lot

        # Decision Logic: Which strategy is better?
        recommendation = ""
        action_plan = []

        if retail_sub <= 1.0 and retail_sub > 0:
            recommendation = "ALL-IN RETAIL (3 FAMILY ACCOUNTS)"
            action_plan = [
                f"Retail is UNDER-SUBSCRIBED ({retail_sub}x) - 100% GUARANTEED ALLOTMENT!",
                f"Apply exactly 1 lot in Jeevan's account (₹{min_inv:,.0f})",
                f"Apply exactly 1 lot in Sister's account (₹{min_inv:,.0f})",
                f"Apply exactly 1 lot in Brother's account (₹{min_inv:,.0f})",
                f"Total Capital Deployed: ₹{investment_3_retail:,.0f}",
                f"Expected Allotment: 3 LOTS GUARANTEED (Profit: +₹{profit_per_lot * 3:,.0f} at {gmp_pct:.1f}% GMP)"
            ]
        elif p_3_accounts_retail > (p_shni * 1.5):
            recommendation = "APPLY 1 LOT EACH IN 3 ACCOUNTS (RETAIL LOTTERY)"
            action_plan = [
                f"Retail subscription is {retail_sub:.2f}x vs sHNI at {shni_sub:.2f}x",
                f"Applying across 3 PANs boosts allotment probability to {p_3_accounts_retail * 100:.1f}%",
                f"Do NOT apply multiple lots in 1 account (SEBI rules allocate 1 lot per PAN)",
                f"Capital required: ₹{investment_3_retail:,.0f} (₹{min_inv:,.0f} x 3 accounts)",
                f"Expected Profit per Allotted Lot: +₹{profit_per_lot:,.0f} (+{gmp_pct:.1f}%)"
            ]
        else:
            recommendation = "sHNI CATEGORY (MIN ₹2,00,000)"
            action_plan = [
                f"sHNI subscription ({shni_sub:.2f}x) offers better odds than Retail ({retail_sub:.2f}x)",
                "Apply in sHNI with 14 lots (₹2,00,000+)",
                f"Estimated probability of getting minimum lot: {p_shni * 100:.1f}%"
            ]

        # Safety Check on GMP
        safety_status = "SAFE FOR LISTING GAIN"
        if gmp_pct < 2.0:
            safety_status = "DANGEROUS: FLAT/NEGATIVE LISTING RISK"
        elif gmp_pct < 5.0:
            safety_status = "MODERATE: SMALL 2-5% LISTING POP"
        else:
            safety_status = f"HIGH REWARD: +{gmp_pct:.1f}% ESTIMATED GAIN"

        return {
            "symbol": ipo_data["symbol"],
            "name": ipo_data["name"],
            "status": ipo_data["status"],
            "gmp_rs": gmp_rs,
            "gmp_percent": gmp_pct,
            "gmp_trend": ipo_data.get("gmp_trend", "STABLE"),
            "safety_status": safety_status,
            "min_investment_1lot": min_inv,
            "min_investment_3accounts": investment_3_retail,
            "retail_sub": retail_sub,
            "shni_sub": shni_sub,
            "prob_1_retail": round(p_single_retail * 100, 1),
            "prob_3_accounts": round(p_3_accounts_retail * 100, 1),
            "prob_shni": round(p_shni * 100, 1),
            "profit_per_lot": round(profit_per_lot, 0),
            "expected_profit_3_retail": round(expected_profit_3_retail, 0),
            "recommendation": recommendation,
            "action_plan": action_plan
        }

    def evaluate_all_ipos(self, ipo_list):
        """
        Runs full analysis across all Mainboard IPOs and sorts by best opportunity.
        """
        results = []
        for ipo in ipo_list:
            res = self.analyze_allotment_probability(ipo)
            results.append(res)

        # Sort: Highest expected profit and best allotment probability first
        results.sort(key=lambda x: (x["prob_3_accounts"] * x["gmp_percent"]), reverse=True)
        return results
