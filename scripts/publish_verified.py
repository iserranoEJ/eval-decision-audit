"""Fail-closed coordination gate; attested agent IDs are NOT authenticated.

Writers sharing credentials can forge attestations or statuses. This script
reduces publishing mistakes; it does not establish an identity/security boundary.
It never changes repository protections. Dry-run is the default.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPOSITORY = "iserranoEJ/eval-decision-audit"
CI_APP_ID = 15368
CI_CONTEXTS = {"test (3.11)", "test (3.12)", "test (3.13)"}
REQUIRED_CONTEXTS = CI_CONTEXTS | {"agent-review"}
PLACEHOLDERS = {"todo", "tbd", "placeholder", "unknown", "example", "replace-me", "changeme"}


class GateError(ValueError):
    """Evidence or live repository state does not permit publication."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateError(message)


def meaningful(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and value.strip().lower() not in PLACEHOLDERS
        and re.search(r"<[^<>]*>", value) is None
    )


def sha(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) is not None and len(set(value)) > 1


def validate_attestation(attestation: Any, pr: int) -> dict[str, Any]:
    require(isinstance(attestation, dict), "attestation must be an object")
    require(type(attestation.get("schema_version")) is int and attestation["schema_version"] == 1, "schema_version must be integer 1")
    require(attestation.get("repository") == REPOSITORY, "attestation repository mismatch")
    require(type(pr) is int and pr > 0, "PR must be a positive integer")
    require(type(attestation.get("pull_request")) is int and attestation["pull_request"] == pr, "attestation PR mismatch")
    require(sha(attestation.get("head_sha")) and sha(attestation.get("base_sha")), "head_sha and base_sha must be real 40-character lowercase hex values")
    implementer = attestation.get("implementer_id")
    require(meaningful(implementer), "implementer_id must identify the implementing agent")
    reviews = attestation.get("reviews")
    require(isinstance(reviews, list) and len(reviews) == 2, "exactly two reviews are required")
    roles, identities = set(), {implementer.strip()}
    for review in reviews:
        require(isinstance(review, dict), "each review must be an object")
        role = review.get("role")
        require(role in ("tester", "reviewer") and role not in roles, "exactly one tester and one reviewer are required")
        roles.add(role)
        identity = review.get("agent_id")
        require(meaningful(identity), "review agent_id must be nonempty and not a placeholder")
        identity = identity.strip()
        require(identity not in identities, "implementer, tester and reviewer must have distinct agent IDs")
        identities.add(identity)
        require(review.get("head_sha") == attestation["head_sha"] and review.get("base_sha") == attestation["base_sha"], "review SHAs do not match attestation")
        require(review.get("verdict") == "pass", "both review verdicts must be pass")
        require(review.get("findings") == [], "all review findings must be resolved")
        evidence = review.get("evidence")
        require(isinstance(evidence, list) and bool(evidence) and all(meaningful(item) for item in evidence), "review evidence must contain nonempty, non-placeholder strings")
    return attestation


class GitHub:
    def call(self, args: list[str], payload: dict[str, Any] | None = None) -> Any:
        command = ["gh", *args]
        if payload is not None:
            command.extend(["--input", "-"])
        result = subprocess.run(
            command,
            input=json.dumps(payload) if payload is not None else None,
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, "GH_PROMPT_DISABLED": "1"},
            timeout=60,
        )
        require(result.returncode == 0, f"gh command failed: {result.stderr.strip() or result.stdout.strip()}")
        if not result.stdout.strip():
            return None
        # Only API requests return JSON; the merge CLI returns prose.
        return json.loads(result.stdout) if args[0] == "api" else result.stdout

    def get(self, suffix: str) -> Any:
        return self.call(["api", f"repos/{REPOSITORY}/{suffix}"])

    def post(self, suffix: str, payload: dict[str, Any]) -> Any:
        return self.call(["api", "--method", "POST", f"repos/{REPOSITORY}/{suffix}"], payload)


