"""Gate tests: prove the anti-hallucination cross-check.
The Adversary CANNOT approve or veto anything by itself — battery truth
always decides, and discrepancies are flagged and logged."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.battery.runner import BatteryResult
from src.gate import CommitGate, State


class _NullAudit:
    def log_review(self, *a, **k):
        pass


def _battery(fired: bool) -> BatteryResult:
    res = BatteryResult(run_id="run_test")
    res.results.append({
        "check": "confounding", "fired": fired, "summary": "test",
        "details": ([{"required_control": "control X"}] if fired else []),
    })
    return res


def test_hallucinated_approval_is_overridden():
    """Adversary says APPROVE, battery says fired -> gate vetoes anyway."""
    gate = CommitGate(_NullAudit())
    verdict = {"verdict": "APPROVE", "battery_run_id": "run_test"}
    d = gate.review({}, verdict, _battery(fired=True))
    assert d.state == State.VETOED
    assert d.override == "adversary approved but battery checks fired"


def test_hallucinated_veto_is_overridden():
    """Adversary says VETO, battery is clean -> gate approves anyway."""
    gate = CommitGate(_NullAudit())
    verdict = {"verdict": "VETO", "battery_run_id": "run_test"}
    d = gate.review({}, verdict, _battery(fired=False))
    assert d.state == State.APPROVED
    assert d.override == "adversary vetoed but battery is clean"


def test_wrong_run_id_is_flagged():
    gate = CommitGate(_NullAudit())
    verdict = {"verdict": "APPROVE", "battery_run_id": "run_FAKE"}
    d = gate.review({}, verdict, _battery(fired=False))
    assert d.override == "adversary cited wrong/absent battery run id"
    assert d.state == State.APPROVED  # battery truth still decides


def test_escalation_after_max_cycles():
    """Gate fails closed: persistent vetoes escalate to a human."""
    gate = CommitGate(_NullAudit())
    verdict = {"verdict": "VETO", "battery_run_id": "run_test"}
    for _ in range(CommitGate.MAX_CYCLES - 1):
        d = gate.review({}, verdict, _battery(fired=True))
        assert d.state == State.VETOED
    d = gate.review({}, verdict, _battery(fired=True))
    assert d.state == State.ESCALATED_TO_HUMAN


if __name__ == "__main__":
    fns = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS  {fn.__name__}")
    print(f"\n{len(fns)}/{len(fns)} gate tests passed")
