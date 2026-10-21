"""Read-only adapter for the independently frozen D2-v2 backfill release."""

import json
from pathlib import Path
import pandas as pd
from archive import sha
from backfill_rpc import V2, PUBLIC
from dataset import D2Dataset
from pit import AsOfResult, Calendar, FactStore, stamp
from labels import LabelBuilder


class D2BackfillDataset:
    def __init__(self, root=None, manifest=None, baseline=True):
        self.root = Path(root or V2 / "normalized")
        self.manifest = json.loads(
            Path(manifest or PUBLIC / "normalized_manifest.json").read_text()
        )
        self.receipts = {
            r["relative_path"]: r["sha256"] for r in self.manifest["files"]
        }
        self.observed_at = stamp(self.manifest["sealed_at"])
        self._loaded = {}
        self.inventory = self._read("securities.parquet")
        self.aliases = self._read("code_intervals.parquet")
        self.calendar = Calendar(self._read("calendar.parquet").date)
        self.baseline = D2Dataset() if baseline else None
        vp = self.root / "reviewed_facts.parquet"
        if vp.exists():
            f = self._read("reviewed_facts.parquet")
            companion = "reviewed_facts.parquet.manifest.json"
            if sha(self.root / companion) != self.receipts.get(companion):
                raise ValueError("changed reviewed-fact receipt")
            f["value"] = f.value.map(json.loads)
            own_archive = self.root.parent / "raw/sha256"
            if own_archive.exists():
                f["source_path"] = f.source_sha256.map(
                    lambda h: str(own_archive / h[:2] / h)
                )
            self.reviewed = FactStore(f)
        else:
            self.reviewed = FactStore()

    def _read(self, relative):
        path = self.root / relative
        if relative not in self.receipts:
            if path.exists():
                raise ValueError("unsealed partition: " + relative)
            return pd.DataFrame()
        if not path.exists() or sha(path) != self.receipts[relative]:
            raise ValueError("missing or changed sealed partition: " + relative)
        if relative not in self._loaded:
            self._loaded[relative] = pd.read_parquet(path)
        return self._loaded[relative].copy()

    def _security(self, security):
        f = self.inventory[
            self.inventory.security_id.eq(security)
            | self.inventory.instrument.eq(security)
        ]
        if f.empty and len(self.aliases):
            ids = self.aliases.loc[
                self.aliases.historical_instrument.eq(security), "security_id"
            ].unique()
            f = self.inventory[self.inventory.security_id.isin(ids)]
        if len(f) != 1:
            raise ValueError("security must resolve to one stable provisional identity")
        return f.iloc[0]

    def universe_asof(
        self, decision_time, quality_tier="PIT-reconstructed", mode="historical"
    ):
        if quality_tier != "Historical-proxy":
            if self.baseline is None:
                f = pd.DataFrame()
                f.attrs["population_status"] = (
                    "BLOCKED_NOT_CERTIFIED_COMPLETE_HISTORICAL_A_SHARE"
                )
                return f
            return self.baseline.universe_asof(decision_time, quality_tier, mode)
        t = stamp(decision_time)
        if mode not in ("historical", "archived"):
            raise ValueError("invalid as-of mode")
        if mode == "archived" and t < self.observed_at:
            f = self.inventory.iloc[:0].copy()
        else:
            day = t.tz_localize(None).normalize()
            f = self.inventory.copy()
            listing = f.listing_date.where(~f.exchange.eq("BJ"), f.bse_listing_proxy)
            f = f[
                listing.le(day)
                & (f.delist_date.isna() | f.delist_date.gt(day))
                & ~f.identity_date_conflict
            ]
            if len(self.aliases) and len(f):
                a = self.aliases
                a = a[
                    (a.valid_from.isna() | a.valid_from.le(day))
                    & (a.valid_to.isna() | a.valid_to.gt(day))
                ]
                if a.security_id.duplicated().any():
                    raise ValueError("ambiguous historical code intervals")
                f = f.copy()
                f["canonical_instrument"] = f.instrument
                historical = f.security_id.map(
                    a.set_index("security_id").historical_instrument
                )
                f["instrument"] = historical.combine_first(f.instrument)
        f.attrs["population_status"] = (
            "PROVISIONAL_NOT_COMPLETE_HISTORICAL_MEMBERSHIP_BSE_TERMINAL_STATUS_UNPROVEN"
        )
        return f

    def get_asof(
        self,
        security,
        field,
        decision_time,
        quality_tier="PIT-reconstructed",
        mode="historical",
    ):
        row = self._security(security)
        if mode not in ("historical", "archived"):
            raise ValueError("invalid as-of mode")
        if quality_tier not in (
            "PIT-certified",
            "PIT-reconstructed",
            "Historical-proxy",
            "UNKNOWN/BLOCKED",
        ):
            raise ValueError("invalid quality tier")
        known = self.reviewed.get_asof(
            row.security_id, field, decision_time, quality_tier, mode
        )
        if known.records:
            return known
        if self.baseline and field not in (
            "open",
            "high",
            "low",
            "close",
            "volume",
            "money",
            "turnover_rate",
            "total_shares",
        ):
            try:
                result = self.baseline.get_asof(
                    row.security_id, field, decision_time, quality_tier, mode
                )
                if result.records:
                    return result
            except ValueError:
                pass
        if quality_tier != "Historical-proxy":
            return AsOfResult(reason="NEW_VENDOR_HISTORY_NOT_FIRST_VERSION_CERTIFIED")
        t = stamp(decision_time)
        if mode == "archived" and t < self.observed_at:
            return AsOfResult(reason="BACKFILL_NOT_ARCHIVED_BY_DECISION_TIME")
        day = t.tz_localize(None).normalize()
        if field == "code" and row.exchange == "BJ" and len(self.aliases):
            f = self.aliases[self.aliases.security_id.eq(row.security_id)]
            f = f[
                (f.valid_from.isna() | f.valid_from.le(day))
                & (f.valid_to.isna() | f.valid_to.gt(day))
            ]
            if len(f) == 1:
                return AsOfResult(
                    f.iloc[0].historical_instrument[2:],
                    "Historical-proxy",
                    "OFFICIAL_CODE_INTERVAL_MEMBERSHIP_CHECK_SEPARATE",
                    tuple(f.to_dict("records")),
                )
        if field in (
            "open",
            "high",
            "low",
            "close",
            "volume",
            "money",
            "turnover_rate",
            "vendor_trade_status",
            "vendor_is_st",
        ):
            f = self._read(f"prices/{row.security_id}.parquet")
            if f.empty or field not in f:
                return AsOfResult(reason="NO_QUOTE_SOURCE_OR_FIELD")
            f = f[f.date.le(day) if t.hour >= 15 else f.date.lt(day)]
            if f.empty:
                return AsOfResult()
            selected = f.sort_values("date").iloc[-1]
            if bool(selected.get(field + "_conflict", False)):
                return AsOfResult(
                    reason="UNRESOLVED_SOURCE_CONFLICT",
                    records=tuple(f.tail(1).to_dict("records")),
                )
            value = selected[field]
            if pd.isna(value):
                return AsOfResult(reason="FIELD_UNKNOWN_AT_LATEST_OBSERVATION")
            return AsOfResult(
                value,
                "Historical-proxy",
                "RETROSPECTIVE_VENDOR_VALUE_NO_EXECUTION_CERTIFICATION",
                tuple(f.tail(1).to_dict("records")),
            )
        if field == "total_shares":
            f = self._read(f"shares/{row.security_id}.parquet")
            if f.empty:
                return AsOfResult(reason="NO_SHARE_HISTORY_SOURCE")
            f = f[f.effective_date.le(day)]
            if f.empty:
                return AsOfResult(reason="NO_EFFECTIVE_SHARE_BASELINE")
            f = f[f.effective_date.eq(f.effective_date.max())]
            if f.total_shares.nunique(dropna=False) != 1:
                return AsOfResult(
                    reason="UNRESOLVED_SHARE_SOURCE_CONFLICT",
                    records=tuple(f.to_dict("records")),
                )
            value = f.iloc[0].total_shares
            return AsOfResult(
                None if pd.isna(value) else value,
                "Historical-proxy",
                "EFFECTIVE_DATE_KNOWN_FIRST_PUBLICATION_UNPROVEN",
                tuple(f.to_dict("records")),
            )
        if field in (
            "vendor_pe_ttm",
            "vendor_pb_mrq",
            "vendor_ps_ttm",
            "vendor_pcf_ncf_ttm",
        ):
            f = self._read("vendor_valuations.parquet")
            f = f[f.instrument.eq(row.instrument)]
            f = f[f.date.le(day) if t.hour >= 15 else f.date.lt(day)]
            if f.empty:
                return AsOfResult(reason="NO_VENDOR_VALUATION_HISTORY")
            selected = f.sort_values("date").tail(1)
            value = selected.iloc[0][field]
            return AsOfResult(
                None if pd.isna(value) else value,
                "Historical-proxy",
                "VENDOR_DENOMINATOR_VINTAGE_UNPROVEN",
                tuple(selected.to_dict("records")),
            )
        if field.startswith("financial:"):
            return AsOfResult(
                reason="ORIGINAL_PDF_EXTRACTION_CANDIDATE_REQUIRES_REVIEW"
            )
        if field in ("can_buy", "can_sell"):
            return AsOfResult(reason="EXECUTION_EVIDENCE_UNPROVEN")
        return AsOfResult(reason="UNSUPPORTED_OR_UNCERTIFIED_FIELD")

    def price_and_corporate_action_path(self, security, start, end, policy="price"):
        if policy not in ("price", "total", "executable"):
            raise ValueError("invalid return policy")
        row = self._security(security)
        bars = self._read(f"prices/{row.security_id}.parquet")
        if len(bars):
            bars = bars[bars.date.between(start, end)]
        actions = self._read("corporate_actions.parquet")
        actions = actions[
            actions.security_id.eq(row.security_id)
            & actions.ex_date.between(start, end)
        ]
        rights = self._read("rights_issues.parquet")
        rights = rights[
            rights.security_id.eq(row.security_id) & rights.ex_date.between(start, end)
        ]
        return dict(
            bars=bars,
            actions=actions,
            rights_issues=rights,
            policy=policy,
            rights_coverage_verified=False,
            execution_coverage_verified=False,
            status="HISTORICAL_PROXY_ACTUAL_PAYMENT_AND_EXECUTION_PENDING",
        )

    def build_labels(self, security, origin, horizon, return_policy="price"):
        row = self._security(security)
        bars = self._read(f"prices/{row.security_id}.parquet")
        if bars.empty:
            bars = pd.DataFrame(
                columns=["security_id", "date", "open", "close", "can_buy", "can_sell"]
            )
        # The common label contract rejects unknown next-session execution before
        # any NAV calculation. No vendor-adjusted price becomes cash settlement.
        return LabelBuilder(self.calendar, bars).build_labels(
            row.security_id, origin, horizon, return_policy
        )

    def snapshot_manifest(self, asof_time):
        if stamp(asof_time) < self.observed_at:
            return dict(
                status="UNAVAILABLE", reason="BACKFILL_NOT_ARCHIVED_BY_REQUESTED_TIME"
            )
        return self.manifest.copy()
