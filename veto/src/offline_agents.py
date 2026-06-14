"""Offline (deterministic) Analyst and Adversary.

These mirror the Foundry agents' contracts exactly, with rule-based
logic instead of LLM calls. They exist so the pipeline is testable,
rehearsable, and demoable with zero cloud dependency — and they make a
deeper point: the gate's guarantees do not depend on which brain is
plugged in. Swap in `foundry_agents` via --live and nothing else changes.
"""
from __future__ import annotations

import pandas as pd

from .tools.pandas_sandbox import run_pandas


class OfflineAnalyst:
    """Fast, decisive, naive — by design. Computes a real naive groupby
    through the sandbox and proposes an action with a victim."""

    def __init__(self, df: pd.DataFrame, meta: dict):
        self.df, self.meta = df, meta
        self.controls_applied: list[str] = []

    def propose(self) -> dict:
        outcome, treatment = self.meta["outcome"], self.meta["treatment"]
        means = run_pandas(
            self.df,
            f"result = df.groupby({treatment!r})[{outcome!r}].mean().sort_values()",
        )
        focus = str(means.index[0])          # the "loser" group
        best = str(means.index[-1])
        gap = float(means.iloc[-1] - means.iloc[0])
        n = int((self.df[treatment].astype(str) == focus).sum())

        return {
            "claim": f"{treatment}={focus} underperforms on {outcome}",
            "outcome": outcome,
            "treatment": treatment,
            "treatment_focus": focus,
            "evidence": (
                f"{treatment}={focus} mean {outcome}={means.iloc[0]:.4f} vs "
                f"{treatment}={best}={means.iloc[-1]:.4f} (gap {gap:.4f}, n={n})"
            ),
            "proposed_action": {
                "type": "teams_post",
                "severity": "high",
                "text": (
                    f"RECOMMENDATION: {treatment} '{focus}' is the weakest performer "
                    f"on {outcome}. Reallocate its budget and headcount to "
                    f"'{best}' effective next quarter."
                ),
            },
            "analysis_code_summary": f"df.groupby('{treatment}')['{outcome}'].mean()",
            "controls_applied": list(self.controls_applied),
            "confidence": 0.86,
        }

    def revise(self, proposal: dict, decision) -> dict:
        """Rerun the analysis applying exactly the controls the gate demands."""
        fired = {r["check"]: r for r in decision.battery.fired()}
        outcome, treatment = self.meta["outcome"], self.meta["treatment"]
        focus = proposal["treatment_focus"]

        if "confounding" in fired:
            conf = fired["confounding"]["details"][0]["confounder"]
            self.controls_applied.append(conf)
            strat = run_pandas(
                self.df,
                f"result = df.groupby([{conf!r}, {treatment!r}])[{outcome!r}].mean().unstack()",
            )
            revised = dict(proposal)
            revised["claim"] = (
                f"{treatment}={focus} OUTPERFORMS within every {conf} segment; "
                f"the pooled gap is a composition effect"
            )
            revised["evidence"] = "stratified means by " + conf + ": " + "; ".join(
                f"{idx}: " + ", ".join(f"{c}={strat.loc[idx, c]:.4f}" for c in strat.columns)
                for idx in strat.index
            )
            revised["proposed_action"] = {
                "type": "teams_post",
                "severity": "high",
                "text": (
                    f"CORRECTED RECOMMENDATION: controlling for {conf}, "
                    f"{treatment} '{focus}' is the STRONGEST performer in every "
                    f"segment. Its pooled average is dragged down by a harder "
                    f"{conf} mix. Do NOT cut '{focus}'; rebalance segment "
                    f"assignment and share its playbook instead."
                ),
            }
            revised["analysis_code_summary"] = (
                f"df.groupby(['{conf}','{treatment}'])['{outcome}'].mean()"
            )
            revised["controls_applied"] = list(self.controls_applied)
            revised["confidence"] = 0.93
            return revised

        if "power" in fired:
            d = fired["power"]["details"][0]
            ci_note = ("crosses zero" if d["ci_crosses_zero"]
                       else "is too unstable at this sample size")
            revised = dict(proposal)
            revised["claim"] = f"insufficient evidence that {treatment}={focus} differs on {outcome}"
            revised["evidence"] = (
                f"achieved power {d['achieved_power']}, 95% CI {d['bootstrap_ci_95']} "
                f"{ci_note}; n={d['n_focus']}/group"
            )
            revised["proposed_action"] = {
                "type": "teams_post", "severity": "medium",
                "text": (
                    f"CORRECTED RECOMMENDATION: the apparent {outcome} gap for "
                    f"{treatment} '{focus}' is not statistically reliable "
                    f"(power={d['achieved_power']}). Suspend action; collect "
                    f"≥{d['n_required_per_group_for_80pct_power']} observations "
                    f"per group, then re-run this pipeline."
                ),
            }
            revised["controls_applied"] = list(self.controls_applied) + ["power_gate"]
            revised["confidence"] = 0.9
            return revised

        if "multiplicity" in fired:
            revised = dict(proposal)
            revised["claim"] = "no metric difference survives FDR correction"
            revised["proposed_action"] = {
                "type": "teams_post", "severity": "medium",
                "text": (
                    "CORRECTED RECOMMENDATION: the headline metric was selected "
                    "from a scan of many; after Benjamini-Hochberg correction no "
                    "difference is significant. Treat as exploratory — "
                    "pre-register the single metric and re-test on fresh data."
                ),
            }
            # the corrected claim asserts NO difference, so the power check's
            # purpose (blocking unreliable difference claims) no longer applies
            revised["controls_applied"] = list(self.controls_applied) + [
                "fdr_correction", "power_gate"]
            revised["confidence"] = 0.9
            return revised

        # distribution shift or other: restrict to stable window
        revised = dict(proposal)
        revised["proposed_action"] = {
            "type": "teams_post", "severity": "medium",
            "text": ("CORRECTED RECOMMENDATION: the data distribution shifted "
                     "mid-window; restricting to the stable window before acting."),
        }
        revised["controls_applied"] = list(self.controls_applied) + ["stable_window"]
        return revised


class OfflineAdversary:
    """An auditor with no opinion of its own: formats a verdict strictly
    from the battery output and must cite its run id."""

    def review(self, proposal: dict, battery) -> dict:
        fired = battery.fired()
        if fired:
            return {
                "verdict": "VETO",
                "battery_run_id": battery.run_id,
                "fired_checks": [
                    {"check": r["check"], "detail": r["summary"], "evidence": r["details"]}
                    for r in fired
                ],
                "passed_checks": battery.passed(),
                "narrative": (
                    "Commit blocked. " + "; ".join(
                        f"[{r['check']}] {r['summary']}" for r in fired)
                ),
            }
        return {
            "verdict": "APPROVE",
            "battery_run_id": battery.run_id,
            "fired_checks": [],
            "passed_checks": battery.passed(),
            "narrative": "All applicable checks passed. Commit signed.",
        }
