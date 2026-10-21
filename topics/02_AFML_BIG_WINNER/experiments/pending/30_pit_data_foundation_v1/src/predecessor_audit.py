"""Explicit lineage map of preserved source code, contracts and conclusions."""

import pandas as pd
from archive import EP, sha


def main():
    records = []
    notes = {
        "01": (
            "metadata/raw/shares/status/Qlib",
            "source cache and calendar; lifetime SH ST and bar-derived status not adopted as certification",
        ),
        "05": (
            "Top400/100/data source census",
            "reuse 318/229 window source denominator; no TopN population promoted to all A-share",
        ),
        "19": (
            "decision/next open/limits/cooldown",
            "reuse separation of decision and fill; qfq execution and vendor industry remain proxy",
        ),
        "24": (
            "financials/valuation/actions/historical industry",
            "reuse preserved source fields and releases; NOTICE/UPDATE not first-version proof",
        ),
        "25": (
            "distribution/forward maturity contract",
            "preserve qfq labels and original negative conclusion; no training rerun",
        ),
        "26": (
            "6-calendar-month R<-20%",
            "reuse strict threshold and missing labels; no new probabilities",
        ),
        "27": (
            "frozen D0/industry/state",
            "reuse 43960-row D0 lineage and source receipts; no current industry backfill",
        ),
        "28": (
            "D1 recovery/census",
            "reuse 228 raw quote recoveries and full census; no settlement certification",
        ),
        "29": (
            "adaptation/as-of mature labels",
            "preserve fixed D0 and historical exploration boundary; no issuer adaptation on immature outcomes",
        ),
    }
    for prefix, (contract, decision) in notes.items():
        root = next(EP.parent.glob(prefix + "_*"))
        selected = []
        for p in root.rglob("*"):
            if not p.is_file() or any(
                x in p.parts for x in ["local_cache", "__pycache__"]
            ):
                continue
            relative = p.relative_to(root)
            if (
                (
                    p.suffix in [".py", ".yaml"]
                    and relative.parts[0] in ["src", "code", "configs", "tests"]
                )
                or p.name
                in [
                    "config.yaml",
                    "research_plan.md",
                    "requirement.md",
                    "final_conclusion.md",
                    "EP24_research_report.md",
                ]
                or (
                    p.suffix == ".md"
                    and "reports" in p.parts
                    and any(
                        x in p.name for x in ["final", "integrity", "audit", "contract"]
                    )
                )
            ):
                selected.append(p)
        for p in sorted(selected):
            # Reading the exact bytes is part of the source/code audit receipt.
            data = p.read_bytes()
            records.append(
                dict(
                    episode=prefix,
                    path=str(p.relative_to(EP.parent)),
                    bytes=len(data),
                    sha256=sha(p),
                    audited_contract=contract,
                    D2_reuse_decision=decision,
                    prior_unchanged=True,
                )
            )
    pd.DataFrame(records).to_csv(
        EP / "outputs/audits/predecessor_lineage.csv", index=False
    )
    print("predecessor contracts/code/reports inventoried", len(records), flush=True)


if __name__ == "__main__":
    main()
