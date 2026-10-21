"""Read-only sealed v3 adapter. Partial event evidence is not full daily status."""

import json
from pathlib import Path
import pandas as pd
from archive import sha
from pit import AsOfResult, FactStore, stamp
from backfill_dataset import D2BackfillDataset
from v3_bridge import HORIZONS, POLICIES


class D2V3Dataset:
    def __init__(self, release):
        self.root = Path(release)
        complete = json.loads((self.root / "COMPLETE.json").read_text())
        manifest = self.root / "FULL_MANIFEST.json"
        if sha(manifest) != complete["full_manifest_sha256"]:
            raise ValueError("changed v3 release manifest")
        records = json.loads(manifest.read_text())
        self.files = {r["relative_path"]: r["sha256"] for r in records}
        nested = "baseline/provenance/normalized_manifest.json"
        if sha(self.root / nested) != self.files.get(nested):
            raise ValueError("changed frozen baseline manifest")
        self.base = D2BackfillDataset(
            self.root / "baseline/normalized",
            self.root / "baseline/provenance/normalized_manifest.json",
            baseline=False,
        )
        self.base.inventory = self._read("normalized/securities.parquet")
        self.observed_at = stamp(complete["sealed_at"])
        self.status = self._facts("normalized/status_facts.parquet")
        self.financial = self._facts("normalized/financial_reviewed_facts.parquet")

    def _read(self, name):
        path = self.root / name
        if name not in self.files or not path.exists() or sha(path) != self.files[name]:
            raise ValueError("missing or changed sealed v3 partition: " + name)
        return pd.read_parquet(path)

    def _facts(self, name):
        if name not in self.files:
            return FactStore()
        frame = self._read(name)
        frame["value"] = frame.value.map(json.loads)
        frame["source_path"] = frame.source_sha256.map(
            lambda h: str(self.root / "raw/sha256" / h[:2] / h)
        )
        return FactStore(frame)

    def get_asof(
        self,
        security,
        field,
        decision_time,
        quality_tier="PIT-reconstructed",
        mode="historical",
    ):
        sid = self.base._security(security).security_id
        partition = f"normalized/prices/{sid}.parquet"
        if (
            field in {"open", "high", "low", "close", "volume", "money"}
            and partition in self.files
        ):
            if quality_tier != "Historical-proxy":
                return AsOfResult(
                    reason="CURRENT_EXCHANGE_HISTORY_NOT_FIRST_VERSION_CERTIFIED"
                )
            t = stamp(decision_time)
            if mode == "archived" and t < self.observed_at:
                return AsOfResult(reason="V3_SOURCE_NOT_ARCHIVED_AT_DECISION")
            frame = self._read(partition)
            day = t.tz_localize(None).normalize()
            frame = frame[frame.date.le(day) if t.hour >= 15 else frame.date.lt(day)]
            if frame.empty:
                return AsOfResult()
            row = frame.sort_values("date").iloc[-1]
            records = (row.to_dict(),)
            if row.get(field + "_conflict", False):
                return AsOfResult(reason="UNRESOLVED_SOURCE_CONFLICT", records=records)
            return AsOfResult(
                None if pd.isna(row[field]) else row[field],
                "Historical-proxy",
                "EXCHANGE_AND_VENDOR_OBSERVATIONS_NOT_OPEN_FILL_CERTIFICATION",
                records,
            )
        if field in {
            "suspended",
            "is_st",
            "delisting_risk_warning",
            "other_risk_warning",
        }:
            event = self.status.get_asof(sid, field, decision_time, quality_tier, mode)
            return AsOfResult(
                reason="FULL_DAILY_STATUS_COVERAGE_UNATTESTED", records=event.records
            )
        if field == "listed":
            event = self.status.get_asof(sid, field, decision_time, quality_tier, mode)
            if event.records and event.value is not None and not bool(event.value):
                return AsOfResult(False, event.status, event.reason, event.records)
            if event.records:
                return AsOfResult(
                    reason="POSITIVE_MEMBERSHIP_OR_EVENT_CONFLICT_REQUIRES_EPISODE_REVIEW",
                    records=event.records,
                )
        result = self.financial.get_asof(sid, field, decision_time, quality_tier, mode)
        if result.records:
            return result
        return self.base.get_asof(security, field, decision_time, quality_tier, mode)

    def latest_status_event(self, security, field, decision_time, mode="historical"):
        sid = self.base._security(security).security_id
        event = self.status.get_asof(
            sid, field, decision_time, "PIT-reconstructed", mode
        )
        return AsOfResult(
            reason="EVENT_ONLY_CONTINUOUS_STATE_COVERAGE_UNATTESTED",
            records=event.records,
        )

    def universe_asof(
        self, decision_time, quality_tier="PIT-reconstructed", mode="historical"
    ):
        if mode == "archived" and stamp(decision_time) < self.observed_at:
            empty = self.base.inventory.iloc[:0].copy()
            empty.attrs["population_status"] = (
                "V3_COMPLETE_SNAPSHOT_NOT_OBSERVED_AT_DECISION"
            )
            return empty
        return self.base.universe_asof(decision_time, quality_tier, mode)

    def build_labels(
        self, security, origin, horizon, return_policy, observable_at="2026-10-21 15:00"
    ):
        horizon = str(horizon) + "_sessions" if isinstance(horizon, int) else horizon
        if horizon not in HORIZONS or return_policy not in POLICIES:
            raise ValueError("invalid horizon or return policy")
        sid = self.base._security(security).security_id
        f = self._read(f"normalized/labels/{horizon}/{return_policy}.parquet")
        day = stamp(origin).tz_localize(None).normalize()
        f = f[f.security_id.eq(sid) & f.date.eq(day)]
        if len(f) != 1:
            return dict(
                status="UNKNOWN",
                reason="NO_MONTHLY_POPULATION_LABEL_AT_ORIGIN",
                value=None,
            )
        row = f.iloc[0].to_dict()
        for field in [
            "value",
            "loss_below_minus20",
            "mfe",
            "mae",
            "execution_cost_bps",
        ]:
            if field in row and pd.isna(row[field]):
                row[field] = None
        limit = stamp(observable_at).tz_localize(None).normalize()
        if pd.isna(row["target_session"]) or row["target_session"] > limit:
            row.update(
                status="CENSORED", reason="TARGET_NOT_YET_OBSERVABLE", value=None
            )
        return row

    def price_and_corporate_action_path(self, security, start, end, policy):
        if policy not in POLICIES:
            raise ValueError("invalid return policy")
        row = self.base._security(security)
        sid = row.security_id
        partition = f"normalized/prices/{sid}.parquet"
        bars = (
            self._read(partition)
            if partition in self.files
            else self.base._read(f"prices/{sid}.parquet")
        )
        if len(bars):
            bars = bars[bars.date.between(start, end)]
        original = self._read("normalized/original_distribution_contracts.parquet")
        original = original[
            original.security_id.eq(sid)
            & pd.to_datetime(original.ex_date).between(start, end)
        ]
        return dict(
            bars=bars,
            original_contracts=original,
            original_contract_schedules_are_not_actual_receipts=True,
            policy=policy,
            rights_coverage_verified=False,
            reason="FULL_INTERVAL_RIGHTS_AND_EXECUTION_UNATTESTED",
        )

    def snapshot_manifest(self, asof_time=None):
        if asof_time is not None and stamp(asof_time) < self.observed_at:
            return dict(
                status="UNKNOWN",
                files={},
                reason="FROZEN_V3_SNAPSHOT_NOT_OBSERVED_BY_REQUESTED_TIME",
            )
        return dict(
            files=self.files,
            strict_proxy_separation=True,
            partial_events_do_not_attest_complete_status=True,
        )
