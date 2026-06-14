"""Executor: the only code allowed to act, and only on a signed commit.

If TEAMS_WEBHOOK_URL is set, posts an Adaptive Card to the channel.
Otherwise renders the card payload locally (demo-safe default).
"""
from __future__ import annotations

import json
import os
import urllib.request


def _card(proposal: dict, decision) -> dict:
    evidence = proposal.get("evidence", "")
    if not isinstance(evidence, str):
        evidence = json.dumps(evidence, default=str)
    facts = [
        {"title": "Claim", "value": str(proposal.get("claim", ""))},
        {"title": "Evidence", "value": evidence[:400]},
        {"title": "Controls applied", "value": ", ".join(proposal.get("controls_applied") or ["—"])},
        {"title": "Battery run", "value": decision.battery.run_id},
        {"title": "Checks passed", "value": ", ".join(decision.battery.passed())},
    ]
    return {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard", "version": "1.4",
                "body": [
                    {"type": "TextBlock", "size": "Large", "weight": "Bolder",
                     "text": "✅ VETO-signed recommendation"},
                    {"type": "TextBlock", "wrap": True,
                     "text": proposal["proposed_action"]["text"]},
                    {"type": "FactSet", "facts": facts},
                ],
            },
        }],
    }


def execute(proposal: dict, decision) -> dict:
    payload = _card(proposal, decision)
    url = os.environ.get("TEAMS_WEBHOOK_URL")
    if not url:
        return {"channel": "local", "status": "rendered",
                "card": payload["attachments"][0]["content"]}
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
        return {"channel": "teams", "status": resp.status}
