import copy
import importlib.util
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location("publish_verified", Path(__file__).resolve().parents[1] / "scripts" / "publish_verified.py")
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)
HEAD = "0123456789abcdef" * 2 + "01234567"
BASE = "abcdef0123456789" * 2 + "abcdef01"
OTHER = "9876543210abcdef" * 2 + "98765432"


def attestation():
    return {
        "schema_version": 1,
        "repository": gate.REPOSITORY,
        "pull_request": 7,
        "head_sha": HEAD,
        "base_sha": BASE,
        "implementer_id": "/root/implementation-21",
        "reviews": [
            {"role": "tester", "agent_id": "/root/tests-22", "head_sha": HEAD, "base_sha": BASE, "verdict": "pass", "evidence": ["python -m unittest discover -s tests -v: 20 tests passed"], "findings": []},
            {"role": "reviewer", "agent_id": "/root/review-23", "head_sha": HEAD, "base_sha": BASE, "verdict": "pass", "evidence": ["Reviewed full diff against base; no blocking findings"], "findings": []},
        ],
    }


class FakeGitHub:
    def __init__(self):
        self.reads = []
        self.writes = []
        self.merges = []
        self.pr_reads = 0
        self.advance_on_read = None
        self.merge_error = None
        self.revocation_error = None
        self.merge_confirmation = {"merged": True, "merge_commit_sha": OTHER}
        self.comment_url = f"https://github.com/{gate.REPOSITORY}/pull/7#issuecomment-123"
        self.values = {
            "pulls/7": {"state": "open", "draft": False, "head": {"sha": HEAD, "repo": {"full_name": gate.REPOSITORY}}, "base": {"sha": BASE, "ref": "main", "repo": {"full_name": gate.REPOSITORY}}},
            "git/ref/heads/main": {"object": {"sha": BASE}},
            "branches/main/protection": {
                "enforce_admins": {"enabled": True},
                "required_pull_request_reviews": {"required_approving_review_count": 0, "dismiss_stale_reviews": True, "require_code_owner_reviews": False, "require_last_push_approval": False},
                "allow_force_pushes": {"enabled": False},
                "allow_deletions": {"enabled": False},
                "required_status_checks": {"strict": True, "checks": [{"context": name, "app_id": gate.CI_APP_ID} for name in sorted(gate.CI_CONTEXTS)] + [{"context": "agent-review", "app_id": None}]},
            },
            f"commits/{HEAD}/check-runs?per_page=100&filter=latest": {"total_count": 3, "check_runs": [{"name": name, "head_sha": HEAD, "app": {"id": gate.CI_APP_ID}, "status": "completed", "conclusion": "success"} for name in sorted(gate.CI_CONTEXTS)]},
        }

    def get(self, suffix):
        self.reads.append(suffix)
        if suffix == "pulls/7":
            self.pr_reads += 1
            if self.pr_reads == self.advance_on_read:
                self.values[suffix]["head"]["sha"] = OTHER
        return copy.deepcopy(self.values[suffix])

    def post(self, suffix, payload):
        self.writes.append((suffix, copy.deepcopy(payload)))
        if payload.get("state") == "failure" and self.revocation_error:
            raise self.revocation_error
        return {"html_url": self.comment_url} if suffix.endswith("/comments") else {"state": "success"}

    def call(self, args):
        self.merges.append(args)
        if self.merge_error:
            raise self.merge_error
        self.values["pulls/7"].update(self.merge_confirmation)

    @property
    def runs(self):
        return self.values[f"commits/{HEAD}/check-runs?per_page=100&filter=latest"]

    @property
    def protection(self):
        return self.values["branches/main/protection"]


