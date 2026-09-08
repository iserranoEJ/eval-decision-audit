# Progress

## 2026-09-08 — Initial implementation

Completed the M0 analysis contract: strict provenance checks, complete paired cohorts, retained failed-attempt costs, deterministic paired bootstrap and a descriptive observed frontier. Added a synthetic ten-case, three-agent fixture and 20 tests.

Independent review identified overflow for very large finite costs. Mean and percentile calculations were revised to use scaling, with a regression test. The installed command was run from a fresh virtual environment and produced valid JSON. No model inference or empirical benchmark was run.

Validation: `python -m unittest discover -s tests -v` passed 20 tests; the documented `eval-decision-audit` command ran successfully with 2,000 bootstrap resamples and seed 42. CI is configured for Python 3.11–3.13; remote outcomes are tracked in GitHub Actions.

Next: select one public Inspect log, verify its license and schema, and write a conversion specification that preserves missing-cost information and provenance. Do not invent cost values to fit the current schema. Any schema extension must explain compatibility with v1.
