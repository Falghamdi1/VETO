"""The reversal chart: naive pooled comparison vs. the controlled,
stratified truth. This single image is the demo's gut-punch."""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

NAIVE_COLOR = "#c0392b"
TRUTH_COLOR = "#1a7f37"
GREY = "#8a8f98"


def reversal_chart(df: pd.DataFrame, outcome: str, treatment: str,
                   focus: str, confounder: str, path: str) -> str:
    pooled = df.groupby(treatment)[outcome].mean()
    strat = df.groupby([confounder, treatment])[outcome].mean().unstack()

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    fig.suptitle("The same data. One confound apart.", fontsize=14, fontweight="bold")

    ax = axes[0]
    colors = [NAIVE_COLOR if str(i) == str(focus) else GREY for i in pooled.index]
    ax.bar([str(i) for i in pooled.index], pooled.values, color=colors)
    ax.set_title(f"Naive view: {focus} looks worst → 'cut it'", color=NAIVE_COLOR)
    ax.set_ylabel(f"mean {outcome}")
    ax.set_xlabel(treatment)

    ax = axes[1]
    idx = [str(i) for i in strat.index]
    width = 0.8 / len(strat.columns)
    for k, col in enumerate(strat.columns):
        offs = [i + k * width for i in range(len(idx))]
        color = TRUTH_COLOR if str(col) == str(focus) else GREY
        ax.bar(offs, strat[col].values, width=width, color=color, label=str(col))
    ax.set_xticks([i + width * (len(strat.columns) - 1) / 2 for i in range(len(idx))])
    ax.set_xticklabels(idx)
    ax.set_title(f"Controlled for {confounder}: {focus} is strongest everywhere",
                 color=TRUTH_COLOR)
    ax.set_xlabel(confounder)
    ax.legend(title=treatment, fontsize=8)

    for a in axes:
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path
