# Measurement contract and interpretation

## The question

Given a matched set of tasks, how do observed quality and cost differ between agent configurations, and what uncertainty remains over tasks?

The initial version is a descriptive analysis tool with explicit rejection rules. It does not establish causal effects of a model change, validate a grader, or certify that a system is suitable for deployment.

## Unit of analysis

One observation per agent and case. Cases are sorted before sampling, so input row order must not affect a seeded result. Every agent must share the exact same case set. An omitted failed task is a cohort error, not a reason to average over a smaller denominator.

An error has score zero and an explicit cost. This is a particular evaluation policy: it measures delivered performance including failures. It does not distinguish model error from infrastructure error or remove the need to report that distinction in later versions.

## Provenance

Every observation repeats `dataset_revision`, `scorer_revision` and `harness_revision`, and these must agree with the declared provenance. Revision identifiers should be immutable digests or commit IDs in real studies, not moving labels such as `latest`.

This check catches contradictory declarations; it cannot prove that declarations are correct. It also does not capture all confounders. Real data imports will need model snapshot, agent/prompt settings, execution limits, sampling settings, run identity, price date, retries and cache treatment. In v0, include such distinctions in the agent identifier and study documentation, and do not compare experiments that differ in uncontrolled conditions.

## Paired bootstrap

Draw case indices with replacement. Use the same indices for every agent and for both score and cost. Calculate mean differences relative to the reference in each resample, and take the 2.5th and 97.5th empirical percentiles.

The inference concerns variation over the observed task population under an independent-task assumption. Correlated templates require cluster-level sampling, which is not implemented yet. Multiple attempts per task are also not implemented: do not encode repeated attempts as independent case IDs to artificially narrow uncertainty.

Percentile intervals are approximate and can be poor for small, degenerate or highly discrete samples. A warning is emitted for fewer than 30 cases; 30 is a heuristic warning threshold, not a guarantee of validity. More bootstrap iterations reduce simulation noise, not missing experimental evidence.

## Cost and decisions

The frontier uses the observed means: a configuration is dominated when another has no higher cost and no lower score, with at least one strict difference. This is descriptive, with no confidence guarantee.

Intervals crossing zero do not establish equivalence. Separate marginal intervals do not establish a joint cost–quality guarantee. No multiplicity correction, non-inferiority margin, selection correction or confirmatory hypothesis test is performed in v0.

Do not optimise a routing policy on these results and report performance on the same tasks as an unbiased test. Held-out selection and joint uncertainty are roadmap items.

## Data and reproducibility

The supplied fixture uses fictional agent names and constructed numbers. It exercises success, failure, different costs and disagreement over tasks; it cannot support a claim about any real model. Record the command, seed, bootstrap count, software revision and raw input for a real analysis.
