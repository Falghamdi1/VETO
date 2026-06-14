"""Distribution shift check.

If the data carries a period/time column, compares early vs. late
windows on the outcome (KS test + Population Stability Index). A
conclusion drawn from data whose distribution moved underneath it does
not generalize. Fires on KS p < 0.01 with PSI > 0.2.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

PSI_THRESHOLD = 0.2
KS_ALPHA = 0.01
PERIOD_CANDIDATES = ("period", "week", "month", "date", "day")


def _psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    edges = np.unique(np.percentile(expected, np.linspace(0, 100, bins + 1)))
    if len(edges) < 3:
        return 0.0
    e_pct = np.clip(np.histogram(expected, edges)[0] / len(expected), 1e-4, None)
    a_pct = np.clip(np.histogram(actual, edges)[0] / len(actual), 1e-4, None)
    return float(np.sum((a_pct - e_pct) * np.log(a_pct / e_pct)))


def check_shift(df: pd.DataFrame, outcome: str) -> dict:
    period_col = next((c for c in df.columns if c.lower() in PERIOD_CANDIDATES), None)
    if period_col is None:
        return {"check": "distribution_shift", "fired": False,
                "summary": "no period column; shift check not applicable", "details": []}

    ordered = df.sort_values(period_col)
    half = len(ordered) // 2
    early = ordered[outcome].iloc[:half].dropna().to_numpy(float)
    late = ordered[outcome].iloc[half:].dropna().to_numpy(float)
    if len(early) < 10 or len(late) < 10:
        return {"check": "distribution_shift", "fired": False,
                "summary": "insufficient data per window", "details": []}

    ks_stat, ks_p = ks_2samp(early, late)
    psi = _psi(early, late)
    fired = (ks_p < KS_ALPHA) and (psi > PSI_THRESHOLD)

    return {
        "check": "distribution_shift",
        "fired": fired,
        "summary": f"KS={ks_stat:.3f} (p={ks_p:.4f}), PSI={psi:.3f} across {period_col} windows",
        "details": (
            [{"ks_stat": round(float(ks_stat), 3), "ks_p": round(float(ks_p), 5),
              "psi": round(psi, 3),
              "required_control": "restrict analysis to the stable window or model the shift explicitly"}]
            if fired else []
        ),
    }
