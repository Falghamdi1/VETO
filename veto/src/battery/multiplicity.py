"""Multiple comparisons check.

When the Analyst's claim emerges from scanning many metrics, nominal
p < 0.05 hits are expected by chance alone. Fires when nominally
significant metrics do not survive Benjamini-Hochberg FDR correction.
"""
from __future__ import annotations

import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

ALPHA = 0.05


def check_multiplicity(
    df: pd.DataFrame,
    treatment: str,
    treatment_focus: str,
    metric_columns: list[str] | None = None,
) -> dict:
    if metric_columns is None:
        metric_columns = [
            c for c in df.select_dtypes("number").columns if c != treatment
        ]
    if len(metric_columns) < 2:
        return {"check": "multiplicity", "fired": False,
                "summary": "single comparison; correction not applicable", "details": []}

    mask = df[treatment].astype(str) == str(treatment_focus)
    rows = []
    pvals = []
    for m in metric_columns:
        a = df.loc[mask, m].dropna()
        b = df.loc[~mask, m].dropna()
        if len(a) < 2 or len(b) < 2:
            continue
        t, p = stats.ttest_ind(a, b, equal_var=False)
        rows.append({"metric": m, "t": round(float(t), 3), "p_nominal": round(float(p), 5)})
        pvals.append(float(p))

    reject, p_adj, _, _ = multipletests(pvals, alpha=ALPHA, method="fdr_bh")
    for r, pa, rej in zip(rows, p_adj, reject):
        r["p_bh_adjusted"] = round(float(pa), 5)
        r["significant_after_correction"] = bool(rej)

    nominal_hits = [r for r in rows if r["p_nominal"] < ALPHA]
    surviving = [r for r in rows if r["significant_after_correction"]]
    fired = bool(nominal_hits) and not surviving

    return {
        "check": "multiplicity",
        "fired": fired,
        "summary": (f"{len(rows)} metrics tested; {len(nominal_hits)} nominally significant; "
                    f"{len(surviving)} survive Benjamini-Hochberg at α={ALPHA}"),
        "details": (
            [{"nominal_hits": nominal_hits,
              "required_control": "treat as exploratory; pre-register and re-test the single metric on fresh data"}]
            if fired else []
        ),
    }
