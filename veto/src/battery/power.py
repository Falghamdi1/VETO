"""Statistical power check.

Fires when a claimed group difference rests on a sample too small to
detect the observed effect reliably: achieved power < POWER_THRESHOLD,
or the bootstrap CI of the difference crosses zero.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.stats.power import TTestIndPower

POWER_THRESHOLD = 0.8
N_BOOT = 2000
SEED = 7


def check_power(
    df: pd.DataFrame,
    outcome: str,
    treatment: str,
    treatment_focus: str,
) -> dict:
    rng = np.random.default_rng(SEED)
    a = df.loc[df[treatment].astype(str) == str(treatment_focus), outcome].dropna().to_numpy(float)
    b = df.loc[df[treatment].astype(str) != str(treatment_focus), outcome].dropna().to_numpy(float)
    n1, n2 = len(a), len(b)
    if n1 == 0 or n2 == 0:
        # focus didn't match any rows — not a power problem, skip cleanly
        return {"check": "power", "fired": False,
                "summary": f"focus group not found in data (n1={n1}, n2={n2}); power check skipped",
                "details": []}
    if n1 < 2 or n2 < 2:
        return {"check": "power", "fired": True,
                "summary": f"group sizes too small to analyze (n1={n1}, n2={n2})",
                "details": [{"required_control": "collect more data before acting"}]}

    diff = float(a.mean() - b.mean())
    pooled_sd = float(np.sqrt(((n1 - 1) * a.var(ddof=1) + (n2 - 1) * b.var(ddof=1)) / (n1 + n2 - 2)))
    cohens_d = diff / pooled_sd if pooled_sd > 0 else 0.0

    achieved_power = float(
        TTestIndPower().power(effect_size=abs(cohens_d) + 1e-9, nobs1=n1,
                              ratio=n2 / n1, alpha=0.05)
    )

    boot = np.empty(N_BOOT)
    for i in range(N_BOOT):
        boot[i] = rng.choice(a, n1).mean() - rng.choice(b, n2).mean()
    ci_lo, ci_hi = (float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5)))
    ci_crosses_zero = ci_lo < 0 < ci_hi

    n_required = None
    if abs(cohens_d) > 1e-6:
        n_required = int(np.ceil(TTestIndPower().solve_power(
            effect_size=abs(cohens_d), power=POWER_THRESHOLD, alpha=0.05)))

    fired = achieved_power < POWER_THRESHOLD or ci_crosses_zero
    details = []
    if fired:
        details.append({
            "n_focus": n1, "n_rest": n2,
            "observed_diff": round(diff, 4),
            "cohens_d": round(cohens_d, 3),
            "achieved_power": round(achieved_power, 3),
            "bootstrap_ci_95": [round(ci_lo, 4), round(ci_hi, 4)],
            "ci_crosses_zero": bool(ci_crosses_zero),
            "n_required_per_group_for_80pct_power": n_required,
            "required_control": (
                f"suspend action; collect ≥{n_required} obs/group before re-testing"
                if n_required else "suspend action; effect indistinguishable from zero"
            ),
        })

    return {
        "check": "power",
        "fired": fired,
        "summary": (f"d={cohens_d:.3f}, achieved power={achieved_power:.2f}, "
                    f"95% bootstrap CI=[{ci_lo:.4f}, {ci_hi:.4f}]"),
        "details": details,
    }
