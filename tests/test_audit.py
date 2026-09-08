import copy
import json
import math
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from eval_decision_audit import AuditValidationError, audit


ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return json.loads((ROOT / "examples" / "synthetic.json").read_text(encoding="utf-8"))


def evaluate(data):
    return audit(data, "baseline", bootstrap_samples=200, seed=42)


class AuditTests(unittest.TestCase):
    def test_rejects_each_mixed_revision(self):
        for key in ("dataset_revision", "scorer_revision", "harness_revision"):
            with self.subTest(key=key):
                data = fixture()
                data["observations"][0][key] = "different-revision"
                with self.assertRaisesRegex(AuditValidationError, "does not match provenance"):
                    evaluate(data)

    def test_rejects_empty_provenance(self):
        data = fixture()
        data["provenance"]["dataset_revision"] = " "
        with self.assertRaisesRegex(AuditValidationError, "nonempty"):
            evaluate(data)

    def test_rejects_incomplete_grid(self):
        data = fixture()
        data["observations"].pop()
        with self.assertRaisesRegex(AuditValidationError, "case set"):
            evaluate(data)

    def test_rejects_different_case_set_even_with_same_length(self):
        data = fixture()
        data["observations"][0]["case_id"] = "unpaired-case"
        with self.assertRaisesRegex(AuditValidationError, "case set"):
            evaluate(data)

    def test_rejects_duplicate(self):
        data = fixture()
        data["observations"].append(copy.deepcopy(data["observations"][0]))
        with self.assertRaisesRegex(AuditValidationError, "duplicate"):
            evaluate(data)

    def test_rejects_failed_nonzero_score(self):
        data = fixture()
        data["observations"][0].update(status="error", score=0.1)
        with self.assertRaisesRegex(AuditValidationError, "score 0"):
            evaluate(data)

    def test_rejects_nonfinite_and_boolean_numbers(self):
        for field in ("score", "cost_usd"):
            for invalid in (math.nan, math.inf, -math.inf, True, False, -1, "0.5", None):
                with self.subTest(field=field, invalid=invalid):
                    data = fixture()
                    data["observations"][0][field] = invalid
                    with self.assertRaises(AuditValidationError):
                        evaluate(data)

    def test_rejects_out_of_range_score(self):
        data = fixture()
        data["observations"][0]["score"] = 1.01
        with self.assertRaises(AuditValidationError):
            evaluate(data)

    def test_requires_explicit_failed_cost(self):
        data = fixture()
        data["observations"][0].update(status="error", score=0)
        del data["observations"][0]["cost_usd"]
        with self.assertRaises(AuditValidationError):
            evaluate(data)

    def test_rejects_bad_status_or_schema(self):
        data = fixture()
        data["observations"][0]["status"] = "timeout"
        with self.assertRaises(AuditValidationError):
            evaluate(data)
        for invalid in (True, "1", 1.0, 2):
            data = fixture()
            data["schema_version"] = invalid
            with self.assertRaises(AuditValidationError):
                evaluate(data)

    def test_minimum_cohort_and_reference(self):
        data = fixture()
        with self.assertRaisesRegex(AuditValidationError, "absent"):
            audit(data, "missing")
        for filtered in (
            [row for row in data["observations"] if row["agent_id"] == "baseline"],
            [row for row in data["observations"] if row["case_id"] == "case-01"],
        ):
            small = {**data, "observations": filtered}
            with self.assertRaises(AuditValidationError):
                evaluate(small)

    def test_identical_agents_have_exact_zero_interval(self):
        data = fixture()
        reference = {row["case_id"]: row for row in data["observations"] if row["agent_id"] == "baseline"}
        for row in data["observations"]:
            for field in ("score", "cost_usd", "status"):
                row[field] = reference[row["case_id"]][field]
        report = evaluate(data)
        for comparison in report["comparisons"]:
            self.assertEqual(comparison["score_delta_ci95"], [0.0, 0.0])
            self.assertEqual(comparison["cost_delta_usd_ci95"], [0.0, 0.0])
            self.assertEqual(comparison["score_diagnostic"], "inconclusive")
        # Equal points do not strictly dominate one another.
        self.assertEqual(len(report["observed_pareto_frontier"]), 3)

    def test_failed_attempts_are_retained_in_both_means(self):
        data = fixture()
        expected = [row for row in data["observations"] if row["agent_id"] == "budget"]
        self.assertTrue(any(row["status"] == "error" and row["cost_usd"] > 0 for row in expected))
        report = evaluate(data)
        budget = next(row for row in report["agents"] if row["agent_id"] == "budget")
        self.assertEqual(report["n_cases"], len(expected))
        self.assertAlmostEqual(budget["mean_score"], sum(row["score"] for row in expected) / len(expected))
        self.assertAlmostEqual(budget["mean_cost_usd"], sum(row["cost_usd"] for row in expected) / len(expected))
        self.assertEqual(budget["error_rate"], sum(row["status"] == "error" for row in expected) / len(expected))

    def test_row_shuffle_does_not_change_report(self):
        data = fixture()
        expected = evaluate(data)
        random.Random(193).shuffle(data["observations"])
        self.assertEqual(evaluate(data), expected)

    def test_constant_paired_deltas_produce_degenerate_intervals(self):
        # Between-case variability is large, but paired difference is constant.
        data = fixture()
        for row in data["observations"]:
            case_number = int(row["case_id"].split("-")[1])
            baseline = (case_number % 3) / 4
            row.update(status="ok", score=baseline, cost_usd=case_number)
            if row["agent_id"] != "baseline":
                row["score"] += 0.25
                row["cost_usd"] += 2
        report = evaluate(data)
        for comparison in report["comparisons"]:
            self.assertEqual(comparison["score_delta_ci95"], [0.25, 0.25])
            self.assertEqual(comparison["cost_delta_usd_ci95"], [2.0, 2.0])
            self.assertEqual(comparison["score_diagnostic"], "positive_score_difference")

    def test_shared_case_draws_preserve_linked_outcomes_and_agents(self):
        data = fixture()
        for row in data["observations"]:
            case_number = int(row["case_id"].split("-")[1])
            delta = (case_number % 3) / 4
            row.update(status="ok", score=0, cost_usd=0)
            if row["agent_id"] != "baseline":
                row.update(score=delta, cost_usd=delta * 2)
        report = evaluate(data)
        left, right = report["comparisons"]
        self.assertEqual(left["score_delta_ci95"], right["score_delta_ci95"])
        self.assertEqual(left["cost_delta_usd_ci95"], right["cost_delta_usd_ci95"])
        self.assertEqual(left["cost_delta_usd_ci95"], [value * 2 for value in left["score_delta_ci95"]])

    def test_known_observed_dominance(self):
        data = fixture()
        for row in data["observations"]:
            row.update(status="ok", score=0.5, cost_usd=1)
            if row["agent_id"] == "budget":
                row.update(score=0.75, cost_usd=0.5)
        self.assertEqual(evaluate(data)["observed_pareto_frontier"], ["budget"])

    def test_synthetic_and_small_cohort_are_explicit(self):
        report = evaluate(fixture())
        self.assertTrue(report["metadata"]["synthetic_demo"])
        self.assertEqual({warning["code"] for warning in report["warnings"]}, {"small_cohort", "synthetic_demo"})

    def test_finite_extreme_costs_remain_serialisable(self):
        data = fixture()
        for row in data["observations"]:
            row["cost_usd"] = sys.float_info.max
        report = evaluate(data)
        for agent in report["agents"]:
            self.assertEqual(agent["mean_cost_usd"], sys.float_info.max)
        json.dumps(report, allow_nan=False)

    def test_cli_writes_valid_json_and_rejects_bad_input(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            command = [sys.executable, "-m", "eval_decision_audit", "--input", str(ROOT / "examples" / "synthetic.json"), "--reference", "baseline", "--output", str(output), "--bootstrap-samples", "100"]
            completed = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["n_cases"], 10)
            invalid = Path(directory) / "invalid.json"
            invalid.write_text('{"schema_version": 2}', encoding="utf-8")
            command[4] = str(invalid)
            completed = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 2)
            self.assertIn("schema_version", completed.stderr)


if __name__ == "__main__":
    unittest.main()
