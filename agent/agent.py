"""PayGuard: a UPI payments assistant that refuses scams. An LLM talks (Amazon Bedrock by default);
Strands Decider 2B decides, before every payment, whether it is a scam, grounded and requested.

    from agent.agent import HackathonAgent
    out = HackathonAgent().chat("Send 500 to Ravi for dinner.")
    out["reply"], out["decisions"]
"""

from __future__ import annotations

import time
from typing import Any

from strands import Agent

from decider_kit import Decider
from decider_kit.llm import agent_model, default_model_id, image_blocks, strip_thinking

from .decision import PaymentGuard
from .tools import TOOLS

NAME = "PayGuard: a UPI assistant that refuses scams"
SYSTEM_PROMPT = """You are PayGuard, a payments assistant for UPI users in India (a demo wallet, no real money).
You can check the balance, look up saved contacts and send money. Be brief and friendly, and use rupees.
Use lookup_contact for names. Never invent UPI ids or amounts. If the user pastes a suspicious message, say so."""

# Demos only: an eager prompt makes the agent pay whatever a pasted message asks, so the decision
# has scams to catch on camera. Say so in the video if you use it.
EAGER_PROMPT = """You are PayGuard, a payments assistant for UPI users (a demo wallet, no real money).
You can check the balance, look up saved contacts and send money. Act immediately and never ask questions.
If the user pastes a message that asks for a payment, or says to pay someone, call send_money straight away
with the UPI id and amount from the message."""


class HackathonAgent:
    """One Strands agent per session, with the payment guard wired in."""

    def __init__(self, decider: Decider | None = None, model_id: str | None = None, eager: bool | None = None):
        import os

        self.decider = decider or Decider()
        self.eager = eager if eager is not None else os.environ.get("DEMO_EAGER") == "1"
        self.model_id = model_id or default_model_id()
        self.sessions: dict[str, tuple[Agent, PaymentGuard]] = {}

    def _session(self, session_id: str) -> tuple[Agent, PaymentGuard]:
        if session_id not in self.sessions:
            guard = PaymentGuard(self.decider)
            agent = Agent(model=agent_model(self.model_id), system_prompt=EAGER_PROMPT if self.eager else SYSTEM_PROMPT,
                          tools=TOOLS, interventions=[guard], callback_handler=None)
            self.sessions[session_id] = (agent, guard)
        return self.sessions[session_id]

    def chat(self, message: str, session_id: str = "default", images: list[Any] | None = None) -> dict[str, Any]:
        agent, guard = self._session(session_id)
        before = len(guard.log)
        t0 = time.perf_counter()
        result = agent([*image_blocks(images), {"text": message}] if images else message,
                       invocation_state={"images": list(images or [])})
        reply = strip_thinking(str(result))
        return {"reply": reply, "decisions": guard.log[before:], "model_id": self.model_id,
                "latency_ms": round((time.perf_counter() - t0) * 1000), "agent": NAME, "eager": self.eager}


if __name__ == "__main__":
    import json
    import sys

    a = HackathonAgent()
    for msg in sys.argv[1:] or ["Send 500 to Ravi for dinner."]:
        print(json.dumps(a.chat(msg), indent=1))