class PublishGateTests(unittest.TestCase):
    def reject(self, evidence=None, client=None):
        client = client or FakeGitHub()
        with self.assertRaises(gate.GateError):
            gate.publish_verified(evidence or attestation(), 7, publish=True, github=client)
        self.assertEqual(client.writes, [])
        self.assertEqual(client.merges, [])

    def test_dry_run_is_read_only(self):
        client = FakeGitHub()
        result = gate.publish_verified(attestation(), 7, github=client)
        self.assertEqual(result["mode"], "dry-run")
        self.assertEqual(client.writes, [])
        self.assertEqual(client.merges, [])
        self.assertEqual(len(client.reads), 4)

    def test_stale_head_and_base_rejected(self):
        for side in ("head", "base"):
            with self.subTest(side=side):
                client = FakeGitHub()
                client.values["pulls/7"][side]["sha"] = OTHER
                self.reject(client=client)
        client = FakeGitHub()
        client.values["git/ref/heads/main"]["object"]["sha"] = OTHER
        self.reject(client=client)

    def test_stale_review_rejected(self):
        for key in ("head_sha", "base_sha"):
            data = attestation()
            data["reviews"][0][key] = OTHER
            self.reject(evidence=data)

    def test_self_review_and_duplicate_reviewer_rejected(self):
        for identity in ("/root/implementation-21", "/root/tests-22", " /root/tests-22 "):
            data = attestation()
            data["reviews"][1]["agent_id"] = identity
            self.reject(evidence=data)

    def test_blockers_failed_verdict_missing_evidence_and_roles_rejected(self):
        for key, value in (("findings", ["Unresolved data leak"]), ("verdict", "fail"), ("evidence", []), ("evidence", [" "]), ("role", "tester")):
            with self.subTest(key=key):
                data = attestation()
                data["reviews"][1][key] = value
                self.reject(evidence=data)

    def test_placeholders_and_invalid_sha_rejected(self):
        for key, value in (("head_sha", "0" * 40), ("head_sha", "not-a-sha"), ("implementer_id", "TODO"), ("schema_version", True), ("pull_request", True)):
            data = attestation()
            data[key] = value
            self.reject(evidence=data)

    def test_partially_filled_template_is_rejected(self):
        data = attestation()
        data["implementer_id"] = "<actual implementing agent ID>"
        self.reject(evidence=data)
        data = attestation()
        data["reviews"][0]["agent_id"] = "<actual tester agent ID>"
        self.reject(evidence=data)
        data = attestation()
        data["reviews"][1]["evidence"] = ["Reviewed <actual diff and findings>"]
        self.reject(evidence=data)

    def test_closed_draft_fork_and_wrong_target_rejected(self):
        for mutation in (
            lambda pr: pr.update(state="closed"),
            lambda pr: pr.update(draft=True),
            lambda pr: pr["head"]["repo"].update(full_name="other/repo"),
            lambda pr: pr["base"].update(ref="develop"),
        ):
            client = FakeGitHub()
            mutation(client.values["pulls/7"])
            self.reject(client=client)

    def test_skipped_failed_incomplete_wrong_app_or_wrong_sha_rejected(self):
        for key, value in (("conclusion", "skipped"), ("conclusion", "failure"), ("status", "in_progress"), ("app", {"id": 999}), ("head_sha", OTHER)):
            with self.subTest(key=key, value=value):
                client = FakeGitHub()
                client.runs["check_runs"][0][key] = value
                self.reject(client=client)

    def test_missing_or_truncated_checks_rejected(self):
        client = FakeGitHub()
        client.runs["check_runs"].pop()
        client.runs["total_count"] = 2
        self.reject(client=client)
        client = FakeGitHub()
        client.runs["total_count"] = 101
        self.reject(client=client)

    def test_disabled_protections_rejected(self):
        for key, value in (("enforce_admins", {"enabled": False}), ("allow_force_pushes", {"enabled": True}), ("allow_deletions", {"enabled": True}), ("required_pull_request_reviews", None)):
            client = FakeGitHub()
            client.protection[key] = value
            self.reject(client=client)
        client = FakeGitHub()
        client.protection["required_status_checks"]["strict"] = False
        self.reject(client=client)
        for missing in gate.REQUIRED_CONTEXTS:
            client = FakeGitHub()
            client.protection["required_status_checks"]["checks"] = [check for check in client.protection["required_status_checks"]["checks"] if check["context"] != missing]
            self.reject(client=client)
        client = FakeGitHub()
        client.protection["required_status_checks"]["checks"][0]["app_id"] = None
        self.reject(client=client)

    def test_malformed_review_protection_rejected(self):
        client = FakeGitHub()
        client.protection["required_pull_request_reviews"] = {}
        self.reject(client=client)
        for invalid in ("invalid", True, -1, 7, None):
            client = FakeGitHub()
            client.protection["required_pull_request_reviews"]["required_approving_review_count"] = invalid
            self.reject(client=client)
        for flag in ("dismiss_stale_reviews", "require_code_owner_reviews", "require_last_push_approval"):
            for invalid in (0, "false", None):
                client = FakeGitHub()
                client.protection["required_pull_request_reviews"][flag] = invalid
                self.reject(client=client)

    def test_revalidation_before_writes_catches_race(self):
        client = FakeGitHub()
        client.advance_on_read = 2
        self.reject(client=client)

    def test_revalidation_before_merge_catches_race(self):
        client = FakeGitHub()
        client.advance_on_read = 3
        with self.assertRaises(gate.GateError):
            gate.publish_verified(attestation(), 7, publish=True, github=client)
        self.assertEqual(len(client.writes), 3)
        self.assertEqual(client.writes[-1][0], f"statuses/{HEAD}")
        self.assertEqual(client.writes[-1][1]["state"], "failure")
        self.assertEqual(client.writes[-1][1]["context"], "agent-review")
        self.assertEqual(client.merges, [])

    def test_failed_merge_revokes_status_without_retry(self):
        client = FakeGitHub()
        client.merge_error = gate.GateError("merge refused by branch protection")
        with self.assertRaisesRegex(gate.GateError, "merge refused by branch protection"):
            gate.publish_verified(attestation(), 7, publish=True, github=client)
        self.assertEqual(len(client.merges), 1)
        self.assertEqual(len(client.writes), 3)
        self.assertEqual(client.writes[-1][0], f"statuses/{HEAD}")
        self.assertEqual(client.writes[-1][1]["state"], "failure")

    def test_unconfirmed_merge_never_reports_published(self):
        for confirmation in ({}, {"merged": False, "merge_commit_sha": OTHER}, {"merged": True, "merge_commit_sha": None}, {"merged": True, "merge_commit_sha": "0" * 40}):
            client = FakeGitHub()
            client.merge_confirmation = confirmation
            with self.assertRaisesRegex(gate.GateError, "not confirmed a completed merge"):
                gate.publish_verified(attestation(), 7, publish=True, github=client)
            self.assertEqual(len(client.merges), 1)
            self.assertEqual(client.writes[-1][1]["state"], "failure")

    def test_revocation_failure_reports_both_causes(self):
        for fail_final_check in (False, True):
            with self.subTest(fail_final_check=fail_final_check):
                client = FakeGitHub()
                client.revocation_error = gate.GateError("status API unavailable")
                if fail_final_check:
                    client.advance_on_read = 3
                    expected_cause = "stale head SHA"
                else:
                    client.merge_error = gate.GateError("merge refused")
                    expected_cause = "merge refused"
                with self.assertRaises(gate.GateError) as raised:
                    gate.publish_verified(attestation(), 7, publish=True, github=client)
                message = str(raised.exception)
                self.assertIn(expected_cause, message)
                self.assertIn("status API unavailable", message)
                self.assertIn("previous success status may remain", message)
                self.assertEqual(len(client.merges), 0 if fail_final_check else 1)
                self.assertEqual(len(client.writes), 3)

    def test_publish_records_evidence_and_merges_exact_sha(self):
        client = FakeGitHub()
        evidence = attestation()
        evidence["reviews"][0]["evidence"].append("Literal Markdown ``` and $(do-not-execute) remain evidence")
        result = gate.publish_verified(evidence, 7, publish=True, github=client)
        self.assertEqual(result["mode"], "published")
        self.assertEqual(client.pr_reads, 4)
        self.assertEqual(result["merge_commit_sha"], OTHER)
        suffix, comment = client.writes[0]
        self.assertEqual(suffix, "issues/7/comments")
        code = comment["body"].split("\n\n", 2)[2]
        self.assertEqual(json.loads("\n".join(line[4:] for line in code.splitlines())), evidence)
        suffix, status = client.writes[1]
        self.assertEqual(suffix, f"statuses/{HEAD}")
        self.assertEqual(status["state"], "success")
        self.assertEqual(status["context"], "agent-review")
        self.assertEqual(status["target_url"], client.comment_url)
        self.assertEqual(client.merges, [["pr", "merge", "7", "--squash", "--match-head-commit", HEAD, "--repo", gate.REPOSITORY]])

    def test_unverified_comment_url_blocks_status_and_merge(self):
        client = FakeGitHub()
        client.comment_url = "https://example.com/unverified"
        with self.assertRaises(gate.GateError):
            gate.publish_verified(attestation(), 7, publish=True, github=client)
        self.assertEqual(len(client.writes), 1)
        self.assertEqual(client.merges, [])

    def test_subprocess_uses_argument_list_and_json_stdin(self):
        result = subprocess.CompletedProcess([], 0, '{"ok": true}', "")
        with patch.object(gate.subprocess, "run", return_value=result) as execute:
            response = gate.GitHub().post("issues/7/comments", {"body": "literal ` $() text"})
        self.assertTrue(response["ok"])
        args, kwargs = execute.call_args
        self.assertIsInstance(args[0], list)
        self.assertEqual(args[0][-2:], ["--input", "-"])
        self.assertNotIn("shell", kwargs)
        self.assertEqual(kwargs["env"]["GH_PROMPT_DISABLED"], "1")
        self.assertEqual(json.loads(kwargs["input"]), {"body": "literal ` $() text"})

    def test_gh_failure_raises_and_never_continues(self):
        result = subprocess.CompletedProcess([], 1, "", "permission denied")
        with patch.object(gate.subprocess, "run", return_value=result):
            with self.assertRaisesRegex(gate.GateError, "permission denied"):
                gate.GitHub().get("pulls/7")


if __name__ == "__main__":
    unittest.main()
