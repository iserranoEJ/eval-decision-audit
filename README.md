# Eval Decision Audit

**Audit whether agent evaluation results can support a cost–quality comparison.**

A small Python library and CLI that checks evaluation provenance, compares agents on matched tasks, and reports paired uncertainty in score and cost.

## Why this project

An apparent improvement can come from a different scorer, a different task set or a changed execution environment. Before drawing a Pareto frontier, the comparison needs an explicit measurement contract.

This is a concrete problem in current agent evaluation: the [τ²-bench July 2026 changelog](https://github.com/sierra-research/tau2-bench/blob/main/CHANGELOG.md) documents a grading change that makes scores across that release incompatible. [Anthropic's February 2026 infrastructure study](https://www.anthropic.com/engineering/infrastructure-noise) also shows that execution configuration can affect agent scores. These are motivations for the project, not experiments performed by this repository.

## Status

Early prototype. The initial release checks explicit dataset, scorer and harness revisions; rejects incomplete paired cohorts; and calculates task-level paired bootstrap intervals. Its Pareto frontier is descriptive.

The included demo is **synthetic test data**, not a benchmark of real models. No model APIs, paid services or proprietary datasets are required. Inspect adapters, repeat-aware analysis and scorer-sensitivity experiments are planned, not implemented in this first version.

## Quick start

Requires Python 3.11 or later. The library has no runtime dependencies.

```bash
git clone https://github.com/iserranoEJ/eval-decision-audit.git
cd eval-decision-audit
python -m venv .venv
```

Activate the virtual environment for your shell, then:

```bash
python -m pip install -e .
eval-decision-audit --input examples/synthetic.json --reference baseline --output report.json --bootstrap-samples 2000 --seed 42
python -m unittest discover -s tests -v
```

## Measurement contract

- Each agent must have exactly one observation for every case in the same cohort.
- Dataset, scorer and harness revisions must match the declared provenance.
- Scores lie in `[0, 1]`; recorded costs are non-negative USD values.
- Failed attempts remain in the cohort with score zero and their incurred cost.
- The same resampled case indices are used for paired score and cost differences.

The initial contract is deliberately small. Matching revision strings is necessary but not sufficient to establish a fair comparison: the caller must also control model configuration, task distribution, execution resources, budgets and pricing. See [methodology](docs/methodology.md).

## How to read the output

The report includes mean score, mean cost and failure rate by agent, a frontier based on observed means, and paired score/cost differences against the chosen reference with percentile bootstrap intervals.

An interval spanning zero is inconclusive about the direction of the score difference; it is not evidence of equivalence. An observed frontier is not proof of dominance in the underlying population. Small-cohort and synthetic-data warnings are part of the report.

## Next milestones

1. Import real, shareable evaluation logs with preserved provenance.
2. Model repeated attempts and resample at the task level.
3. Compare the same trajectories under multiple scorers without mixing those regimes into one ranking.
4. Evaluate budgeted selection on held-out tasks and measure sensitivity of the decision.

The [roadmap](docs/roadmap.md) tracks the acceptance criteria. See [related work](docs/related-work.md) for the existing frameworks and analysis tools this project should complement.

## Development and provenance

Agent-assisted development with tests and review. The human maintainer is [Iñaki Serrano](https://github.com/iserranoEJ). Commit activity is not an experimental result; claims about models require real, traceable evaluation data.

This is an independent project. It contains no Model ML Composite internals or employer datasets.

MIT licensed. See [LICENSE](LICENSE).
