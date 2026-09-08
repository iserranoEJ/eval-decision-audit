# Progress

## 2026-09-08 — Reviewed publication workflow

Added coordinator, implementer, tester and reviewer responsibilities, a PR template and a fail-closed publication script. Reviews identify the full candidate and base SHAs; the script rejects stale evidence, missing/unsuccessful CI and weakened required protection settings. It publishes the actual receipts on the PR and merges only the matching candidate. Dry-run performs read-only checks.

Configured main protection to require PRs, strict Python 3.11–3.13 CI from GitHub Actions and the coordinator's agent-review status, including for administrators. Force pushes and branch deletion are disabled. The receipts attest separate agent tasks; shared GitHub credentials do not provide authenticated reviewer independence.

Review and adversarial testing found residual approval after an aborted merge, accepted template placeholders, insufficient review-protection validation and missing post-merge confirmation. These were corrected with regression tests. Aborted publication now attempts to revoke approval; an unconfirmed merge is never reported as published.

Local validation: 41 unit tests passed (20 analysis tests and 21 publication-gate tests); the installed synthetic CLI completed with 2,000 resamples and seed 42. Final candidate review and remote CI evidence will be recorded on the pull request after the commit is frozen. No empirical model study or paid API call was performed.

Next: use this workflow for one bounded public-data milestone. Select licensed fixed responses suitable for a scorer-sensitivity question, check that the necessary provenance is available, and build only the conversion needed for that experiment. Predefine grading regimes before examining the ranking.

## 2026-09-08 — Initial implementation

Completed the M0 analysis contract: strict provenance checks, complete paired cohorts, retained failed-attempt costs, deterministic paired bootstrap and a descriptive observed frontier. Added a synthetic ten-case, three-agent fixture and 20 tests.

Independent review identified overflow for very large finite costs. Mean and percentile calculations were revised to use scaling, with a regression test. The installed command was run from a fresh virtual environment and produced valid JSON. No model inference or empirical benchmark was run.

Validation: `python -m unittest discover -s tests -v` passed 20 tests; the documented `eval-decision-audit` command ran successfully with 2,000 bootstrap resamples and seed 42. CI is configured for Python 3.11–3.13; remote outcomes are tracked in GitHub Actions.

Next: select one public Inspect log, verify its license and schema, and write a conversion specification that preserves missing-cost information and provenance. Do not invent cost values to fit the current schema. Any schema extension must explain compatibility with v1.
