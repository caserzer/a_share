"""EP30 versioned as-of facts. Proxy records cannot satisfy strict requests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import math
import pandas as pd

from archive import sha, write_json

TZ = "Asia/Shanghai"
STRICT = ("PIT-certified", "PIT-reconstructed")
TIERS = (*STRICT, "Historical-proxy", "UNKNOWN/BLOCKED")
COLUMNS = [
    "record_id",
    "logical_key",
    "security_id",
    "field",
    "value",
    "event_time",
    "effective_time",
    "known_at",
    "source_observed_at",
    "ingested_at",
    "vendor_revision_time",
    "source_uri",
    "source_path",
    "source_sha256",
    "unit",
    "original_version",
    "transform_sha256",
    "quality_tier",
    "publication_evidence",
    "reconstruction",
    "supersedes",
]
CLOCKS = [
    "event_time",
    "effective_time",
    "known_at",
    "source_observed_at",
    "ingested_at",
    "vendor_revision_time",
]


def stamp(value):
    if value is None or pd.isna(value):
        return pd.NaT
    t = pd.Timestamp(value)
    return t.tz_localize(TZ) if t.tzinfo is None else t.tz_convert(TZ)


class Calendar:
    def __init__(self, dates, verified_through=None):
        self.days = (
            pd.DatetimeIndex(pd.to_datetime(dates)).tz_localize(None).normalize()
        )
        if (
            self.days.has_duplicates
            or not self.days.is_monotonic_increasing
            or len(self.days) == 0
        ):
            raise ValueError("calendar must be nonempty, sorted and unique")
        self.verified_through = pd.Timestamp(
            verified_through or self.days[-1]
        ).normalize()
        if self.verified_through > self.days[-1]:
            raise ValueError("verified calendar cutoff outside supplied calendar")

    def publication_time(self, published, precise=False):
        if precise:
            return stamp(published)
        day = stamp(published).tz_localize(None).normalize()
        i = self.days.searchsorted(day, side="right")
        if i >= len(self.days) or self.days[i] > self.verified_through:
            return pd.NaT
        return stamp(self.days[i] + pd.Timedelta(hours=9, minutes=30))


@dataclass(frozen=True)
class AsOfResult:
    value: object = None
    status: str = "UNKNOWN"
    reason: str = "NO_ELIGIBLE_RECORD"
    records: tuple = ()


class FactStore:
    def __init__(self, facts=None, archive_root=None):
        self.archive_root = Path(archive_root) if archive_root else None
        self.facts = pd.DataFrame(columns=COLUMNS)
        if facts is not None:
            self.append(facts)

    def append(self, rows):
        incoming = pd.DataFrame(rows).copy()
        if incoming.empty:
            return
        missing = set(COLUMNS) - set(incoming.columns)
        if missing:
            raise ValueError("missing fact columns: " + ",".join(sorted(missing)))
        for col in CLOCKS:
            incoming[col] = pd.to_datetime(
                incoming[col].map(stamp), utc=True
            ).dt.tz_convert(TZ)
        if (
            incoming.record_id.duplicated().any()
            or incoming.record_id.isin(self.facts.record_id).any()
        ):
            raise ValueError("append-only record id violation")
        for row in incoming.to_dict("records"):
            if row["quality_tier"] not in TIERS:
                raise ValueError("unknown quality tier")
            for key in [
                "record_id",
                "logical_key",
                "security_id",
                "field",
                "source_uri",
                "source_sha256",
                "unit",
                "original_version",
                "transform_sha256",
            ]:
                if not row[key]:
                    raise ValueError("missing provenance: " + key)
            if any(
                pd.isna(row[c])
                for c in ["effective_time", "source_observed_at", "ingested_at"]
            ):
                raise ValueError("missing mandatory clock")
            if row["ingested_at"] < row["source_observed_at"]:
                raise ValueError("ingestion precedes observation")
            if row["quality_tier"] in STRICT:
                if pd.isna(row["known_at"]) or not row["publication_evidence"]:
                    raise ValueError(
                        "strict tier requires historical publication/version evidence"
                    )
                if (
                    row["quality_tier"] == "PIT-reconstructed"
                    and not row["reconstruction"]
                ):
                    raise ValueError("missing deterministic reconstruction recipe")
                if not self._source_ok(row):
                    raise ValueError("source bytes missing or hash mismatch")
            value = row["value"]
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("unknown values must be null with explicit status")
            parent = row["supersedes"]
            if parent is not None and not pd.isna(parent):
                predecessors = (
                    incoming
                    if self.facts.empty
                    else pd.concat([self.facts, incoming], ignore_index=True)
                )
                prior = predecessors[predecessors.record_id.eq(parent)]
                if len(prior) != 1:
                    raise ValueError("correction must name one preserved predecessor")
                old = prior.iloc[0]
                if any(
                    old[k] != row[k]
                    for k in ["security_id", "field", "logical_key", "effective_time"]
                ):
                    raise ValueError("correction must preserve logical fact identity")
                if (
                    pd.isna(row["known_at"])
                    or pd.isna(old.known_at)
                    or row["known_at"] <= old.known_at
                ):
                    raise ValueError(
                        "correction must have a strictly later verified/declared publication clock"
                    )
        self.facts = (
            incoming
            if self.facts.empty
            else pd.concat([self.facts, incoming], ignore_index=True)
        )

    def _source_ok(self, row):
        source = Path(row["source_path"])
        if source.is_file():
            return sha(source) == row["source_sha256"]
        if self.archive_root:
            digest = row["source_sha256"]
            source = self.archive_root / digest[:2] / digest
            return source.is_file() and sha(source) == digest
        return False

    def get_asof(
        self,
        security,
        field,
        decision_time,
        quality_tier="PIT-reconstructed",
        mode="historical",
    ):
        if quality_tier not in TIERS or mode not in ("historical", "archived"):
            raise ValueError("invalid tier or as-of mode")
        t = stamp(decision_time)
        allowed = STRICT[:1] if quality_tier == STRICT[0] else STRICT
        if quality_tier == "Historical-proxy":
            allowed = (*STRICT, "Historical-proxy")
        if quality_tier == "UNKNOWN/BLOCKED":
            return AsOfResult(reason="UNKNOWN_TIER_IS_NOT_AN_INPUT")
        f = self.facts
        if f.empty:
            return AsOfResult()
        f = f[
            (f.security_id == security)
            & (f.field == field)
            & (f.effective_time <= t)
            & f.quality_tier.isin(allowed)
        ].copy()
        # Unknown availability is permitted only on an explicitly requested diagnostic proxy.
        f = f[
            (f.known_at <= t)
            | ((f.quality_tier == "Historical-proxy") & f.known_at.isna())
        ]
        if mode == "archived":
            f = f[(f.source_observed_at <= t) & (f.ingested_at <= t)]
        if f.empty:
            return AsOfResult()
        # First select the original/correction vintage for each independently sourced logical fact.
        f = f.sort_values(["known_at", "ingested_at", "record_id"], na_position="first")
        superseded = set(f.supersedes.dropna())
        f = f[~f.record_id.isin(superseded)]
        f = f.groupby(["logical_key", "source_uri"], sort=True).tail(1)
        f = f[f.effective_time == f.effective_time.max()]
        # A record that loses its evidence must fail closed even after it was loaded.
        for r in f[f.quality_tier.isin(STRICT)].to_dict("records"):
            if not self._source_ok(r):
                return AsOfResult(
                    reason="SOURCE_HASH_MISMATCH", records=tuple(f.to_dict("records"))
                )
        records = tuple(f.to_dict("records"))
        values = {
            json.dumps([r["value"], r["unit"]], sort_keys=True, default=str)
            for r in records
        }
        if len(values) != 1:
            return AsOfResult(reason="UNRESOLVED_SOURCE_CONFLICT", records=records)
        if f.value.isna().any():
            return AsOfResult(reason="EXPLICIT_UNKNOWN", records=records)
        tier = (
            "Historical-proxy"
            if (f.quality_tier == "Historical-proxy").any()
            else (
                "PIT-reconstructed"
                if (f.quality_tier == "PIT-reconstructed").any()
                else "PIT-certified"
            )
        )
        return AsOfResult(
            f.iloc[-1].value,
            tier,
            "RETROSPECTIVE_AVAILABILITY_UNPROVEN"
            if tier == "Historical-proxy"
            else "OK",
            records,
        )

    def universe_asof(
        self, decision_time, quality_tier="PIT-reconstructed", mode="historical"
    ):
        result = []
        for security in sorted(self.facts.security_id.unique()):
            listed = self.get_asof(
                security, "listed", decision_time, quality_tier, mode
            )
            if listed.value is True or listed.value == 1:
                row = {"security_id": security, "listed_tier": listed.status}
                for field in [
                    "code",
                    "name",
                    "exchange",
                    "board",
                    "is_st",
                    "can_buy",
                    "can_sell",
                ]:
                    value = self.get_asof(
                        security, field, decision_time, quality_tier, mode
                    )
                    row[field] = value.value
                    row[field + "_reason"] = value.reason
                result.append(row)
        return pd.DataFrame(result)

    def snapshot_manifest(self, asof_time, mode="archived"):
        t = stamp(asof_time)
        f = self.facts
        if f.empty:
            records = []
        else:
            f = f[
                (f.effective_time <= t)
                & (
                    (f.known_at <= t)
                    | (f.quality_tier.eq("Historical-proxy") & f.known_at.isna())
                )
            ]
            if mode == "archived":
                f = f[(f.source_observed_at <= t) & (f.ingested_at <= t)]
            elif mode != "historical":
                raise ValueError("invalid mode")
            records = sorted(f.to_dict("records"), key=lambda r: r["record_id"])
        canonical = json.dumps(
            records, sort_keys=True, default=str, ensure_ascii=False, allow_nan=False
        )
        return {
            "asof_time": str(t),
            "mode": mode,
            "record_count": len(records),
            "facts_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
            "source_sha256": sorted({r["source_sha256"] for r in records}),
            "transform_sha256": sorted({r["transform_sha256"] for r in records}),
        }

    def to_parquet(self, path):
        f = self.facts.copy()
        # JSON encodes heterogeneous scalar field values without dtype coercion.
        f["value"] = f.value.map(
            lambda v: json.dumps(v, ensure_ascii=False, allow_nan=False)
        )
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        f.to_parquet(path, index=False)
        write_json(
            str(path) + ".manifest.json",
            {"sha256": sha(path), "rows": len(f), "format": "D2-facts-json-scalar-v1"},
        )

    @classmethod
    def from_parquet(cls, path, archive_root=None):
        receipt = json.loads(Path(str(path) + ".manifest.json").read_text())
        if sha(path) != receipt["sha256"]:
            raise ValueError("Parquet snapshot hash mismatch")
        f = pd.read_parquet(path)
        f["value"] = f.value.map(json.loads)
        return cls(f, archive_root=archive_root)

    def qlib_frame(self, requests, quality_tier="PIT-reconstructed", mode="historical"):
        """Return Qlib-compatible features and mandatory per-cell provenance separately."""
        values, provenance = [], []
        for security, field, time in requests:
            r = self.get_asof(security, field, time, quality_tier, mode)
            key = {"datetime": stamp(time).tz_localize(None), "instrument": security}
            values.append({**key, "field": "$" + field, "value": r.value})
            provenance.append(
                {
                    **key,
                    "field": field,
                    "status": r.status,
                    "reason": r.reason,
                    "record_ids": [x["record_id"] for x in r.records],
                }
            )
        if not values:
            return pd.DataFrame(), pd.DataFrame()
        frame = pd.DataFrame(values).pivot(
            index=["datetime", "instrument"], columns="field", values="value"
        )
        return frame.sort_index(), pd.DataFrame(provenance)


def reconstruct_valuation(
    raw_close,
    total_shares,
    earnings_ttm=None,
    equity=None,
    sales_ttm=None,
    cash_dividends=None,
):
    """Call only after same-date/as-of provenance gates, in CNY and shares."""
    if raw_close is None or total_shares is None or raw_close <= 0 or total_shares <= 0:
        return {"status": "UNKNOWN", "reason": "MISSING_PRICE_OR_EFFECTIVE_SHARES"}
    cap = raw_close * total_shares
    out = {"status": "DERIVED_REQUIRES_INPUT_PROVENANCE", "market_cap_cny": cap}
    for name, denominator in [("pe", earnings_ttm), ("pb", equity), ("ps", sales_ttm)]:
        out[name] = (
            cap / denominator if denominator is not None and denominator > 0 else None
        )
        out[name + "_reason"] = (
            "OK" if out[name] is not None else "MISSING_OR_NONPOSITIVE_DENOMINATOR"
        )
    out["dividend_yield"] = (
        cash_dividends / cap
        if cash_dividends is not None and cash_dividends >= 0
        else None
    )
    return out
