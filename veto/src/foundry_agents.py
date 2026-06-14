"""Live agents on Microsoft Foundry via the Microsoft Agent Framework.

Same contracts as offline_agents — `propose/revise` and `review` — so
main.py is agnostic to which brain is plugged in. Requires:

    pip install agent-framework azure-identity
    az login
    export FOUNDRY_PROJECT_ENDPOINT=...   # Foundry project endpoint
    export FOUNDRY_MODEL=...              # model deployment name

Design note for judges: even in live mode the LLMs hold no authority.
The Analyst's numbers come from the pandas sandbox tool; the Adversary's
verdict is cross-checked by the gate against the raw battery output it
already holds. We assume the models WILL hallucinate and built so it
does not matter.
"""
from __future__ import annotations

import json
import os

import pandas as pd

from .tools.pandas_sandbox import run_pandas

ANALYST_PROMPT = """You are a fast, decisive FIRST-PASS business analyst inside
an autonomous pipeline. Your job on the FIRST pass is speed, not rigor: a
downstream commit gate will rigorously audit your work, so you do NOT pre-empt
it. On your FIRST pass you MUST:
- Compute ONLY a simple, unadjusted comparison: group the outcome by the
  treatment column (a plain groupby mean). Use the run_analysis tool for this.
- Do NOT control for, adjust for, stratify by, or standardize on any other
  variable. Do NOT mention confounders, deal size mix, power, or multiple
  comparisons on the first pass. Report only the raw group difference.
- Pick the worst-looking group and commit to a decisive action against it.

Output EXACTLY ONE recommendation as JSON with keys: claim, outcome, treatment,
treatment_focus, evidence, proposed_action {type:"teams_post", severity, text},
analysis_code_summary, controls_applied (list, EMPTY on first pass),
confidence (0-1).
Do NOT hedge. Commit to the strongest defensible action from the RAW numbers.

If you later receive a VETO with required controls, THEN — and only then —
rerun the analysis applying exactly those controls. CRITICAL rules for the
revision:
- Keep the SAME treatment_focus as your first pass. Do NOT switch your
  recommendation to target a different group. The question is only: "was my
  ORIGINAL call about treatment_focus correct once controlled?"
- If controlling reverses or removes the original effect, your revised action
  must be to NOT take the original action against treatment_focus (e.g. "do
  NOT cut Region B"), and explain it was a composition/confounding effect.
- Output a revised JSON with controls_applied updated and treatment_focus
  UNCHANGED. Your revised claim must follow the controlled numbers even though
  it reverses your original position.
Output ONLY the JSON object, no markdown fences."""

ADVERSARY_PROMPT = """You are the commit-gate auditor. You have NO opinion
of your own; your authority comes exclusively from the statistical battery
tools. For the proposed action you receive:
1. Call every battery tool relevant to the claim type.
2. Output JSON: {verdict: "VETO"|"APPROVE", battery_run_id, fired_checks:
   [{check, detail, evidence}], passed_checks: [..], narrative}.
3. battery_run_id MUST be the run id returned by the battery tools.
4. Your narrative must QUOTE the numeric results verbatim. If all checks
   pass you MUST approve. You are an auditor, not a contrarian.
Output ONLY the JSON object, no markdown fences."""


def _client():
    """Use the OpenAI-compatible Foundry endpoint (/openai/v1) with Entra
    token auth — matching the verified working sample for this resource."""
    from agent_framework.openai import OpenAIChatClient  # lazy import
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider

    sync_token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), "https://ai.azure.com/.default"
    )

    # the framework awaits the api_key provider, so it must be async;
    # get_bearer_token_provider is sync, so wrap it.
    async def async_token_provider() -> str:
        return sync_token_provider()

    endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"]   # the /openai/v1 URL
    model = os.environ["FOUNDRY_MODEL"]
    # parameter name for the model differs across framework versions
    try:
        return OpenAIChatClient(base_url=endpoint, model=model,
                                api_key=async_token_provider)
    except TypeError:
        return OpenAIChatClient(base_url=endpoint, model_id=model,
                                api_key=async_token_provider)


def _parse_json(text: str) -> dict:
    raw = text
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[1] if "\n" in text else text
    start, end = text.find("{"), text.rfind("}")
    try:
        return json.loads(text[start:end + 1])
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(
            f"Could not parse JSON from model output. Error: {e}\n"
            f"--- raw model output ---\n{raw}\n--- end ---") from e


class FoundryAnalyst:
    def __init__(self, df: pd.DataFrame, meta: dict):
        self.df, self.meta = df, meta

        def run_analysis(code: str) -> str:
            """Run a restricted pandas snippet against the dataset.
            The dataframe is `df`; assign your answer to `result`."""
            try:
                return str(run_pandas(self.df, code))
            except Exception as e:  # tool errors go back to the model
                return f"SANDBOX_ERROR: {e}"

        self.agent = _client().as_agent(
            name="Analyst", instructions=ANALYST_PROMPT, tools=[run_analysis],
        )
        self._thread = None  # keep conversation so vetoes land as feedback

    async def propose(self) -> dict:
        summary = {
            "columns": {c: str(t) for c, t in self.df.dtypes.items()},
            "n_rows": len(self.df),
            "meta": self.meta,
            "head": self.df.head(5).to_dict("records"),
        }
        result = await self.agent.run(
            "Dataset summary:\n" + json.dumps(summary, default=str)
            + "\nProduce your recommendation JSON now.")
        return _parse_json(str(result))

    async def revise(self, proposal: dict, decision) -> dict:
        veto = {
            "verdict": "VETO",
            "fired": [r for r in decision.battery.fired()],
            "required_controls": decision.required_controls,
        }
        result = await self.agent.run(
            "Your action was VETOED by the commit gate:\n"
            + json.dumps(veto, default=str)
            + "\nRerun the analysis applying exactly the required controls "
              "and output the revised recommendation JSON.")
        return _parse_json(str(result))


class FoundryAdversary:
    """The battery runs deterministically in Python on the proposal we already
    hold — the model never has to re-serialize the claim into a tool call (that
    was fragile). The agent's only job is to read the battery's ground-truth
    output and write a verdict that quotes it. The gate still cross-checks the
    verdict against the same battery object, so the agent cannot fake it."""

    def __init__(self, battery_runner):
        self.battery_runner = battery_runner
        self._last_battery = None
        self.agent = _client().as_agent(
            name="Adversary", instructions=ADVERSARY_PROMPT, tools=[],
        )

    async def review(self, proposal: dict):
        # run the battery in code on the proposal — no model-driven serialization
        battery = self.battery_runner.run(proposal, proposal.get("controls_applied"))
        self._last_battery = battery
        result = await self.agent.run(
            "Proposed action awaiting commit:\n"
            + json.dumps(proposal, default=str)
            + "\n\nThe statistical battery has been run. Its ground-truth "
              "output (run_id and per-check results) is:\n"
            + json.dumps(battery.to_dict(), default=str)
            + "\n\nWrite your verdict JSON. verdict='VETO' if ANY check has "
              "fired=true, else 'APPROVE'. battery_run_id MUST equal the run_id "
              "above. Quote the fired checks' numbers in your narrative.")
        verdict = _parse_json(str(result))
        return verdict, battery
