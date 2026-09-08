# Roadmap

Work in acceptance criteria, not contribution streaks. Finish or explicitly defer one milestone before broadening the scope.

## M0 — Initial auditable CLI

- Strict schema and provenance consistency.
- Complete paired cohorts; retained errors and costs.
- Deterministic paired bootstrap and descriptive frontier.
- Synthetic fixture, meaningful tests, clean installation and CI.
- Clear limits on interpretation and no real-model performance claims.

## M1 — One real public data adapter

Target Inspect logs first if their schema and public examples support the required fields. Read current upstream documentation and licenses before selecting a fixture.

Acceptance: parse a small legally shareable log, preserve scorer/harness/dataset provenance, explain unavailable cost fields rather than inventing them, and reject malformed input with actionable errors. Validate conversion against source totals. Keep fixtures free of personal data and secrets.

## M2 — Repeated attempts and execution conditions

Represent run IDs and repeated attempts without pretending they are independent tasks. Add task-level resampling, failure categories and declared execution budgets. A simulation should demonstrate why naive per-attempt resampling can overstate certainty.

Acceptance: known simulated cases exercise the expected coverage/failure mode; no fabricated model experiment. Explain which uncertainty is and is not estimated.

## M3 — Scorer sensitivity study

Keep trajectories fixed while evaluating at least two grading regimes on a public or independently authored task set. Preserve both regimes rather than mixing them into one leaderboard. Quantify changed decisions and inspect disagreements.

Acceptance: reproducible rescoring commands, licensed inputs, raw data, error analysis and a technical report. A negative or inconclusive result is a valid outcome.

## M4 — Budgeted decisions on held-out tasks

Choose a policy on validation tasks, freeze it, then compare with fixed-agent baselines on held-out tasks. Use declared quality tolerances and costs that include failures and retries. Publish uncertainty and situations where no recommendation is supported.

## M5 — Upstream contribution

Use a reproducible issue discovered in M1–M3 to prepare a focused contribution to the relevant framework. Check current issue/PR status to avoid duplicating an existing fix. Do not assume maintainers will accept it or commit to an unsupported compatibility promise.

## Daily workflow

1. Read the current state and select one bounded item.
2. Reproduce or specify the problem before changing code.
3. Implement and run relevant checks.
4. Obtain a separate review for statistical or execution changes.
5. Publish verified changes to the owner's repository; log the evidence and next step.

Review new research weekly. A trend must change the problem, method or validation plan to justify a new feature. Do not create empty commits, placeholder features or unsupported results to satisfy a daily cadence.
