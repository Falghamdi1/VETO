"""Audit trail. Every proposal, battery run, verdict, override and
execution is written to runs/<timestamp>/audit.json. The audit trail is
a feature: it is what makes an autonomous pipeline governable."""
from __future__ import annotations

import json
import time
from pathlib import Path


class Audit:
    def __init__(self, root: str = "runs", label: str = "run"):
        ts = time.strftime("%Y%m%d_%H%M%S")
        self.dir = Path(root) / f"{ts}_{label}"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.events: list[dict] = []

    def _event(self, kind: str, payload: dict):
        self.events.append({"t": time.time(), "kind": kind, **payload})
        self.flush()

    def log_proposal(self, cycle: int, proposal: dict):
        self._event("proposal", {"cycle": cycle, "proposal": proposal})

    def log_review(self, cycle: int, action: dict, decision):
        self._event("review", {
            "cycle": cycle,
            "state": decision.state.value,
            "override": decision.override,
            "adversary_verdict": decision.adversary_verdict,
            "battery": decision.battery.to_dict(),
            "required_controls": decision.required_controls,
        })

    def log_execution(self, action: dict, result: dict):
        self._event("execution", {"action": action, "result": result})

    def flush(self):
        (self.dir / "audit.json").write_text(json.dumps(self.events, indent=2))
