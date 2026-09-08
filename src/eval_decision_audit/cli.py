"""Command line entry point; all computation is local and uses no model API."""

import argparse
import json
import sys
from pathlib import Path

from .audit import AuditValidationError, audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit paired evaluation score and cost differences.")
    parser.add_argument("--input", required=True, type=Path, help="Schema v1 observation JSON")
    parser.add_argument("--reference", required=True, help="Reference agent_id")
    parser.add_argument("--output", required=True, type=Path, help="Report JSON path")
    parser.add_argument("--bootstrap-samples", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    try:
        if args.input.resolve() == args.output.resolve():
            raise AuditValidationError("input and output must be different files")
        document = json.loads(args.input.read_text(encoding="utf-8"))
        report = audit(document, args.reference, bootstrap_samples=args.bootstrap_samples, seed=args.seed)
        payload = json.dumps(report, indent=2, allow_nan=False) + "\n"
        args.output.write_text(payload, encoding="utf-8")
    except (AuditValidationError, OSError, ValueError) as exc:
        print(f"eval-decision-audit: {exc}", file=sys.stderr)
        return 2
    print(f"Wrote {args.output} ({report['n_cases']} paired cases, {len(report['agents'])} agents)")
    return 0
