# Working on Eval Decision Audit

This is an independent evaluation-analysis project owned by iserranoEJ. Read README.md, docs/methodology.md, docs/progress.md and docs/agent-workflow.md before working. Preserve the distinction between implemented capabilities and planned experiments.

## Authorised workflow

The owner authorises publication of verified changes through pull requests. Never push directly to main, bypass branch protection, force-push, rewrite published history or change repository protections to make a run succeed. Contributions to other projects may be prepared locally; do not send unsolicited messages or requests to maintainers.

The coordinator selects one bounded acceptance criterion and assigns separate implementer, tester and reviewer agents. At most four agents run concurrently, including the coordinator. The tester can develop counterexamples while implementation proceeds. The reviewer examines the completed candidate without editing it. Use separate task contexts and actual agent IDs; never impersonate a reviewer or invent approval. Even small changes need the two short receipts required by the gate; scale the work to the change.

Before editing, inspect git status, remotes, open PRs and CI. Preserve user changes and resume relevant unfinished work. Copy scripts/publish_verified.py from current origin/main into an external work directory before editing; use that trusted copy for publication. Keep one work item and one publication attempt active at a time. Agents must not switch the shared checkout or edit the same files concurrently. Use separate worktrees if needed.

Freeze the candidate commit before final testing/review. Receipts name its full head SHA and current main/base SHA. Every edit requires new receipts for the new commit. Evidence belongs in a PR comment, not a new commit that invalidates its own SHA. Publish through the gate after actual reviews and CI success. If checks fail, fix and review again; after two repair cycles leave the PR open with a concrete next step. Never weaken checks to meet a schedule.

## Evidence standard

- No employer data, confidential metrics, private Composite contents or credentials.
- No paid model runs without an explicit experiment budget. Current API/model execution budget is zero; use labelled fixtures and existing public data with appropriate rights.
- No fabricated measurements, citations, tests, adoption, reviews or benchmark results.
- Failed attempts and missing costs remain visible. Reject incompatible cohorts instead of silently dropping observations.
- Statistical changes require meaningful counterexamples. A marginal interval or observed Pareto frontier is not a guarantee.
- Before an experiment, freeze hypothesis, inputs, metric, split, seed and acceptance criteria. Do not optimize the evaluator after seeing outcomes. Null and inconclusive results are valid.

## Validation and progress

Python 3.11+. Run `python -m unittest discover -s tests -v`, install in an isolated environment for packaging changes, and run the documented CLI for relevant changes. Do not commit virtual environments, caches, generated reports or private logs. Review test removals, dataset/scorer changes and workflow edits explicitly.

Update docs/progress.md before freezing the candidate: problem, change, observed validation, limitations and next step. Do not claim remote checks passed before they have run; final evidence goes on the PR. Stop without manufacturing a commit when there is no useful change. Weekly research must inform a concrete experiment or resolve an upstream issue, not continually replace the project. Report meaningful completions, actionable failures or decisions only.

## Trust limit

Separate agent tasks provide cross-checking, not separate GitHub identities or independent human review. The coordinator posts `agent-review` using the owner's credentials. Writers can forge a status, and an administrator can change protection settings. The workflow prevents normal publication with missing/stale evidence; it is not an access-control boundary against those credentials.
