# Finish and submit PayGuard (run on your own machine, in order)

Deadline: 23 Oct 2026, 11:59 p.m. PT (= 24 Oct, about 12:29 p.m. IST). Aim to finish tonight.

1. Unzip, open a terminal in the folder, run `./kit setup` (Windows: `.\kit setup`). Add your AWS
   User Group Madurai decider key and Bedrock access to `.env`. Never commit `.env`.
2. `./kit test`  then  `./kit run` and try the three demo messages.
3. `./kit bench --split test`  (real accuracy, latency, cost; do not edit numbers by hand).
4. `./kit deploy`  (needs your AWS account with Bedrock model access).
5. `./kit video --target agentcore`  -> upload `submission/video/` output to YouTube as Public.
6. `./kit article --draft`, edit `submission/ARTICLE_DRAFT.md` into your words, then
   `./kit article` until ready. Publish on AWS Builder Center with tags
   `#strands-decider-2b` and `#guardrails`.
7. `./kit readme` (adds your real numbers), `./kit check`, `./kit publish <your-repo-name>`.
8. On awsugmdu.in -> hackathon -> Submit: paste the Builder Center blog URL and the GitHub URL.
   Also submit the video link wherever the official Builder Center entry asks for it.
