"""Battery tests against datasets with KNOWN ground truth.
Run: python -m pytest tests/ -q   (or python tests/test_battery.py)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from src.battery.confounding import check_confounding
from src.battery.power import check_power
from src.battery.multiplicity import check_multiplicity
from src.battery.shift import check_shift

RNG = np.random.default_rng(0)


def test_confounding_fires_on_simpsons():
    df = pd.read_csv(Path(__file__).parent.parent / "data/headline_sales.csv")
    r = check_confounding(df, "converted", "region", "B", ["deal_size"])
    assert r["fired"], "Simpson's reversal must fire the confounding check"
    assert r["details"][0]["sign_reversal"] is True


def test_confounding_silent_when_clean():
    n = 4000
    df = pd.DataFrame({
        "g": RNG.choice(["A", "B"], n),
        "z": RNG.choice(["x", "y"], n),
    })
    df["y"] = (df["g"] == "B") * 0.05 + RNG.normal(0, 0.1, n)
    r = check_confounding(df, "y", "g", "B", ["z"])
    assert not r["fired"], "independent covariate must not fire"


def test_power_fires_on_tiny_sample():
    df = pd.read_csv(Path(__file__).parent.parent / "data/trap_power.csv")
    r = check_power(df, "activation_score", "variant", "old")
    assert r["fired"], "n=22/group 'trend' must fire the power check"


def test_power_silent_on_large_clear_effect():
    n = 2000
    df = pd.DataFrame({"g": ["A"] * n + ["B"] * n,
                       "y": np.concatenate([RNG.normal(0, 1, n), RNG.normal(0.5, 1, n)])})
    r = check_power(df, "y", "g", "A")
    assert not r["fired"]


def test_multiplicity_kills_phacked_metric():
    df = pd.read_csv(Path(__file__).parent.parent / "data/trap_multiplicity.csv")
    meta_cols = [f"metric_{i:02d}" for i in range(1, 21)]
    r = check_multiplicity(df, "variant", "A", meta_cols)
    assert r["fired"], "nominal hit from a 20-metric scan must die under BH"


def test_shift_not_applicable_without_period():
    df = pd.DataFrame({"g": ["A", "B"] * 50, "y": RNG.normal(0, 1, 100)})
    r = check_shift(df, "y")
    assert not r["fired"]


def test_shift_fires_on_real_shift():
    n = 600
    df = pd.DataFrame({
        "period": [1] * n + [2] * n,
        "y": np.concatenate([RNG.normal(0, 1, n), RNG.normal(1.2, 1, n)]),
    })
    r = check_shift(df, "y")
    assert r["fired"]


if __name__ == "__main__":
    fns = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS  {fn.__name__}")
    print(f"\n{len(fns)}/{len(fns)} battery tests passed")
