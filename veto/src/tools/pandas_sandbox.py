"""A small restricted sandbox so the Analyst's analysis is computed, not
narrated. Exposes the dataframe as `df`; expects the snippet to assign
its answer to `result`. No imports, no IO, no dunder access."""
from __future__ import annotations

import numpy as np
import pandas as pd

_FORBIDDEN = ("__", "import", "open(", "exec", "eval", "os.", "sys.")


def run_pandas(df: pd.DataFrame, code: str):
    """Run a restricted pandas snippet against df and return `result`."""
    low = code.lower()
    for bad in _FORBIDDEN:
        if bad in low:
            raise ValueError(f"forbidden token in sandbox code: {bad!r}")
    scope = {"df": df, "pd": pd, "np": np, "result": None}
    exec(compile(code, "<sandbox>", "exec"), {"__builtins__": {}}, scope)  # noqa: S102
    return scope["result"]
