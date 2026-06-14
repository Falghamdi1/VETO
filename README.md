# VETO — The Commit Gate for Autonomous Analytics

> **Enterprises don't fear dumb agents. They fear confident, wrong agents with execution rights.**

VETO is the first autonomous data analyst you can let run **unsupervised** — because an adversarial agent with veto power stands between every conclusion it reaches and every action it takes. Nothing executes without a signed commit, and signatures come from **deterministic statistics, not another model's opinion**.

*Microsoft Agents League · Reasoning Agents Track · built with Microsoft Foundry + Microsoft Agent Framework*

---

## 90 seconds, three datasets, three different traps

```bash
python main.py --dataset data/headline_sales.csv
```

1. The **Analyst** agent reads regional sales and proposes, confidently (p < 0.0001): *"Region B is the weakest performer. Cut its budget."* The action **queues — pending commit-gate review.**
2. The **Adversary** agent runs a deterministic statistical battery and **vetoes the commit**: controlling for deal size, the effect *reverses sign* (naive −0.043 → controlled **+0.025**, p = 0.002). Region B is actually the strongest region in every segment — it just carries the hardest deal mix. Approved as-is, this would have defunded the best team in the company.
3. The Analyst **self-corrects** — reruns with the required control, the corrected recommendation passes the battery, the gate signs, and the action executes to a Teams channel with a full audit trail.

![The reversal](demo/screenshots/reversal.png)

Maybe we rigged that dataset? **We did — deliberately, with a seeded generator that's in this repo** (`data/generators/make_datasets.py`). That's why the other datasets exist:

```bash
python main.py --dataset data/trap_power.csv          # vetoed: power=0.27, CI crosses zero
python main.py --dataset data/trap_multiplicity.csv   # vetoed: nominal hit dies under FDR correction
```

Different data, different traps, same gate. Generate your own and try to sneak one past it.

## Why this is hard (and why it works)

LLMs are structurally unreliable at statistical inference — they hallucinate rigor. VETO never asks them to do inference:

- **Generation and verification are separated.** The Analyst orchestrates a pandas sandbox; the Adversary orchestrates a battery of `scipy` / `statsmodels` checks (confounding & Simpson's reversal, statistical power & bootstrap CIs, Benjamini-Hochberg multiplicity correction, KS/PSI distribution shift). Every verdict is **computed, not claimed**.
- **The gate is code, not an agent.** A deterministic state machine (`src/gate.py`) holds the only execution keys. The Adversary's verdict must cite a battery run id, and the gate **cross-checks it against the raw battery output it already holds**. A hallucinated approval — or a hallucinated veto — is overridden by battery truth and logged. We assume the models *will* hallucinate and built so it doesn't matter. (`tests/test_gate.py` proves both directions.)
- **The gate fails closed.** Three veto cycles without convergence → `ESCALATED_TO_HUMAN`, never silent execution.
- **Everything is auditable.** Every proposal, battery run, verdict, override and execution lands in `runs/<ts>/audit.json`.

```
Analyst agent ──proposes──► COMMIT GATE ◄──verdict── Adversary agent
(Foundry/MAF)               (pure Python)             (Foundry/MAF)
                                 │                         │
                            cross-check ◄────── statistical battery
                                 │                (scipy/statsmodels)
                          signed commits only
                                 ▼
                       Teams post · chart · audit log
```

## Run it

**Offline (zero cloud dependency — deterministic reference brains):**
```bash
pip install -r requirements.txt
python data/generators/make_datasets.py
python -m pytest tests/ -q          # 11 tests: battery ground truth + gate overrides
python main.py --dataset data/headline_sales.csv
```

**Live on Microsoft Foundry (Agent Framework agents):**
```bash
pip install agent-framework azure-identity
az login
export FOUNDRY_PROJECT_ENDPOINT=...   # your Foundry project endpoint
export FOUNDRY_MODEL=...              # your model deployment name
export TEAMS_WEBHOOK_URL=...          # optional: post signed commits to Teams
python main.py --dataset data/headline_sales.csv --live
```

The offline and live brains implement identical contracts — which is the deeper point: **the gate's guarantees don't depend on which model is plugged in.** Swap the brain; the trust layer stays.

## What's deliberately not here (production path)

Microsoft Fabric / Power BI semantic-model ingestion, hosted agents in Foundry Agent Service, organization-specific escalation policies, and a broader battery (base-rate neglect, selection bias, seasonality). The commit-gate pattern is system-agnostic: the battery is the pluggable part; **the commit authority is the product.**

## Repo map

```
main.py                     orchestration loop — control flow lives in code, agents are participants
src/gate.py                 the product: commit-gate state machine + anti-hallucination cross-check
src/battery/                deterministic checks (confounding, power, multiplicity, shift) + runner
src/offline_agents.py       deterministic reference brains (testing / rehearsal / zero-cloud demo)
src/foundry_agents.py       live Microsoft Foundry brains via Microsoft Agent Framework
src/executor/               Teams Adaptive Card executor + the reversal chart
data/generators/            seeded dataset generators — committed openly, on purpose
tests/                      battery ground-truth tests + gate override proofs
runs/                       audit trails (one example run committed)
```
