# Related work

Focused literature and tooling scan, 8 September 2026. This is not an exhaustive novelty claim.

## Motivation

- **[τ²-bench changelog, 15 July 2026](https://github.com/sierra-research/tau2-bench/blob/main/CHANGELOG.md):** a grading revision changes score meaning across releases. This motivates explicit version boundaries; no τ²-bench reproduction has been performed here.
- **[Anthropic, 5 February 2026](https://www.anthropic.com/engineering/infrastructure-noise):** execution configuration affects coding-agent measurements. This is older engineering evidence, not a new September announcement.
- **[Rank Reversal in Multilingual LLM Judges, 23 August 2026](https://arxiv.org/abs/2608.22432):** recent calibration research motivates a later scorer-language sensitivity study. It is a preprint, and calibration consistency should not be confused with correctness.

## Existing tools

[Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai) already supplies evaluation execution and logging. An adapter should reuse that machinery rather than build another provider/harness layer.

[Arena](https://github.com/macanderson/arena) already offers paired comparison and regression analysis. [HAL](https://github.com/princeton-pli/hal-harness) is prior work on cost-aware agent evaluation. Pareto frontiers and bootstrap intervals are established techniques; they are not innovations of this repository.

The intended contribution is a compact audit of whether a cost–quality decision survives measurement changes, with explicit provenance and refusal to merge incompatible regimes. The initial release only establishes a strict single-regime contract and paired descriptive analysis. Repeat-aware uncertainty, sensitivity studies and real-data adapters remain future work.

## Contribution direction

Prefer a focused reproduction or regression test upstream when this project's adapter reveals a concrete bug. Verify the current issue and PR state before starting; a dated research list is not an assignment or evidence that work remains available.
