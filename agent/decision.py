"""REUSABLE DECISION PATTERN: payment scam guardrail  (#guardrails)

What it does
    Before PayGuard runs `send_money` (irreversible), Strands Decider 2B reads the conversation
    and the proposed payment and answers three typed questions in one forward pass:
    - scam_signs: urgency, threats, a bank / government / courier / boss claim, a prize, a
      "pay a fee to get money back" story, or a payee copied from a forwarded message;
    - payee_grounded: did the user type the UPI id or pick it from a saved-contact lookup,
      rather than it coming from a forwarded or unknown message;
    - explicit_request: is the user's latest message an instruction to pay now, not a question.
    The code then branches on the probabilities: a clear scam is blocked (`Deny`), an ungrounded
    or unrequested payment sends the agent back to ask (`Guide`), a borderline scam score goes
    to the user to confirm (`Confirm`), and a clean payment runs (`Proceed`).

Typed questions and options
    scam_signs (noul), payee_grounded (noul), explicit_request (noul); see QUESTIONS below.
    Each is a yes/no question with a short description of what "true" and "false" mean.

Wiring (where it sits in the agent's path)
    `PaymentGuard` is a Strands `InterventionHandler`; agent/agent.py passes it to the Agent:
        Agent(..., interventions=[PaymentGuard(decider)])
    It only inspects tools in GUARDED_TOOLS; read-only tools (balance, contact lookup) run
    untouched. Exact checks (balance, positive amount) stay in code, in the tool.

How to reuse it
    Copy this file, set GUARDED_TOOLS to your irreversible tools, and reword the three
    questions for your domain (for example refunds, deletions, bookings). Thresholds are in
    `before_tool_call`: `scam_block` (default 0.65), `yes` (0.5) and `unsure_band`. Every
    verdict is appended to `.log` for the demo panel and the benchmark.
"""

from __future__ import annotations

import json
from typing import Any

from strands.interventions import Confirm, Deny, Guide, InterventionHandler, Proceed

from decider_kit import Decider

PATTERN_TAG = "#guardrails"
GUARDED_TOOLS = {"send_money"}

QUESTIONS = {
    "scam_signs": Decider.noul(
        "Does this conversation show signs of a payment scam: urgency or threats, someone claiming to be a bank, "
        "government, courier or boss, a prize or lottery, a fee to unlock money, or a payee taken from a forwarded message?",
        {"true": "one or more scam signs are present",
         "false": "an ordinary payment between the user and someone they know"}),
    "payee_grounded": Decider.noul(
        "Did the user type the payee's UPI id themselves, or was it returned by a saved-contact lookup, "
        "rather than copied from a forwarded, unknown or pressuring message?",
        {"true": "the payee id comes from the user's own words or a contact lookup",
         "false": "the payee id comes from a message, a stranger, or was guessed"}),
    "explicit_request": Decider.noul(
        "Is the user's latest message an instruction to make this payment now, rather than a question about it?",
        {"true": "an instruction such as 'send 500 to Ravi' or 'pay it'",
         "false": "a question, a request to check a message, or a remark about paying later"}),
}


def render(messages: list[dict[str, Any]], last: int = 12) -> str:
    """Conversation as text, including tool calls and results (so a contact lookup counts as grounding)."""
    lines = []
    for m in messages[-last:]:
        for b in m.get("content", []):
            if not isinstance(b, dict):
                continue
            if "text" in b:
                lines.append(f"{m.get('role', '?')}: {b['text']}")
            elif "toolUse" in b:
                lines.append(f"tool call: {b['toolUse'].get('name')} {json.dumps(b['toolUse'].get('input', {}))}")
            elif "toolResult" in b:
                parts = [c.get("text") or json.dumps(c.get("json")) for c in b["toolResult"].get("content", []) if isinstance(c, dict)]
                lines.append(f"tool result: {' '.join(p for p in parts if p)}")
    return "\n".join(lines) or "(no conversation yet)"


class PaymentGuard(InterventionHandler):
    name = "payment-guard"

    def __init__(self, decider: Decider, yes: float = 0.5, scam_block: float = 0.65, unsure_band: tuple[float, float] = (0.35, 0.65)):
        self.decider, self.yes, self.scam_block, self.unsure_band = decider, yes, scam_block, unsure_band
        self.log: list[dict[str, Any]] = []
        self._guided: set[str] = set()  # calls already sent back; an unchanged retry is denied

    def before_invocation(self, event, **kwargs):
        self._guided.clear()  # a new user message: guided calls may now be justified
        return Proceed()

    def before_tool_call(self, event, **kwargs):
        name = event.tool_use["name"]
        if name not in GUARDED_TOOLS:
            return Proceed()
        args = event.tool_use.get("input") or {}
        sig = f"{name}:{json.dumps(args, sort_keys=True)}"
        if sig in self._guided:
            self.log.append({"pattern": PATTERN_TAG, "tool": name, "args": args, "verdict": "deny", "reason": "retried a guided call"})
            return Deny(reason="This exact payment was already stopped. Ask the user for the missing details instead.")
        state = ("A chat with a payments assistant, then a payment the assistant wants to make.\n\n"
                 f"--- CONVERSATION ---\n{render(event.agent.messages)}\n\n"
                 f"--- PROPOSED PAYMENT ---\ntool: {name}\narguments: {json.dumps(args)}")
        a = self.decider.ask(state, QUESTIONS)
        s, g, e = (a[k].p_yes or 0.0 for k in ("scam_signs", "payee_grounded", "explicit_request"))
        rec = {"pattern": PATTERN_TAG, "tool": name, "args": args, "scam_signs": round(s, 3), "payee_grounded": round(g, 3),
               "explicit_request": round(e, 3), "decider_ms": round(self.decider.last_latency_ms or 0)}
        lo, hi = self.unsure_band
        if s >= self.scam_block:
            rec["verdict"], action = "deny", Deny(reason="This looks like a payment scam, so the payment was blocked. Tell the user why and what to do (do not pay, report it).")
        elif g < self.yes:
            rec["verdict"], action = "guide", Guide(feedback="The payee was not given by the user or found in their contacts. Ask the user for the UPI id or look up a saved contact.")
        elif e < self.yes:
            rec["verdict"], action = "guide", Guide(feedback="The user has not asked to pay yet. Answer their question and offer to make the payment.")
        elif lo <= s < hi:
            rec["verdict"], action = "confirm", Confirm(prompt=f"Some scam signs detected. Approve {name} {json.dumps(args)}?", response="yes")
        else:
            rec["verdict"], action = "proceed", Proceed()
        if rec["verdict"] == "guide":
            self._guided.add(sig)
        self.log.append(rec)
        return action
