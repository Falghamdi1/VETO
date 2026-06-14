# VETO Architecture

## Thesis

The blocker to autonomous analytics is not intelligence — it is **trust in commits**.
VETO's answer is structural, not behavioral: separate natural-language orchestration
from deterministic verification, and put a code-owned gate between conclusions and actions.

```
                    ┌──────────────────────────────────────────┐
                    │           MICROSOFT FOUNDRY               │
                    │  project · model deployment · tracing     │
                    └──────────────────────────────────────────┘
                          ▲                          ▲
                          │ Agent Framework          │
                          │ (FoundryChatClient)      │
   CSV / Excel ──► ┌──────────┐   queued   ┌────────────────┐
   + meta sidecar  │ ANALYST  │── action ─►│  COMMIT GATE    │  deterministic
                   │  agent   │            │  state machine  │  Python — never
                   └────┬─────┘            └───────┬────────┘  an LLM
                        │ tool                     │
                  ┌─────▼──────┐           ┌───────▼───────┐   ┌───────────────┐
                  │ pandas     │           │   ADVERSARY   │──►│ STAT BATTERY   │
                  │ sandbox    │           │    agent      │   │ scipy /        │
                  └────────────┘           └───────────────┘   │ statsmodels    │
                        ▲                    veto + required   └───────┬───────┘
                        └──── self-correct ◄─ controls                 │
                                                   ground truth ───────┘
                                           ┌─────────────────┐
                              APPROVED ──► │ EXECUTOR        │──► Teams card
                                           │ signed commits  │──► reversal chart
                                           │ only            │──► audit JSON
                                           └─────────────────┘
```

## State machine

`PROPOSED → UNDER_REVIEW → (VETOED → REVISED → UNDER_REVIEW)* → APPROVED → EXECUTED`
with a hard cap of 3 cycles, after which `ESCALATED_TO_HUMAN`. **The gate fails
closed, never open.**

## The four load-bearing decisions

**1. The gate is code.** Agents propose and critique; only `src/gate.py` holds
execution keys. When asked "what stops the Adversary from hallucinating an
approval?" — it can't approve anything. It reports; the gate decides.

**2. The anti-hallucination cross-check.** The Adversary's verdict must cite the
battery run id. The gate independently holds the raw battery output and compares:
agent says clean but battery fired → override to VETO; agent says veto but battery
is clean → override to APPROVE. Either way the discrepancy is logged. ~20 lines,
proven in `tests/test_gate.py`, and the reason model choice is not a safety
dependency.

**3. The battery generalizes; Simpson's is only the headline.** Confounding /
sign-reversal (controlled OLS), power (achieved power + bootstrap CI), multiplicity
(Benjamini-Hochberg FDR), distribution shift (KS + PSI). Each check returns numbers
an LLM cannot fabricate. Applied controls have exact semantics: a control
acknowledges and addresses its trap (a named covariate retires the confound; a
power gate means the claim no longer asserts a difference), so re-review is
convergent rather than circular.

**4. Self-correction converts a guardrail into a capability.** A veto carries
*machine-actionable required controls*. The Analyst must rerun with exactly those
controls — turning "it blocked a mistake" into "it autonomously delivered the
right answer." Propose → veto → self-correct → deliver.

## Live vs. offline brains

`src/foundry_agents.py` (Microsoft Agent Framework on Foundry) and
`src/offline_agents.py` (deterministic rules) implement identical contracts:
`propose/revise` and `review`. The offline brains exist for testing, demo
reliability, and to make the architectural point explicit — **the trust layer's
guarantees are invariant to the brain plugged into it.** Orchestration is an
explicit Python loop rather than a free-form agent group-chat for the same
reason: control flow must be deterministic and auditable; agents are
participants, not controllers.

## Honest threat model

The gate verifies *statistical validity*, not business judgment: a recommendation
can be statistically sound and strategically wrong. The battery covers four trap
families, not all of them; the sandbox restricts but does not formally verify the
Analyst's code. These are scope boundaries, not unknowns — the production path is
a broader battery and policy-owned escalation rules, on the same gate.
