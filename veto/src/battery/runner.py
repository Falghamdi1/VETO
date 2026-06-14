"""BatteryRunner — the deterministic core of VETO.

Runs every applicable check against a claim and returns a single
ground-truth object. The commit gate trusts THIS object, never an
agent's narration of it. Each run gets an id the Adversary must cite.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import pandas as pd

from .confounding import check_confounding
from .power import check_power
from .multiplicity import check_multiplicity
from .shift import check_shift


@dataclass
class BatteryResult:
    run_id: str
    results: list[dict] = field(default_factory=list)

    def any_fired(self) -> bool:
        return any(r["fired"] for r in self.results)

    def fired(self) -> list[dict]:
        return [r for r in self.results if r["fired"]]

    def passed(self) -> list[str]:
        return [r["check"] for r in self.results if not r["fired"]]

    def required_controls(self) -> list[str]:
        out = []
        for r in self.fired():
            for d in r["details"]:
                rc = d.get("required_control")
                if rc:
                    out.append(rc)
                for sub in d.get("nominal_hits", []):
                    pass
        return out

    def to_dict(self) -> dict:
        return {"run_id": self.run_id, "results": self.results}


class BatteryRunner:
    def __init__(self, df: pd.DataFrame, meta: dict):
        self.df = df
        self.meta = meta  # outcome, treatment, candidate_confounders, metric_columns

    def run(self, claim: dict, controls_applied: list[str] | None = None) -> BatteryResult:
        """Run the battery against an Analyst claim.

        controls_applied: confounders the Analyst already controlled for in a
        revised analysis — those no longer count as unaddressed confounding.
        """
        controls_applied = controls_applied or []
        outcome = claim.get("outcome", self.meta["outcome"])
        treatment = claim.get("treatment", self.meta["treatment"])
        focus = claim["treatment_focus"]

        # a control acknowledges and addresses its trap:
        #  - a named confounder -> excluded from the confounding scan
        #  - "power_gate"       -> claim no longer asserts a difference
        #  - "fdr_correction"   -> claim already FDR-corrected
        #  - "stable_window"    -> claim restricted to stable window
        confs = [c for c in self.meta.get("candidate_confounders", [])
                 if c not in controls_applied]

        res = BatteryResult(run_id=f"run_{uuid.uuid4().hex[:8]}")
        if confs:
            res.results.append(check_confounding(self.df, outcome, treatment, focus, confs))
        if "power_gate" not in controls_applied:
            res.results.append(check_power(self.df, outcome, treatment, focus))
        if "fdr_correction" not in controls_applied:
            res.results.append(check_multiplicity(
                self.df, treatment, focus, self.meta.get("metric_columns")))
        if "stable_window" not in controls_applied:
            res.results.append(check_shift(self.df, outcome))
        return res
