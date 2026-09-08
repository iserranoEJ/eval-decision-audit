# Agent development and publication

The maintainer authorises automatic publication of verified work to this repository. A daily Codex task coordinates the work; GitHub Actions runs deterministic checks. This repository does not launch paid model calls or an always-running agent service.

## Roles

| Role | Responsibility | Output |
| --- | --- | --- |
| Coordinator | Select acceptance criteria, allocate files, integrate and publish | Bounded plan, candidate commit and PR |
| Implementer | Implement the agreed change | Code and rationale; no self-approval |
| Tester | Design counterexamples independently and test the frozen candidate | SHAs, commands, observed results and limits |
| Reviewer | Inspect the complete diff and assumptions without editing | SHAs, evidence and findings or pass |

Use at most four concurrent agents. Testing can develop alongside implementation; final review waits for the candidate. Give reviewers acceptance criteria and code to inspect rather than asking them to agree with the author. Return defects to the implementer, then test/review the new commit. For trivial documentation, receipts can be short and no artificial tests are needed.

## Daily cycle

1. Check local changes, origin/main, open PRs and CI. Resume existing work before creating another PR. Only the coordinator performs Git mutations.
2. Copy the publication script from current origin/main to an external work directory before editing. Run that trusted copy later; a PR must not approve itself using its modified gate. The initial installation receives separate testing and review.
3. Select one hypothesis or acceptance criterion and freeze its measurement plan. Assign implementation and counterexample testing separately. Use distinct file ownership or worktrees.
4. Run relevant checks, update the progress log with observed evidence, and commit code, tests and docs on a topic branch. Push and create a PR against main. This is a reviewable candidate, not a verified release.
5. Record full candidate head and current main/base SHAs. Tester and reviewer inspect that frozen state and return receipts. Do not commit receipts into the candidate. Fixes or base updates invalidate them.
6. Once CI succeeds, assemble the actual receipts in the format below. Dry-run the gate, then run with `--publish`. Routine passing changes need no additional owner permission.
7. Confirm the PR merged and the resulting main CI outcome. Squash creates a new commit; retain the candidate SHA in PR evidence rather than claiming it equals the merge SHA. On failure, leave the PR open and report the actionable cause. Never use `--admin` or disable checks.

Allow at most two repair cycles per daily run. Do not create empty commits or features solely to generate activity. Weekly research must inform the current experiment or a concrete upstream contribution.

## Publication gate

Main requires a PR with zero GitHub human approvals (agents share an account), strict checks `test (3.11)`, `test (3.12)`, `test (3.13)` from GitHub Actions (app ID 15368), and coordinator commit status `agent-review`. Rules apply to administrators; force pushes and branch deletion are disabled.

`scripts/publish_verified.py` uses Python's standard library and authenticated `gh`. It validates receipts, open non-draft PR, repository, exact head/base SHAs, protection settings and completed successful CI. It posts receipts on the PR, links an `agent-review` status to that evidence, rechecks the candidate and merges with `--match-head-commit`. It confirms the merged state and records the resulting merge SHA. Missing, skipped, neutral, failed or stale evidence is rejected. If publication aborts after approval, it attempts to revoke the status and reports any failure to do so. Dry-run makes no remote writes; its `ready` result means the gate's prerequisites passed, not that GitHub has confirmed mergeability. GitHub also checks the PR's merge-result CI and branch rules at merge time.

```bash
python /path/to/trusted/publish_verified.py --pr 12 --attestation /path/to/reviews.json
python /path/to/trusted/publish_verified.py --pr 12 --attestation /path/to/reviews.json --publish
```

The number and paths are illustrative. Use real evidence; authentication/API errors halt publication. Check public receipts for private data before submitting.

## Receipt format

This template is not an approval or test result. Replace every placeholder with actual evidence. `findings` means unresolved findings and must be empty for a pass. Include repaired findings and remaining limitations in evidence.

```json
{
  "schema_version": 1,
  "repository": "iserranoEJ/eval-decision-audit",
  "pull_request": 12,
  "head_sha": "<full 40-character candidate SHA>",
  "base_sha": "<full 40-character current main SHA>",
  "implementer_id": "<actual implementation task ID>",
  "reviews": [
    {
      "role": "tester",
      "agent_id": "<actual separate tester task ID>",
      "head_sha": "<same candidate SHA>",
      "base_sha": "<same main SHA>",
      "verdict": "pass",
      "evidence": ["<commands actually run, versions, results and limits>"],
      "findings": []
    },
    {
      "role": "reviewer",
      "agent_id": "<actual separate reviewer task ID>",
      "head_sha": "<same candidate SHA>",
      "base_sha": "<same main SHA>",
      "verdict": "pass",
      "evidence": ["<files and assumptions inspected, checks and limits>"],
      "findings": []
    }
  ]
}
```

## Trust and limitations

Branch protection blocks ordinary merges when required checks are missing. Statuses belong to a SHA; the publisher also checks the current base, and strict protection requires an up-to-date branch. The publisher accepts only literal CI `success`, stricter than GitHub's generic acceptance of skipped/neutral checks.

The receipt is an attestation by the coordinator, not cryptographic proof of reviewer identity. Writers with shared credentials can forge `agent-review`; an administrator can modify protection. Even the GitHub Actions app identity does not uniquely authenticate a workflow. Agents can share model biases and passing tests do not prove correctness. Stronger authority separation would require credentials unavailable to the implementer; this setup does not claim it.

CI executes candidate code with read-only permissions and no added secrets. The publisher runs locally with the coordinator's existing authentication. Never introduce a privileged workflow executing unreviewed PR code. Gate/workflow/instruction changes need explicit review of enforcement logic and the prior trusted publisher; do not automatically weaken settings.

References: [branch protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches), [commit statuses](https://docs.github.com/en/rest/commits/statuses), [merge SHA matching](https://cli.github.com/manual/gh_pr_merge), [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents).
