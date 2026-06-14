"""Confounding / Simpson's reversal check.

Fires when controlling for a candidate confounder flips the sign of the
treatment effect, or shifts the coefficient by more than RELATIVE_SHIFT.
Authority comes from statsmodels OLS, not from any model's opinion.
"""
from __future__ import annotations

import pandas as pd
import statsmodels.formula.api as smf

RELATIVE_SHIFT = 0.5  # >50% coefficient change counts as material confounding


def check_confounding(
    df: pd.DataFrame,
    outcome: str,
    treatment: str,
    treatment_focus: str,
    candidate_confounders: list[str],
) -> dict:
    """Compare naive vs. controlled effect of `treatment_focus` on `outcome`.

    treatment_focus: the level of `treatment` the Analyst singled out
    (e.g. region "B"). Encoded as a binary indicator vs. all other levels.
    """
    work = df.copy()
    work["_focus"] = (work[treatment].astype(str) == str(treatment_focus)).astype(int)

    naive = smf.ols(f"{outcome} ~ _focus", data=work).fit()
    b_naive = float(naive.params["_focus"])
    p_naive = float(naive.pvalues["_focus"])

    fired_details = []
    for conf in candidate_confounders:
        if conf not in work.columns or conf in (outcome, treatment):
            continue
        term = f"C({conf})" if work[conf].dtype == object else conf
        controlled = smf.ols(f"{outcome} ~ _focus + {term}", data=work).fit()
        b_ctrl = float(controlled.params["_focus"])
        p_ctrl = float(controlled.pvalues["_focus"])

        sign_flip = (b_naive * b_ctrl) < 0
        rel_shift = abs(b_ctrl - b_naive) / (abs(b_naive) + 1e-9)
        if sign_flip or rel_shift > RELATIVE_SHIFT:
            fired_details.append(
                {
                    "confounder": conf,
                    "naive_coef": round(b_naive, 4),
                    "naive_p": round(p_naive, 5),
                    "controlled_coef": round(b_ctrl, 4),
                    "controlled_p": round(p_ctrl, 5),
                    "sign_reversal": bool(sign_flip),
                    "relative_shift": round(rel_shift, 3),
                    "required_control": f"include {conf} as a covariate / stratify by {conf}",
                }
            )

    return {
        "check": "confounding",
        "fired": bool(fired_details),
        "summary": (
            f"naive effect of {treatment}={treatment_focus} on {outcome}: "
            f"{b_naive:+.4f} (p={p_naive:.4f})"
        ),
        "details": fired_details,
    }
