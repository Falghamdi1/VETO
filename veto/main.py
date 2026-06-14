"""VETO — the commit gate for autonomous analytics.

    python main.py --dataset data/headline_sales.csv            # offline brains
    python main.py --dataset data/headline_sales.csv --live     # Foundry agents

Control flow lives HERE, in deterministic code — agents are participants,
not controllers. That is the design thesis.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

import pandas as pd

from src.audit import Audit
from src.battery.runner import BatteryRunner
from src.gate import CommitGate, State
from src.executor.teams import execute
from src.executor.chart import reversal_chart

# ----- demo-grade terminal styling -----------------------------------------
R, G, Y, C, B, DIM, END = "\033[91m", "\033[92m", "\033[93m", "\033[96m", "\033[1m", "\033[2m", "\033[0m"


def banner(text, color=C):
    line = "─" * 64
    print(f"\n{color}{B}{line}\n  {text}\n{line}{END}")


def beat(t=0.6):
    time.sleep(t)


def show_proposal(p, label="ANALYST PROPOSES"):
    banner(label, Y)
    print(f"{B}Claim:{END}      {p['claim']}")
    print(f"{B}Evidence:{END}   {p['evidence']}")
    print(f"{B}Action:{END}     {p['proposed_action']['text']}")
    print(f"{B}Analysis:{END}   {DIM}{p['analysis_code_summary']}{END}")
    print(f"{B}Status:{END}     {Y}⏸  QUEUED — PENDING COMMIT-GATE REVIEW{END}")


def show_verdict(verdict, decision):
    if decision.state in (State.VETOED, State.ESCALATED_TO_HUMAN):
        banner("ADVERSARY VERDICT — COMMIT BLOCKED", R)
        print(f"{R}{B}✗ VETO{END}  {DIM}(battery {decision.battery.run_id}){END}")
        for r in decision.battery.fired():           # ground truth, fixed shape
            print(f"  {R}▸ [{r['check']}]{END} {r['summary']}")
            for ev in r["details"]:
                for k, v in ev.items():
                    if k not in ("required_control", "nominal_hits"):
                        print(f"      {DIM}{k} = {v}{END}")
        print(f"{B}Required controls:{END}")
        for rc in decision.required_controls:
            print(f"  {Y}→ {rc}{END}")
    else:
        banner("ADVERSARY VERDICT — COMMIT SIGNED", G)
        print(f"{G}{B}✓ APPROVE{END}  {DIM}(battery {decision.battery.run_id}){END}")
        print(f"  checks passed: {', '.join(decision.battery.passed())}")
    if decision.override:
        print(f"{R}{B}⚠ GATE OVERRIDE:{END} {decision.override} — battery truth applied")


async def run(dataset: str, live: bool):
    data_path = Path(dataset)
    meta = json.loads(data_path.with_suffix("").with_suffix(".meta.json").read_text()
                      if data_path.with_suffix(".meta.json").exists()
                      else Path(str(data_path).replace(".csv", ".meta.json")).read_text())
    df = pd.read_csv(data_path)

    banner(f"VETO  ·  dataset: {data_path.name}  ·  {len(df):,} rows  ·  "
           f"brains: {'Microsoft Foundry (live)' if live else 'offline deterministic'}")
    print(f"{DIM}{meta.get('story', '')}{END}")

    audit = Audit(label=data_path.stem)
    battery_runner = BatteryRunner(df, meta)
    gate = CommitGate(audit)

    if live:
        from src.foundry_agents import FoundryAnalyst, FoundryAdversary
        analyst = FoundryAnalyst(df, meta)
        adversary = FoundryAdversary(battery_runner)
        proposal = await analyst.propose()
    else:
        from src.offline_agents import OfflineAnalyst, OfflineAdversary
        analyst = OfflineAnalyst(df, meta)
        adversary = OfflineAdversary()
        proposal = analyst.propose()

    audit.log_proposal(1, proposal)
    show_proposal(proposal)
    beat()

    decision = None
    for cycle in range(1, CommitGate.MAX_CYCLES + 1):
        if live:
            verdict, battery = await adversary.review(proposal)
        else:
            battery = battery_runner.run(proposal, proposal.get("controls_applied"))
            verdict = adversary.review(proposal, battery)

        decision = gate.review(proposal["proposed_action"], verdict, battery)
        show_verdict(verdict, decision)
        beat()

        if decision.state == State.APPROVED:
            break
        if decision.state == State.ESCALATED_TO_HUMAN:
            banner("ESCALATED TO HUMAN — gate fails closed, never open", R)
            print("Full audit trail:", audit.dir / "audit.json")
            return

        # self-correction: rerun with exactly the required controls
        banner("ANALYST SELF-CORRECTS — rerunning with required controls", C)
        proposal = (await analyst.revise(proposal, decision)) if live \
            else analyst.revise(proposal, decision)
        audit.log_proposal(cycle + 1, proposal)
        show_proposal(proposal, label="ANALYST PROPOSES (REVISED)")
        beat()

    # ----- execution: only reachable with a signed commit -------------------
    result = execute(proposal, decision)
    audit.log_execution(proposal["proposed_action"], result)
    banner("EXECUTED — signed commit released to channel", G)
    print(f"{G}{B}▶ {proposal['proposed_action']['text']}{END}")
    print(f"{DIM}channel: {result['channel']}  ·  audit: {audit.dir / 'audit.json'}{END}")

    # the reversal chart, when the story was a confound
    if any(c in (proposal.get("controls_applied") or [])
           for c in meta.get("candidate_confounders", [])):
        conf = next(c for c in proposal["controls_applied"]
                    if c in meta["candidate_confounders"])
        chart = reversal_chart(df, meta["outcome"], meta["treatment"],
                               proposal["treatment_focus"], conf,
                               str(audit.dir / "reversal.png"))
        print(f"{DIM}reversal chart: {chart}{END}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="VETO — commit gate for autonomous analytics")
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--live", action="store_true",
                    help="use Microsoft Foundry agents (requires az login + env vars)")
    args = ap.parse_args()
    asyncio.run(run(args.dataset, args.live))
