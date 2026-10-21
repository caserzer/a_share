"""Read-only lazy D2 Parquet adapter. Explicit opt-in for diagnostic proxy queries."""

from pathlib import Path
import json
import pandas as pd
from archive import EP, CACHE, sha
from pit import AsOfResult, FactStore, Calendar, stamp
from labels import LabelBuilder


class D2Dataset:
    def __init__(self, root=CACHE, manifests=None):
        self.root = Path(root)
        self.manifests = Path(manifests or EP / "outputs/manifests")
        f = pd.read_csv(self.manifests / "local_cache_manifest.csv")
        self.receipts = {
            str(self.root / r.relative_path)
            if hasattr(r, "relative_path")
            else str(Path(r.path)): r.sha256
            for r in f.itertuples()
        }
        self.observed_at = stamp(
            json.loads((self.manifests.parent / "audits/validation.json").read_text())[
                "source_observed_at"
            ]
        )
        domain_sources = pd.read_csv(
            self.manifests.parent / "audits/domain_file_inventory.csv"
        )
        self.domain_sources = {
            (r.domain, r.file): r.source_sha256 for r in domain_sources.itertuples()
        }
        self._loaded = {}
        self.identity = FactStore.from_parquet(
            self.root / "identity/facts.parquet", archive_root=self.root / "raw/sha256"
        )
        self.inventory = self._read(self.root / "identity/security_inventory.parquet")
        vp = self.root / "vintages/facts.parquet"
        self.vintages = (
            FactStore.from_parquet(vp, archive_root=self.root / "raw/sha256")
            if vp.exists()
            else FactStore()
        )
        # The calendar is the audited input, not a generated weekday approximation.
        from archive import TOPIC

        frozen_calendar = self.root / "calendar/sessions.parquet"
        if frozen_calendar.exists():
            self.calendar = Calendar(self._read(frozen_calendar).date)
        else:
            cal = TOPIC / "data/qlib/cn_data_pit_largecap/calendars/day.txt"
            self.calendar = Calendar(pd.read_csv(cal, header=None)[0])

    def _read(self, path):
        path = Path(path)
        if not path.exists():
            return pd.DataFrame()
        expected = self.receipts.get(str(path))
        if expected is None or sha(path) != expected:
            raise ValueError("missing receipt or altered D2 partition: " + str(path))
        if str(path) not in self._loaded:
            self._loaded[str(path)] = pd.read_parquet(path)
        return self._loaded[str(path)].copy()

    def _proxy_records(self, frame, columns, path, domain, unit):
        return tuple(
            {
                **record,
                "source_uri": f"legacy_EP24/{domain}/{path.name}",
                "source_sha256": self.domain_sources.get((domain, path.name)),
                "partition_path": str(path),
                "partition_sha256": self.receipts[str(path)],
                "original_version": "UNPROVEN_VENDOR_RETROSPECTIVE_VERSION",
                "known_at": None,
                "source_observed_at": str(self.observed_at),
                "unit": unit,
            }
            for record in frame[columns].to_dict("records")
        )

    def _security(self, security):
        f = self.inventory[
            self.inventory.security_id.eq(security)
            | self.inventory.instrument.eq(security)
        ]
        if len(f) != 1:
            raise ValueError(
                "security must resolve to one listing episode; code reuse needs explicit id"
            )
        return f.iloc[0]

    def universe_asof(
        self, decision_time, quality_tier="PIT-reconstructed", mode="historical"
    ):
        frame = self.identity.universe_asof(decision_time, quality_tier, mode)
        frame.attrs["population_status"] = (
            "BLOCKED_NOT_CERTIFIED_COMPLETE_HISTORICAL_A_SHARE"
        )
        return frame

    def get_asof(
        self,
        security,
        field,
        decision_time,
        quality_tier="PIT-reconstructed",
        mode="historical",
    ):
        row = self._security(security)
        reconstructed = self.vintages.get_asof(
            row.security_id, field, decision_time, quality_tier, mode
        )
        if reconstructed.records:
            return reconstructed
        if field in (
            "listed",
            "code",
            "name",
            "exchange",
            "board",
            "is_st",
            "can_buy",
            "can_sell",
        ):
            return self.identity.get_asof(
                row.security_id, field, decision_time, quality_tier, mode
            )
        if mode not in ("historical", "archived"):
            raise ValueError("unknown as-of mode")
        if quality_tier != "Historical-proxy":
            return AsOfResult(reason="FIRST_VERSION_OR_EXECUTION_EVIDENCE_UNCERTIFIED")
        t = stamp(decision_time)
        if mode == "archived" and t < self.observed_at:
            return AsOfResult(reason="NOT_ARCHIVED_BY_DECISION_TIME")
        day = t.tz_localize(None).normalize()
        if field in (
            "open",
            "high",
            "low",
            "close",
            "volume",
            "money",
            "turnover_rate",
        ):
            f = self._read(self.root / f"prices/{row.security_id}.parquet")
            if f.empty or field not in f:
                return AsOfResult(reason="SOURCE_FAILURE_OR_UNSUPPORTED_FIELD")
            # A daily bar is not available during the same session under this contract.
            f = f[f.date.le(day) if t.hour >= 15 else f.date.lt(day)]
            if f.empty:
                return AsOfResult()
            selected = f.sort_values("date").iloc[-1]
            value = selected[field]
            return AsOfResult(
                None if pd.isna(value) else value,
                "Historical-proxy",
                "RETROSPECTIVE_QUOTE_NO_FIRST_VINTAGE",
                (
                    {
                        "date": str(selected.date),
                        "source_sha256": selected.source_sha256,
                        "partition": str(
                            self.root / f"prices/{row.security_id}.parquet"
                        ),
                        "unit": "shares"
                        if field == "volume"
                        else "ratio"
                        if field == "turnover_rate"
                        else "CNY",
                        "known_at": None,
                        "source_observed_at": str(self.observed_at),
                    },
                ),
            )
        if field == "total_shares":
            f = self._read(self.root / f"shares/{row.security_id}.parquet")
            if f.empty:
                return AsOfResult(reason="NO_SHARE_HISTORY_SOURCE")
            f = f[f.effective_date.le(day)]
            if f.empty:
                return AsOfResult()
            f = f[f.effective_date.eq(f.effective_date.max())]
            if f.total_shares.nunique(dropna=False) != 1:
                return AsOfResult(reason="UNRESOLVED_SHARE_SOURCE_CONFLICT")
            value = f.iloc[0].total_shares
            return AsOfResult(
                None if pd.isna(value) else value,
                "Historical-proxy",
                "EFFECTIVE_DATE_ONLY_PUBLICATION_UNPROVEN",
                tuple(f.to_dict("records")),
            )
        if field.startswith("financial:"):
            # Period explicit: correction to an older report cannot replace a newer report.
            _, name, period = field.split(":")
            path = (
                self.root
                / f"proxy/financials/{row.instrument[2:]}.{row.exchange}.parquet"
            )
            f = self._read(path)
            if f.empty or name not in f:
                return AsOfResult(reason="FINANCIAL_FIELD_OR_SOURCE_ABSENT")
            f = f[pd.to_datetime(f.REPORT_DATE).eq(pd.Timestamp(period))].copy()
            # These are vendor availability hints, never certified first disclosure.
            hint = (
                f[["NOTICE_DATE", "UPDATE_DATE"]]
                .apply(pd.to_datetime, errors="coerce")
                .max(axis=1)
            )
            available = hint.map(
                lambda x: self.calendar.publication_time(x) if pd.notna(x) else pd.NaT
            )
            f = f[available.le(t)].copy()
            if f.empty:
                return AsOfResult(
                    reason="NO_VENDOR_VERSION_ELIGIBLE_OR_CALENDAR_BLOCKED"
                )
            f["_hint"] = hint.loc[f.index]
            f = f[f._hint.eq(f._hint.max())]
            if f[name].nunique(dropna=False) != 1:
                return AsOfResult(reason="UNRESOLVED_FINANCIAL_VERSION_CONFLICT")
            value = f.iloc[0][name]
            return AsOfResult(
                None if pd.isna(value) else value,
                "Historical-proxy",
                "VENDOR_NOTICE_UPDATE_HINT_NOT_FIRST_VERSION",
                self._proxy_records(
                    f,
                    ["REPORT_DATE", "NOTICE_DATE", "UPDATE_DATE", name],
                    path,
                    "financials",
                    {
                        "EPSJB": "CNY/share",
                        "BPS": "CNY/share",
                        "PARENTNETPROFIT": "CNY",
                        "TOTALOPERATEREVE": "CNY",
                        "ROEJQ": "percent",
                        "ZCFZL": "percent",
                        "MGJYXJJE": "CNY/share",
                    }.get(name, "UNKNOWN_UNIT"),
                ),
            )
        if field.startswith("valuation:"):
            name = field.split(":")[1]
            path = self.root / f"proxy/valuation/{row.instrument[2:]}.parquet"
            f = self._read(path)
            if f.empty or name not in f:
                return AsOfResult(reason="VALUATION_FIELD_OR_SOURCE_ABSENT")
            dates = pd.to_datetime(f.TRADE_DATE)
            f = f[dates.le(day) if t.hour >= 15 else dates.lt(day)].copy()
            if f.empty:
                return AsOfResult()
            f = f[pd.to_datetime(f.TRADE_DATE).eq(pd.to_datetime(f.TRADE_DATE).max())]
            if f[name].nunique(dropna=False) != 1:
                return AsOfResult(reason="UNRESOLVED_VALUATION_SOURCE_CONFLICT")
            value = f.iloc[0][name]
            return AsOfResult(
                None if pd.isna(value) else value,
                "Historical-proxy",
                "VENDOR_HISTORICAL_VALUE_NOT_CERTIFIED_FIRST_VINTAGE",
                self._proxy_records(
                    f,
                    [name, "TRADE_DATE"],
                    path,
                    "valuation",
                    {
                        "PE_TTM": "ratio",
                        "PB_MRQ": "ratio",
                        "PS_TTM": "ratio",
                        "TOTAL_MARKET_CAP": "CNY",
                        "CLOSE_PRICE": "CNY/share",
                        "TOTAL_SHARES": "shares",
                    }.get(name, "UNKNOWN_UNIT"),
                ),
            )
        return AsOfResult(reason="FIELD_NOT_CERTIFIED_OR_ADAPTER_UNSUPPORTED")

    def price_and_corporate_action_path(self, security, start, end, policy="total"):
        row = self._security(security)
        bars = self._read(self.root / f"prices/{row.security_id}.parquet")
        if bars.empty:
            bars = pd.DataFrame(columns=["security_id", "date"])
        builder = LabelBuilder(self.calendar, bars)
        result = builder.price_and_corporate_action_path(
            row.security_id, start, end, policy
        )
        result["rights_status"] = (
            "BLOCKED_SOURCE_PAGES_ARE_NOT_A_COMPLETE_POSITION_RIGHTS_LEDGER"
        )
        return result

    def build_labels(
        self,
        security,
        origin,
        horizon,
        return_policy="total",
        asof_time=None,
        cost_bps=None,
    ):
        row = self._security(security)
        bars = self._read(self.root / f"prices/{row.security_id}.parquet")
        if bars.empty:
            bars = pd.DataFrame(columns=["security_id", "date"])
        return LabelBuilder(self.calendar, bars).build_labels(
            row.security_id, origin, horizon, return_policy, asof_time, cost_bps
        )

    def snapshot_manifest(self, asof_time, mode="archived"):
        result = self.identity.snapshot_manifest(asof_time, mode)
        result["financial_vintage_manifest"] = self.vintages.snapshot_manifest(
            asof_time, mode
        )
        result.update(
            configuration_sha256={
                p.name: sha(p)
                for p in sorted((self.manifests.parents[1] / "configs").glob("*.yaml"))
            },
            code_sha256={
                p.name: sha(p)
                for p in sorted((self.manifests.parents[1] / "src").glob("*.py"))
            },
            cache_manifest_sha256=sha(self.manifests / "local_cache_manifest.csv"),
            coverage_status="BLOCKED_FULL_MARKET_PIT",
        )
        return result
