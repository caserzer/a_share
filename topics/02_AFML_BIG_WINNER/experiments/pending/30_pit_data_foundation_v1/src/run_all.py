"""Offline reproducible audit pipeline; live probes require an explicit flag."""

import argparse
from pathlib import Path
import subprocess
import sys


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--live",
        action="store_true",
        help="Append bounded public-source discovery attempts",
    )
    p.add_argument(
        "--freeze",
        action="store_true",
        help="Copy a private immutable release after validation",
    )
    args = p.parse_args()
    root = Path(__file__).resolve().parent
    if args.live:
        subprocess.run(
            [sys.executable, str(root / "probe_sources.py"), "--live"], check=True
        )
        subprocess.run(
            [sys.executable, str(root / "probe_financial_vintages.py")], check=True
        )
    for name in [
        "run_audit",
        "expand_bridge",
        "audit_status",
        "build_vintage_example",
        "field_matrix",
        "predecessor_audit",
        "validate_delivery",
        "report",
    ]:
        subprocess.run([sys.executable, str(root / (name + ".py"))], check=True)
    if args.freeze:
        subprocess.run([sys.executable, str(root / "freeze_release.py")], check=True)


if __name__ == "__main__":
    main()
