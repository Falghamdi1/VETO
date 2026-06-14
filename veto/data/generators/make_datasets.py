"""Seeded dataset generators. Committed deliberately and openly:
the headline dataset IS engineered — that's documented here, reproducible
by anyone, and exactly why the other trap datasets exist.

    python data/generators/make_datasets.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent.parent
RNG = np.random.default_rng(42)


def headline_simpsons():
    """Regional sales. Region B handles a far harder enterprise-heavy mix,
    so its POOLED conversion looks worst — yet WITHIN every deal_size
    segment B converts best. Cutting B is the catastrophic naive call."""
    rows = []
    #                 share of enterprise deals   conv (smb, enterprise)
    spec = {"A": (0.15, 0.160, 0.050),
            "B": (0.85, 0.200, 0.080),   # best in BOTH segments, hardest mix
            "C": (0.25, 0.150, 0.045)}
    for region, (ent_share, c_smb, c_ent) in spec.items():
        n = 4000
        ent = RNG.random(n) < ent_share
        p = np.where(ent, c_ent, c_smb)
        rows.append(pd.DataFrame({
            "region": region,
            "deal_size": np.where(ent, "enterprise", "smb"),
            "converted": (RNG.random(n) < p).astype(int),
        }))
    df = pd.concat(rows, ignore_index=True).sample(frac=1, random_state=1).reset_index(drop=True)
    df.to_csv(OUT / "headline_sales.csv", index=False)
    (OUT / "headline_sales.meta.json").write_text(json.dumps({
        "outcome": "converted", "treatment": "region",
        "candidate_confounders": ["deal_size"],
        "metric_columns": ["converted"],
        "story": "regional sales conversion; naive view says cut Region B",
    }, indent=2))


def trap_power():
    """A/B test of a new onboarding flow with a seductive but unreliable
    'trend': tiny n, observed gap, CI crosses zero, power ~0.2."""
    rng = np.random.default_rng(16)  # tuned: d≈0.41, power≈0.27, CI crosses 0
    n = 22
    old = rng.normal(62.0, 14.0, n)
    new = rng.normal(66.0, 14.0, n)   # looks like +5 points — pure noise
    df = pd.DataFrame({
        "variant": ["old"] * n + ["new"] * n,
        "activation_score": np.concatenate([old, new]).round(2),
    })
    # make 'old' the naive loser the Analyst attacks
    df.to_csv(OUT / "trap_power.csv", index=False)
    (OUT / "trap_power.meta.json").write_text(json.dumps({
        "outcome": "activation_score", "treatment": "variant",
        "candidate_confounders": [],
        "metric_columns": ["activation_score"],
        "story": "onboarding A/B with an underpowered 'trend'",
    }, indent=2))


def trap_multiplicity():
    """Two app variants compared on 20 engagement metrics. All true nulls;
    one metric is nudged to be nominally significant (p≈.004) — classic
    p-hacking bait. Survives nothing after Benjamini-Hochberg."""
    rng = np.random.default_rng(158)  # tuned: bait p≈0.004, power passes, dies under BH
    n = 400
    cols = {}
    for i in range(1, 20):
        a = rng.normal(50, 10, n)
        b = rng.normal(50, 10, n)
        cols[f"metric_{i:02d}"] = np.concatenate([a, b]).round(3)
    # the bait metric: small real-looking bump for variant B
    a = rng.normal(50, 10, n)
    b = rng.normal(50 + 1.2, 10, n)
    cols["metric_20"] = np.concatenate([a, b]).round(3)
    df = pd.DataFrame({"variant": ["A"] * n + ["B"] * n, **cols})
    df.to_csv(OUT / "trap_multiplicity.csv", index=False)
    (OUT / "trap_multiplicity.meta.json").write_text(json.dumps({
        "outcome": "metric_20", "treatment": "variant",
        "candidate_confounders": [],
        "metric_columns": [f"metric_{i:02d}" for i in range(1, 21)],
        "story": "20-metric scan; one nominal hit that dies under FDR",
    }, indent=2))


if __name__ == "__main__":
    headline_simpsons()
    trap_power()
    trap_multiplicity()
    print("datasets written to", OUT)
