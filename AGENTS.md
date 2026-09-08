# Working on Eval Decision Audit

This is an independent evaluation-analysis project owned by iserranoEJ. Read README.md and docs/methodology.md before changing statistical behaviour. Track progress in docs/progress.md and preserve the distinction between implemented capabilities and planned work.

## Authorised workflow

The owner authorises agents to publish verified changes to this repository. Work on one bounded milestone per run. Use one implementation agent and one independent reviewer when changes affect statistics, schema, data conversion or execution. Research can run as a separate bounded subtask weekly. Do not spawn agents merely to parallelise trivial edits.

Before editing, inspect git status and remotes. Preserve user changes. Synchronise safely; never force-push, reset away work or rewrite published history. Push only to the confirmed owner repository. Contributions to other projects may be prepared locally; do not send unsolicited comments or requests to maintainers.

## Evidence standard

- No employer data, confidential metrics, private Composite contents or credentials.
- No paid model runs without an explicit experiment budget. Current budget for API/model execution is zero; use fixtures and existing public data with appropriate rights.
- Keep synthetic fixtures clearly marked. Never present constructed values as measurements or invent citations, tests, adoption or benchmark results.
- Failed attempts and missing costs must remain visible. Reject incompatible cohorts rather than silently dropping observations.
- Changes to statistical methods require meaningful counterexamples and independent review. Do not treat a marginal interval or observed Pareto frontier as a guarantee.

## Validation

Python 3.11+. Runtime dependencies are intentionally empty for M0. Run `python -m unittest discover -s tests -v`, install the package into an isolated environment, and run the documented CLI on the synthetic fixture for relevant changes. Do not commit virtual environments, caches, generated reports or downloaded private logs.

Only commit coherent, checked changes. If the daily run produces no useful change, record an actionable finding locally or remain quiet; do not manufacture activity. Report significant completed work, failures needing the owner or an explicit decision. Do not repeat unchanged status updates.