def validate_live(github: GitHub, attestation: dict[str, Any]) -> None:
    pr = github.get(f"pulls/{attestation['pull_request']}")
    require(pr.get("state") == "open" and pr.get("draft") is False, "PR must be open and non-draft")
    head, base = pr.get("head", {}), pr.get("base", {})
    require(head.get("repo", {}).get("full_name") == REPOSITORY and base.get("repo", {}).get("full_name") == REPOSITORY, "PR must originate in and target the configured repository")
    require(base.get("ref") == "main", "PR must target main")
    require(head.get("sha") == attestation["head_sha"], "stale head SHA")
    require(base.get("sha") == attestation["base_sha"], "stale PR base SHA")
    main = github.get("git/ref/heads/main")
    require(main.get("object", {}).get("sha") == attestation["base_sha"], "main has advanced beyond the reviewed base SHA")

    protection = github.get("branches/main/protection")
    require(protection.get("enforce_admins", {}).get("enabled") is True, "branch protection must be enforced for admins")
    review_protection = protection.get("required_pull_request_reviews")
    require(isinstance(review_protection, dict), "pull request review protection must be enabled")
    approval_count = review_protection.get("required_approving_review_count")
    require(type(approval_count) is int and 0 <= approval_count <= 6, "required approving review count must be an integer from 0 to 6")
    for flag in ("dismiss_stale_reviews", "require_code_owner_reviews", "require_last_push_approval"):
        require(type(review_protection.get(flag)) is bool, f"review protection {flag} must be boolean")
    require(protection.get("allow_force_pushes", {}).get("enabled") is False, "force pushes must be disabled")
    require(protection.get("allow_deletions", {}).get("enabled") is False, "branch deletion must be disabled")
    required = protection.get("required_status_checks", {})
    require(required.get("strict") is True, "strict status checks must be enabled")
    checks = required.get("checks", [])
    require(isinstance(checks, list) and all(isinstance(check, dict) for check in checks), "required check bindings are missing")
    configured = {check.get("context") for check in checks}
    require(REQUIRED_CONTEXTS <= configured, "required CI or agent-review context is missing")
    for context in CI_CONTEXTS:
        matching = [check for check in checks if check.get("context") == context]
        require(len(matching) == 1 and matching[0].get("app_id") == CI_APP_ID, f"{context} must be bound to GitHub Actions app {CI_APP_ID}")

    result = github.get(f"commits/{attestation['head_sha']}/check-runs?per_page=100&filter=latest")
    runs = result.get("check_runs")
    require(isinstance(runs, list) and type(result.get("total_count")) is int and result["total_count"] == len(runs), "check run result is truncated or malformed")
    for context in CI_CONTEXTS:
        matching = [run for run in runs if isinstance(run, dict) and run.get("name") == context]
        require(bool(matching), f"missing CI check: {context}")
        for run in matching:
            require(run.get("head_sha") == attestation["head_sha"], f"{context} was run against a different SHA")
            require(run.get("app", {}).get("id") == CI_APP_ID, f"{context} comes from the wrong app")
            require(run.get("status") == "completed" and run.get("conclusion") == "success", f"{context} must complete successfully (skipped is not success)")


def publish_verified(attestation: Any, pr: int, *, publish: bool = False, github: GitHub | None = None) -> dict[str, Any]:
    data = validate_attestation(attestation, pr)
    client = github if github is not None else GitHub()
    validate_live(client, data)
    if not publish:
        return {"mode": "dry-run", "repository": REPOSITORY, "pull_request": pr, "head_sha": data["head_sha"], "ready": True}
    # Re-query immediately before publishing evidence, then again before merge.
    validate_live(client, data)
    serialised = json.dumps(data, indent=2, ensure_ascii=True)
    # JSON may contain Markdown fences; indented code preserves evidence as data.
    body = "Automated review coordination record\n\nAgent IDs are attested, not authenticated. This gate prevents mistakes; shared credentials can forge this record.\n\n" + "\n".join("    " + line for line in serialised.splitlines())
    comment = client.post(f"issues/{pr}/comments", {"body": body})
    target_url = comment.get("html_url") if isinstance(comment, dict) else None
    require(isinstance(target_url, str) and re.fullmatch(rf"https://github\.com/{re.escape(REPOSITORY)}/(?:pull|issues)/{pr}#issuecomment-[0-9]+", target_url) is not None, "GitHub did not return a verifiable PR comment URL")
    client.post(f"statuses/{data['head_sha']}", {
        "state": "success",
        "context": "agent-review",
        "description": "Distinct implementer/tester/reviewer attested; evidence linked",
        "target_url": target_url,
    })
    try:
        validate_live(client, data)
        client.call(["pr", "merge", str(pr), "--squash", "--match-head-commit", data["head_sha"], "--repo", REPOSITORY])
        merged_pr = client.get(f"pulls/{pr}")
        require(merged_pr.get("merged") is True and sha(merged_pr.get("merge_commit_sha")), "GitHub has not confirmed a completed merge with a valid commit SHA")
    except Exception as original_error:
        # The stamp must not survive a failed final check or merge attempt.
        # Revoke once, never retry the merge or bypass protection.
        try:
            client.post(f"statuses/{data['head_sha']}", {
                "state": "failure",
                "context": "agent-review",
                "description": "Publication failed after review stamp; fresh verification required",
                "target_url": target_url,
            })
        except Exception as revocation_error:
            raise GateError(
                f"Publication failed: {original_error}. "
                f"Revoking agent-review also failed: {revocation_error}. "
                "The previous success status may remain; manual intervention is required."
            ) from original_error
        raise
    return {"mode": "published", "repository": REPOSITORY, "pull_request": pr, "head_sha": data["head_sha"], "merge_commit_sha": merged_pr["merge_commit_sha"], "review_record": target_url}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--attestation", required=True, type=Path)
    parser.add_argument("--publish", action="store_true", help="Write evidence/status and merge; default is read-only")
    args = parser.parse_args(argv)
    try:
        attestation = json.loads(args.attestation.read_text(encoding="utf-8"))
        result = publish_verified(attestation, args.pr, publish=args.publish)
        print(json.dumps(result, indent=2))
        return 0
    except (GateError, OSError, ValueError, TypeError, AttributeError, subprocess.SubprocessError) as exc:
        print(f"publish_verified: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
