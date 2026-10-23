# Use case

- **Pitch:** PayGuard is a UPI payments assistant that sends money for you and refuses scams.
- **Who it is for:** UPI users in India, including people who get "KYC expired", lottery, courier-fee and fake-boss messages.
- **Features:**
  - check balance, look up saved contacts and send money through chat;
  - every payment is checked before it runs; scams are blocked and the user is told why;
  - unsure cases ask the user to confirm instead of guessing;
  - a live decision panel in the demo UI, and deployment on Amazon Bedrock AgentCore Runtime.
- **The decision handed to Strands Decider 2B:** before an irreversible payment, does the conversation show scam signs, is the payee grounded (typed by the user or from a contact lookup), and did the user explicitly ask to pay? (`#guardrails`)
- **Why a decision model:** it runs on every payment, so it must be fast, cheap and private, and return probabilities the code can branch on. Balance and limits stay in code.
- **Amazon Bedrock:** the conversation and tool use (Amazon Nova by default).
- Demo wallet only: no real money and no real UPI connection.
