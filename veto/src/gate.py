"""CommitGate — the product.

A deterministic state machine. Agents propose and critique; only this
code holds execution keys. The Adversary's verdict is cross-checked
against the raw battery output the gate already holds — a hallucinated
approval or veto is overridden by battery truth and logged.

States: PROPOSED -> UNDER_REVIEW -> (VETOED -> REVISED -> UNDER_REVIEW)*
        -> APPROVED -> EXECUTED, or ESCALATED_TO_HUMAN after MAX_CYCLES.
No LLM calls live in this file. That is the point.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .battery.runner import BatteryResult


class State(str, Enum):
    PROPOSED = "PROPOSED"
    UNDER_REVIEW = "UNDER_REVIEW"
    VETOED = "VETOED"
    REVISED = "REVISED"
    APPROVED = "APPROVED"
    EXECUTED = "EXECUTED"
    ESCALATED_TO_HUMAN = "ESCALATED_TO_HUMAN"


@dataclass
class GateDecision:
    state: State
    battery: BatteryResult
    adversary_verdict: dict
    override: str | None = None  # set when battery truth overrode the agent
    required_controls: list[str] = field(default_factory=list)


class CommitGate:
    MAX_CYCLES = 3

    def __init__(self, audit):
        self.audit = audit
        self.cycles = 0

    def review(self, action: dict, adversary_verdict: dict,
               battery: BatteryResult) -> GateDecision:
        """Adjudicate one review cycle. Battery output is authoritative."""
        self.cycles += 1
        truth_fired = battery.any_fired()
        agent_says_veto = adversary_verdict.get("verdict") == "VETO"
        override = None

        # --- anti-hallucination cross-check -------------------------------
        if adversary_verdict.get("battery_run_id") != battery.run_id:
            override = "adversary cited wrong/absent battery run id"
        elif agent_says_veto and not truth_fired:
            override = "adversary vetoed but battery is clean"
        elif (not agent_says_veto) and truth_fired:
            override = "adversary approved but battery checks fired"

        final_veto = truth_fired  # battery truth decides, always
        # -------------------------------------------------------------------

        if final_veto and self.cycles >= self.MAX_CYCLES:
            state = State.ESCALATED_TO_HUMAN
        elif final_veto:
            state = State.VETOED
        else:
            state = State.APPROVED

        decision = GateDecision(
            state=state,
            battery=battery,
            adversary_verdict=adversary_verdict,
            override=override,
            required_controls=battery.required_controls(),
        )
        self.audit.log_review(self.cycles, action, decision)
        return decision
