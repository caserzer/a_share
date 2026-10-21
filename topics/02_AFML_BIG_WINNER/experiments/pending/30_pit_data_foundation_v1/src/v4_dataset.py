"""Sealed v4 extension reader; identity continuity is not daily trade permission."""

import json
from pathlib import Path

import pandas as pd
import numpy as np

from archive import sha
from pit import AsOfResult, FactStore, stamp
from v3_bridge import HORIZONS, POLICIES


class D2V4Dataset:
    def __init__(self, release, baseline_release=None):
        self.root = Path(release)
        complete = json.loads((self.root / "COMPLETE.json").read_text())
        manifest = self.root / "FULL_MANIFEST.json"
        if sha(manifest) != complete["full_manifest_sha256"]:
            raise ValueError("changed v4 manifest")
        self.files = {
            r["relative_path"]: r["sha256"] for r in json.loads(manifest.read_text())
        }
        self.observed_at = stamp(complete["sealed_at"])
        self.inventory = self._read("normalized/securities.parquet")
        self.redirects = self._read("normalized/security_id_redirects.parquet")
        self.intervals = self._read("normalized/code_intervals.parquet")
        self.finance = self._facts("normalized/financial_reviewed_facts.parquet")
        self.states = self._facts("normalized/status_reviewed_facts.parquet")
        self.aliases = self._facts("normalized/alias_facts.parquet")
        self.code_changes = self._facts("normalized/code_change_facts.parquet")
        self.prior_finance = self._facts(
            "inputs/normalized/financial_reviewed_facts.parquet"
        )
        self.base = None
        if baseline_release is not None:
            from v3_dataset import D2V3Dataset

            self.base = D2V3Dataset(baseline_release)

    def _read(self, name):
        p = self.root / name
        if name not in self.files or not p.exists() or sha(p) != self.files[name]:
            raise ValueError("missing or changed sealed v4 input: " + name)
        return pd.read_parquet(p)

    def _facts(self, name):
        f = self._read(name)
        f["value"] = f.value.map(json.loads)
        f["source_path"] = f.source_sha256.map(
            lambda h: str(self.root / "raw/sha256" / h[:2] / h)
        )
        return FactStore(f)

    def _sid(self, security):
        lookup = dict(
            zip(self.redirects.legacy_security_id, self.redirects.canonical_security_id)
        )
        security = lookup.get(security, security)
        if security in set(self.inventory.security_id):
            return security
        match = self.inventory[
            self.inventory.instrument.eq(security)
            | self.inventory.metadata_instrument_v3.eq(security)
        ]
        if len(match) == 1:
            return match.iloc[0].security_id
        codes = self.intervals[self.intervals.instrument.eq(security)]
        if codes.security_id.nunique() == 1:
            return codes.iloc[0].security_id
        raise KeyError("unknown or ambiguous security identity: " + str(security))

    def get_asof(
        self,
        security,
        field,
        decision_time,
        quality_tier="PIT-reconstructed",
        mode="historical",
    ):
        sid = self._sid(security)
        stores = [
            self.finance,
            self.prior_finance,
            self.states,
            self.aliases,
            self.code_changes,
        ]
        for store in stores:
            if (store.facts.security_id.eq(sid) & store.facts.field.eq(field)).any():
                result = store.get_asof(sid, field, decision_time, quality_tier, mode)
                if result.value is not None:
                    if isinstance(result.value, np.bool_):
                        return AsOfResult(
                            bool(result.value),
                            result.status,
                            result.reason,
                            result.records,
                        )
                    return result
        if field == "trading_code":
            t = stamp(decision_time)
            f = self.intervals[self.intervals.security_id.eq(sid)]
            if mode == "archived" and t < self.observed_at:
                return AsOfResult(reason="V4_NOT_ARCHIVED_AT_DECISION")
            for r in f.to_dict("records"):
                if t < stamp(r["valid_from"]) or (
                    r["valid_until_exclusive"] is not None
                    and not pd.isna(r["valid_until_exclusive"])
                    and t >= stamp(r["valid_until_exclusive"])
                ):
                    continue
                if quality_tier != "Historical-proxy" and t < stamp(
                    r["boundary_known_at"]
                ):
                    return AsOfResult(reason="CODE_BOUNDARY_NOT_YET_ATTESTED")
                return AsOfResult(
                    r["instrument"],
                    (
                        "Historical-proxy"
                        if quality_tier == "Historical-proxy"
                        else "PIT-reconstructed"
                    ),
                    "IDENTITY_ONLY_NO_EXECUTION_ATTESTATION",
                    (r,),
                )
        if field in {"open", "high", "low", "close", "volume", "money"}:
            if quality_tier != "Historical-proxy":
                return AsOfResult(
                    reason="RETROSPECTIVE_QUOTE_NOT_FIRST_VINTAGE_OR_OPEN_FILL"
                )
            t = stamp(decision_time)
            if mode == "archived" and t < self.observed_at:
                return AsOfResult(reason="V4_NOT_ARCHIVED_AT_DECISION")
            name = f"normalized/prices/{sid}.parquet"
            if name not in self.files:
                name = f"inputs/baseline/normalized/prices/{sid}.parquet"
            if name not in self.files:
                return AsOfResult(reason="MISSING_QUOTES")
            f = self._read(name)
            day = t.tz_localize(None).normalize()
            f = f[f.date.le(day) if t.hour >= 15 else f.date.lt(day)]
            if f.empty:
                return AsOfResult(reason="MISSING_QUOTES")
            row = f.sort_values("date").iloc[-1]
            if row.get(field + "_conflict", False):
                return AsOfResult(reason="UNRESOLVED_SOURCE_CONFLICT")
            return AsOfResult(
                None if pd.isna(row[field]) else row[field],
                "Historical-proxy",
                "NO_OPEN_EXECUTION_ATTESTATION",
                (row.to_dict(),),
            )
        if self.base is not None:
            if field == "listed" and sid in set(self.redirects.canonical_security_id):
                return AsOfResult(
                    reason="CONTINUOUS_CODE_CHANGE_NOT_DELISTING_DAILY_QUALIFICATION_UNATTESTED"
                )
            return self.base.get_asof(sid, field, decision_time, quality_tier, mode)
        return AsOfResult(reason="V4_EXTENSION_FIELD_NOT_ATTESTED_OR_NOT_YET_KNOWN")

    def universe_asof(
        self, decision_time, quality_tier="PIT-reconstructed", mode="historical"
    ):
        t = stamp(decision_time)
        if quality_tier != "Historical-proxy" or (
            mode == "archived" and t < self.observed_at
        ):
            f = self.inventory.iloc[:0].copy()
            f.attrs["population_status"] = "DAILY_QUALIFICATION_NOT_ATTESTED"
            return f
        day = t.tz_localize(None).normalize()
        start = self.inventory.listing_date.combine_first(
            pd.to_datetime(self.inventory.bse_listing_proxy)
        )
        f = self.inventory[
            start.le(day)
            & (self.inventory.delist_date.isna() | self.inventory.delist_date.gt(day))
        ].copy()
        for r in self.redirects.itertuples():
            f.loc[f.security_id.eq(r.canonical_security_id), "instrument"] = (
                r.old_instrument
                if day < pd.Timestamp(r.effective_date)
                else r.new_instrument
            )
        f.attrs["population_status"] = (
            "PROVISIONAL_IDENTITY_CORRECTED_NOT_QUALIFICATION_CERTIFIED"
        )
        return f

    def build_labels(
        self, security, origin, horizon, return_policy, observable_at="2026-10-21 15:00"
    ):
        horizon = str(horizon) + "_sessions" if isinstance(horizon, int) else horizon
        if horizon not in HORIZONS or return_policy not in POLICIES:
            raise ValueError("invalid label contract")
        sid = self._sid(security)
        f = self._read(f"normalized/labels/{horizon}/{return_policy}.parquet")
        day = stamp(origin).tz_localize(None).normalize()
        f = f[f.security_id.eq(sid) & f.date.eq(day)]
        if len(f) != 1:
            return dict(
                status="UNKNOWN", reason="NO_CANONICAL_MONTHLY_ORIGIN", value=None
            )
        row = f.iloc[0].to_dict()
        for k in ["value", "loss_below_minus20", "mfe", "mae", "execution_cost_bps"]:
            if pd.isna(row[k]):
                row[k] = None
        if (
            pd.isna(row["target_session"])
            or row["target_session"]
            > stamp(observable_at).tz_localize(None).normalize()
        ):
            row.update(
                status="CENSORED", reason="TARGET_NOT_YET_OBSERVABLE", value=None
            )
        return row

    def price_and_corporate_action_path(self, security, start, end, policy):
        if policy not in POLICIES:
            raise ValueError("invalid return policy")
        sid = self._sid(security)
        name = f"normalized/prices/{sid}.parquet"
        if name not in self.files:
            name = f"inputs/baseline/normalized/prices/{sid}.parquet"
        bars = self._read(name) if name in self.files else pd.DataFrame()
        if len(bars):
            bars = bars[bars.date.between(start, end)]
        contracts = self._read(
            "inputs/normalized/original_distribution_contracts.parquet"
        )
        redirect = dict(
            zip(self.redirects.legacy_security_id, self.redirects.canonical_security_id)
        )
        contracts = contracts[
            contracts.security_id.map(lambda x: redirect.get(x, x)).eq(sid)
        ]
        contracts = contracts[pd.to_datetime(contracts.ex_date).between(start, end)]
        return dict(
            bars=bars,
            original_contracts=contracts,
            code_changes=self.redirects[self.redirects.canonical_security_id.eq(sid)],
            policy=policy,
            rights_coverage_verified=False,
            original_contract_schedules_are_not_actual_receipts=True,
            reason="FULL_INTERVAL_RIGHTS_AND_EXECUTION_UNATTESTED",
        )

    def snapshot_manifest(self, asof_time=None):
        if asof_time is not None and stamp(asof_time) < self.observed_at:
            return dict(
                status="UNKNOWN",
                files={},
                reason="V4_SEAL_NOT_OBSERVED_AT_REQUESTED_TIME",
            )
        return dict(
            files=self.files,
            strict_proxy_separation=True,
            canonical_identity_not_daily_eligibility=True,
        )
