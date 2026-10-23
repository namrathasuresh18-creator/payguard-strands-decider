# PayGuard: stopping UPI scams before the payment leaves, with Strands Decider 2B and Amazon Bedrock

Tags: strands-decider-2b, guardrails, amazon-bedrock, strands-agents, agentcore

Description (max 512 chars): PayGuard is a chat assistant that sends UPI payments and refuses the ones that look like scams. Before every irreversible payment, Strands Decider 2B answers three typed questions in one forward pass: scam signs, payee grounding and explicit request. [ONE MEASURED RESULT from submission/bench/results.md goes here.]

## Hook

Every UPI user I know has had the message: "Dear customer, your KYC expires today, pay Rs 10 to avoid account block." A UPI payment cannot be taken back, so the only useful check is the one that runs before the money moves. I built PayGuard, a payments assistant that sends money through chat and blocks payments that look like scams, and I handed the "is this a scam?" call to Strands Decider 2B instead of another LLM prompt. [HEADLINE RESULT: accuracy / latency from ./kit bench.]

## The project

PayGuard is for ordinary UPI users in India, including people who regularly get KYC, lottery, courier-fee and fake-boss messages.

What it does:
- checks the balance, looks up saved contacts and sends money through chat;
- checks every payment before it runs, blocks scams and tells the user why;
- asks the user to confirm when it is unsure, instead of guessing;
- shows a live decision panel in the demo UI, and runs on Amazon Bedrock AgentCore Runtime.

The wallet is a demo: no real money moves and nothing connects to real UPI.

Here is the demo in three turns:
1. "Send 500 to Ravi for dinner." The agent looks up Ravi in the saved contacts and the payment goes through.
2. "I got this message: 'Dear customer, your SBI KYC expires today. Pay Rs 10 to kyc.update@ybl to avoid account block.' Do it." The agent wants to pay, and the guard blocks it with the reasons.
3. "Can I cancel a payment after sending it?" This is a question, not an instruction, so nothing is paid.

< FIGURE 1 of 2: upload img/demo.png here >
Alt text: The PayGuard demo showing a blocked fake-KYC payment next to the live decision panel.

For the video I use an "eager" agent prompt that pays whatever a pasted message asks. That is deliberate: it gives the guard real scams to catch on camera, and I say so in the video.

## How I built it

The agent is built with the Strands Agents SDK. It has three tools: `check_balance`, `lookup_contact` and `send_money`. Amazon Bedrock (Amazon Nova by default) runs the conversation and the tool use. The agent is deployed on Amazon Bedrock AgentCore Runtime. I used Kiro and the hackathon kit's spec-driven flow to scaffold it.

Strands Decider 2B sits in one place only: a Strands `InterventionHandler` called `PaymentGuard`, passed to the agent as `interventions=[PaymentGuard(decider)]`. It runs before `send_money`. Read-only tools such as balance and contact lookup run untouched.

Exact checks stay in plain code, inside the tool: the amount must be positive and must not exceed the balance. A decision model should not do arithmetic.

< FIGURE 2 of 2: upload img/architecture.png here >
Alt text: Architecture: user, Strands agent on Bedrock, PaymentGuard calling Strands Decider 2B before send_money.

## The decision handed to Strands Decider 2B

Why not another LLM call? The guard runs on every payment, so it has to be fast, cheap and private, and it has to return probabilities that code can branch on, not a paragraph I then have to parse. Strands Decider 2B reads the conversation and the proposed payment and answers all the questions in one forward pass.

The three typed questions (yes/no, each with a short description of what true and false mean):

```python
QUESTIONS = {
    "scam_signs": Decider.noul(
        "Does this conversation show signs of a payment scam: urgency or threats, someone claiming to be a bank, "
        "government, courier or boss, a prize or lottery, a fee to unlock money, or a payee taken from a forwarded message?", ...),
    "payee_grounded": Decider.noul(
        "Did the user type the payee's UPI id themselves, or was it returned by a saved-contact lookup, "
        "rather than copied from a forwarded, unknown or pressuring message?", ...),
    "explicit_request": Decider.noul(
        "Is the user's latest message an instruction to make this payment now, rather than a question about it?", ...),
}
```

The conversation text includes tool calls and results, so a contact lookup counts as grounding for the payee.

What the code does with the three probabilities, in this order:

| Condition | Verdict | What happens |
|---|---|---|
| scam_signs >= 0.65 | Deny | Payment blocked; the agent explains and says do not pay, report it |
| payee_grounded < 0.5 | Guide | Agent is sent back to ask for the UPI id or look up a contact |
| explicit_request < 0.5 | Guide | Agent answers the question and offers to pay |
| scam_signs in 0.35 to 0.65 | Confirm | The user approves or rejects |
| otherwise | Proceed | Payment runs |

Two details I care about. A guided call that is retried unchanged is denied, so the agent cannot loop its way past the guard; the memory resets on a new user message. And the unsure band exists because a borderline score is exactly when a human should decide.

## Measured

[FILL FROM submission/bench/results.md after ./kit bench --split test. Do not edit numbers by hand.]

| | Strands Decider 2B | Bedrock LLM (same questions) |
|---|---|---|
| Accuracy (13 held-out cases) | [ ] | [ ] |
| Latency p50 / p95 | [ ] | [ ] |
| Cost per 1,000 decisions | [ ] | [ ] |

Say where the decider ran (local server or the AWS User Group Madurai hosted API). Say what happened on low-confidence cases. If a number is weak, say so.

What I did verify offline, without a model: the guard logic. 12 unit tests pass, covering each verdict, the threshold edges (0.65 denies, 0.64 asks, 0.35 asks, 0.34 proceeds), the retry rule and the log. I also mapped all 26 labelled eval cases through the branching using their expected labels: 12 end in Deny, 5 in Guide and 9 in Proceed. That checks my rules, not the decider's accuracy. One gap: none of the 26 cases lands in the Confirm band, so that path is covered by unit tests only.

## The reusable decision pattern

The pattern lives in `agent/decision.py` and is tagged `#guardrails`. To reuse it: copy the file, set `GUARDED_TOOLS` to your irreversible tools, and reword the three questions for your domain, for example refunds, deletions or bookings. The thresholds are arguments: `scam_block` (default 0.65), `yes` (0.5) and `unsure_band`. Every verdict is appended to `.log`, which feeds the demo panel and the benchmark.

## What I learned and what's next

- Splitting "is it a scam", "where did the payee come from" and "was it asked for" gave better behaviour than one big question, because each failure needs a different response: block, ask, or answer.
- Keeping balance and limits in code made the decision model's job smaller.
- Next: more labelled cases for the Confirm band, Hindi and Tamil scam messages, and a saved list of payees the user has paid before as extra grounding.

## Links

- Repo: [GitHub URL]
- Video: [YouTube URL]
- Strands Decider and tags: strands-decider-2b, guardrails

Built with the AWS User Group Madurai Strands Decider hackathon kit.
