"""Compute descriptive summaries and paired percentile bootstrap intervals.

Input schema v1 is a JSON object with ``schema_version: 1``, ``provenance``
and ``observations``. Provenance contains nonempty ``dataset_revision``,
``scorer_revision`` and ``harness_revision`` strings. Every observation has
the same three revisions, plus nonempty ``case_id`` and ``agent_id``, a finite
``score`` in [0, 1], finite nonnegative ``cost_usd`` and ``status`` (ok/error).
Errors stay in the cohort with score zero and their incurred cost. At least
two agents must each have exactly the same set of at least two cases. Optional
``metadata.synthetic_demo`` is boolean; mark constructed examples as true.

Scores must be comparable across cases and higher must mean better. Cost is
the caller's declared total per attempt, including failed attempts. Revision
equality checks declared identifiers, not their truth or the scorer's validity.
One observation per agent/case is supported; repeated attempts need a future
schema. Bootstrap resampling treats cases as independent sampling units and
does not capture stochastic run-to-run variation or dependent task families.
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping
from typing import Any


class AuditValidationError(ValueError):
    """The input cannot support the declared paired comparison."""


REVISIONS = ("dataset_revision", "scorer_revision", "harness_revision")


def _text(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AuditValidationError(f"{location} must be a nonempty string")
    return value


def _number(value: Any, location: str, *, upper: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AuditValidationError(f"{location} must be a finite number, not a boolean")
    try:
        result = float(value)
    except OverflowError as exc:
        raise AuditValidationError(f"{location} must be finite") from exc
    if not math.isfinite(result) or result < 0 or (upper is not None and result > upper):
        bounds = "[0, 1]" if upper == 1 else "[0, infinity)"
        raise AuditValidationError(f"{location} must be finite and in {bounds}")
    return result


def _mean(values: list[float]) -> float:
    # Normalisation avoids overflowing even when each value is near float max.
    scale = max(abs(value) for value in values)
    if scale == 0:
        return 0.0
    return scale * (math.fsum(value / scale for value in values) / len(values))


def _percentile(sorted_values: list[float], probability: float) -> float:
    position = (len(sorted_values) - 1) * probability
    lower = math.floor(position)
    fraction = position - lower
    if lower == len(sorted_values) - 1:
        return sorted_values[lower]
    # Weighted interpolation also avoids overflow in (upper - lower).
    first, second = sorted_values[lower], sorted_values[lower + 1]
    if first == second:
        return first
    scale = max(abs(first), abs(second))
    return scale * ((1 - fraction) * (first / scale) + fraction * (second / scale))


def _interval(samples: list[float]) -> list[float]:
    ordered = sorted(samples)
    return [_percentile(ordered, 0.025), _percentile(ordered, 0.975)]


def audit(
    document: Mapping[str, Any],
    reference: str,
    *,
    bootstrap_samples: int = 2000,
    seed: int = 42,
) -> dict[str, Any]:
    """Return a deterministic report; reject incomplete or incompatible data.

    Deltas are candidate minus reference. Positive score differences favour
    the candidate; negative cost differences mean cheaper. Intervals are
    marginal, unadjusted percentile intervals, not a joint decision rule.
    The observed Pareto frontier is descriptive, without uncertainty claims.
    """
    if not isinstance(document, Mapping):
        raise AuditValidationError("input must be an object")
    version = document.get("schema_version")
    if type(version) is not int or version != 1:
        raise AuditValidationError("schema_version must be integer 1")
    if type(bootstrap_samples) is not int or bootstrap_samples < 2:
        raise AuditValidationError("bootstrap_samples must be an integer of at least 2")
    if type(seed) is not int:
        raise AuditValidationError("seed must be an integer")
    reference = _text(reference, "reference")
    provenance = document.get("provenance")
    if not isinstance(provenance, Mapping):
        raise AuditValidationError("provenance must be an object")
    revisions = {key: _text(provenance.get(key), f"provenance.{key}") for key in REVISIONS}
    metadata = document.get("metadata", {})
    if not isinstance(metadata, Mapping):
        raise AuditValidationError("metadata must be an object")
    synthetic_demo = metadata.get("synthetic_demo", False)
    if type(synthetic_demo) is not bool:
        raise AuditValidationError("metadata.synthetic_demo must be boolean")
    observations = document.get("observations")
    if not isinstance(observations, list) or not observations:
        raise AuditValidationError("observations must be a nonempty list")

    grid: dict[str, dict[str, dict[str, Any]]] = {}
    for index, row in enumerate(observations):
        location = f"observations[{index}]"
        if not isinstance(row, Mapping):
            raise AuditValidationError(f"{location} must be an object")
        case_id = _text(row.get("case_id"), f"{location}.case_id")
        agent_id = _text(row.get("agent_id"), f"{location}.agent_id")
        for key in REVISIONS:
            if row.get(key) != revisions[key]:
                raise AuditValidationError(f"{location}.{key} does not match provenance")
        score = _number(row.get("score"), f"{location}.score", upper=1)
        cost = _number(row.get("cost_usd"), f"{location}.cost_usd")
        status = row.get("status")
        if status not in ("ok", "error"):
            raise AuditValidationError(f"{location}.status must be 'ok' or 'error'")
        if status == "error" and score != 0:
            raise AuditValidationError(f"{location}: error observations must have score 0")
        by_case = grid.setdefault(agent_id, {})
        if case_id in by_case:
            raise AuditValidationError(f"duplicate observation for agent {agent_id!r}, case {case_id!r}")
        by_case[case_id] = {"score": score, "cost_usd": cost, "status": status}

    if len(grid) < 2:
        raise AuditValidationError("at least two agents are required")
    if reference not in grid:
        raise AuditValidationError(f"reference agent {reference!r} is absent")
    agent_ids = sorted(grid)
    cases = sorted(grid[reference])
    if len(cases) < 2:
        raise AuditValidationError("at least two cases are required")
    case_set = set(cases)
    for agent_id in agent_ids:
        if set(grid[agent_id]) != case_set:
            raise AuditValidationError(f"agent {agent_id!r} has an incomplete or different case set")

    summaries: dict[str, dict[str, float]] = {}
    score_deltas: dict[str, list[float]] = {}
    cost_deltas: dict[str, list[float]] = {}
    for agent_id in agent_ids:
        rows = [grid[agent_id][case] for case in cases]
        summaries[agent_id] = {
            "mean_score": _mean([row["score"] for row in rows]),
            "mean_cost_usd": _mean([row["cost_usd"] for row in rows]),
            "error_rate": sum(row["status"] == "error" for row in rows) / len(cases),
        }
        if agent_id != reference:
            score_deltas[agent_id] = [grid[agent_id][case]["score"] - grid[reference][case]["score"] for case in cases]
            cost_deltas[agent_id] = [grid[agent_id][case]["cost_usd"] - grid[reference][case]["cost_usd"] for case in cases]

    candidates = sorted(score_deltas)
    draws = {candidate: {"score": [], "cost": []} for candidate in candidates}
    rng = random.Random(seed)
    for _ in range(bootstrap_samples):
        # One draw is shared by every agent and both outcomes: pairing is kept.
        indices = [rng.randrange(len(cases)) for _ in cases]
        for candidate in candidates:
            draws[candidate]["score"].append(_mean([score_deltas[candidate][i] for i in indices]))
            draws[candidate]["cost"].append(_mean([cost_deltas[candidate][i] for i in indices]))

    comparisons = []
    for candidate in candidates:
        score_ci = _interval(draws[candidate]["score"])
        diagnostic = "inconclusive"
        if score_ci[0] > 0:
            diagnostic = "positive_score_difference"
        elif score_ci[1] < 0:
            diagnostic = "negative_score_difference"
        comparisons.append({
            "agent_id": candidate,
            "reference_agent_id": reference,
            "mean_score_delta": _mean(score_deltas[candidate]),
            "score_delta_ci95": score_ci,
            "mean_cost_delta_usd": _mean(cost_deltas[candidate]),
            "cost_delta_usd_ci95": _interval(draws[candidate]["cost"]),
            "score_diagnostic": diagnostic,
        })

    frontier = []
    for candidate in agent_ids:
        current = summaries[candidate]
        dominated = any(
            other["mean_score"] >= current["mean_score"]
            and other["mean_cost_usd"] <= current["mean_cost_usd"]
            and (other["mean_score"] > current["mean_score"] or other["mean_cost_usd"] < current["mean_cost_usd"])
            for other_id, other in summaries.items() if other_id != candidate
        )
        if not dominated:
            frontier.append(candidate)
    warnings = []
    if len(cases) < 30:
        warnings.append({"code": "small_cohort", "message": "Fewer than 30 cases; bootstrap intervals may be unstable and have poor coverage."})
    if synthetic_demo:
        warnings.append({"code": "synthetic_demo", "message": "Constructed demonstration data; this is not evidence about real agents or models."})
    return {
        "schema_version": 1,
        "provenance": revisions,
        "metadata": {"synthetic_demo": synthetic_demo},
        "n_cases": len(cases),
        "reference_agent_id": reference,
        "comparability": {"revision_match": True, "complete_paired_case_grid": True, "failed_attempts_included": True},
        "method": {
            "name": "paired_case_percentile_bootstrap",
            "bootstrap_samples": bootstrap_samples,
            "seed": seed,
            "confidence_level": 0.95,
            "resampling_unit": "case",
            "delta_direction": "candidate_minus_reference",
            "interval_scope": "marginal_unadjusted",
            "assumptions": ["Independent cases with comparable scores", "One observed attempt per agent and case; no run-to-run uncertainty estimate"],
        },
        "agents": [{"agent_id": agent_id, **summaries[agent_id]} for agent_id in agent_ids],
        "observed_pareto_frontier": frontier,
        "pareto_frontier_interpretation": "Descriptive frontier of observed means only; not a statistically established ranking or routing policy.",
        "comparisons": comparisons,
        "warnings": warnings,
    }
