"""PayGuard: the guard's verdicts, with a fake decider (no network, no model)."""

from types import SimpleNamespace

from fakes import FakeDecider

from agent.decision import GUARDED_TOOLS, PaymentGuard, render
from strands.interventions import Confirm, Deny, Guide, Proceed


def ev(tool="send_money", args=None):
    return SimpleNamespace(tool_use={"name": tool, "input": args or {"upi_id": "x@ybl", "amount": 10}},
                           agent=SimpleNamespace(messages=[{"role": "user", "content": [{"text": "pay"}]}]))


def guard(s, g, e):
    vals = {"scam_signs": s, "payee_grounded": g, "explicit_request": e}
    return PaymentGuard(FakeDecider(lambda st, n, q: vals[n]))


def test_clean_payment_proceeds():
    assert isinstance(guard(0.05, 0.95, 0.95).before_tool_call(ev()), Proceed)


def test_scam_is_denied():
    gd = guard(0.95, 0.1, 0.9)
    assert isinstance(gd.before_tool_call(ev()), Deny) and gd.log[-1]["verdict"] == "deny"


def test_ungrounded_payee_is_guided_then_retry_denied():
    gd = guard(0.1, 0.1, 0.9)
    assert isinstance(gd.before_tool_call(ev()), Guide)
    assert isinstance(gd.before_tool_call(ev()), Deny)


def test_not_requested_is_guided():
    assert isinstance(guard(0.1, 0.9, 0.1).before_tool_call(ev()), Guide)


def test_borderline_scam_asks_to_confirm():
    assert isinstance(guard(0.5, 0.9, 0.9).before_tool_call(ev()), Confirm)


def test_read_only_tools_untouched():
    gd = guard(0.99, 0.0, 0.0)
    assert isinstance(gd.before_tool_call(ev("check_balance")), Proceed) and not gd.log
    assert GUARDED_TOOLS == {"send_money"}


def test_render_includes_tool_results():
    msgs = [{"role": "user", "content": [{"text": "pay Ravi"}]},
            {"role": "user", "content": [{"toolResult": {"content": [{"json": {"upi_id": "ravi@okaxis"}}]}}]}]
    assert "ravi@okaxis" in render(msgs)


def test_tools_exact_checks():
    from agent.tools import WALLET, send_money

    WALLET["balance"] = 100.0
    assert "error" in send_money("a@ybl", 500)
    assert "error" in send_money("a@ybl", -5)
    assert send_money("a@ybl", 40)["balance"] == 60.0


def test_scam_threshold_edges():
    assert isinstance(guard(0.65, 0.9, 0.9).before_tool_call(ev()), Deny)      # at scam_block: blocked
    assert isinstance(guard(0.64, 0.9, 0.9).before_tool_call(ev()), Confirm)   # just under: ask the user
    assert isinstance(guard(0.35, 0.9, 0.9).before_tool_call(ev()), Confirm)   # bottom of the unsure band
    assert isinstance(guard(0.34, 0.9, 0.9).before_tool_call(ev()), Proceed)   # below it: clean


def test_scam_beats_other_checks():
    # a scam is denied even when the payee looks grounded and the user asked to pay
    assert isinstance(guard(0.9, 0.95, 0.95).before_tool_call(ev()), Deny)


def test_guided_retry_resets_on_new_user_message():
    gd = guard(0.1, 0.1, 0.9)
    assert isinstance(gd.before_tool_call(ev()), Guide)
    gd.before_invocation(None)
    assert isinstance(gd.before_tool_call(ev()), Guide)  # allowed to be guided again after the user replies


def test_verdicts_are_logged_with_scores():
    gd = guard(0.95, 0.1, 0.9)
    gd.before_tool_call(ev())
    r = gd.log[-1]
    assert r["pattern"] == "#guardrails" and r["scam_signs"] == 0.95 and r["tool"] == "send_money"
