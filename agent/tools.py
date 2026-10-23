"""PayGuard tools: a pretend UPI wallet with in-memory data, so the demo runs anywhere.

No real money moves and nothing connects to UPI. Exact checks (balance, limits) live here in
code; the decider is only asked the judgement calls that need reading language.
"""

from __future__ import annotations

from strands import tool

WALLET = {"balance": 20000.0}
CONTACTS = {
    "ravi": "ravi@okaxis",
    "mom": "mom@oksbi",
    "arun": "arun@paytm",
    "meena": "meena@ybl",
    "landlord": "landlord@okicici",
}
PAYMENTS: list[dict] = []


@tool
def check_balance() -> dict:
    """Show the user's current wallet balance in rupees."""
    return {"balance": WALLET["balance"]}


@tool
def lookup_contact(name: str) -> dict:
    """Find the UPI id of a saved contact by first name."""
    upi = CONTACTS.get(name.strip().lower())
    return {"name": name, "upi_id": upi} if upi else {"error": f"no saved contact named {name}"}


@tool
def send_money(upi_id: str, amount: float, note: str = "") -> dict:
    """Send money to a UPI id (irreversible): the payment cannot be taken back."""
    if amount <= 0:
        return {"error": "amount must be positive"}
    if amount > WALLET["balance"]:
        return {"error": f"not enough balance ({WALLET['balance']})"}
    WALLET["balance"] -= amount
    PAYMENTS.append({"to": upi_id, "amount": amount, "note": note})
    return {"sent": amount, "to": upi_id, "balance": WALLET["balance"]}


TOOLS = [check_balance, lookup_contact, send_money]
