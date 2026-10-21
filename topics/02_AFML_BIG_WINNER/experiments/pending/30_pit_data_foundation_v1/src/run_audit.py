"""Deterministic EP30 census and D0/D1/D2 bridge. Never writes upstream files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import uuid

import numpy as np
import pandas as pd

from archive import EP, TOPIC, CACHE, sha, utc_now, write_json, verify_receipt
from pit import COLUMNS, FactStore

OUT = EP / "outputs"
AUDIT = OUT / "audits"
MAN = OUT / "manifests"
PENDING = EP.parent
EP01 = next(PENDING.glob("01_*"))
EP05 = next(PENDING.glob("05_*"))
EP24 = next(PENDING.glob("24_*"))
EP28 = next(PENDING.glob("28_*"))
START = pd.Timestamp("2017-01-03")
END = pd.Timestamp(
    "2026-05-29"
)  # legacy verified observation window, never the request cutoff


def sid(exchange, code, listing):
    # A listing-episode ID is stable inside D2. Cross-code issuer continuity is separately blocked.
    return (
        "D2-"
        + uuid.uuid5(uuid.NAMESPACE_URL, f"cn-security/{exchange}/{code}/{listing}").hex
    )


def bounds(frame, actual="actual", end="label_end"):
    f = frame[frame[end].notna()]
    known = f[actual].notna()
    n, k = len(f), int(known.sum())
    events = int(f.loc[known, actual].lt(-0.2).sum())
    return dict(
        origins=len(frame),
        mature=n,
        known=k,
        missing=n - k,
        censored=len(frame) - n,
        events=events,
        rate_known=events / k if k else None,
        rate_lower=events / n if n else None,
        rate_upper=(events + n - k) / n if n else None,
    )


class Audit:
    def __init__(self):
        AUDIT.mkdir(parents=True, exist_ok=True)
        MAN.mkdir(parents=True, exist_ok=True)
        CACHE.mkdir(parents=True, exist_ok=True)
        self.sources = {}
        self.products = []
        self.now = utc_now()
        self.transform = sha(Path(__file__))
        self.freeze = json.loads((MAN / "p0_freeze.json").read_text())
        for name, digest in self.freeze["files"].items():
            if sha(EP / name) != digest:
                raise ValueError("P0 frozen contract changed: " + name)

    def register(self, path, domain, tier="Historical-proxy"):
        path = Path(path).resolve()
        key = str(path)
        if key not in self.sources:
            self.sources[key] = dict(
                path=str(path.relative_to(TOPIC))
                if path.is_relative_to(TOPIC)
                else key,
                sha256=sha(path),
                bytes=path.stat().st_size,
                domain=domain,
                quality_tier=tier,
                observed_by_EP30_at=self.now,
                historical_known_at=None,
                license="raw_redistribution_not_authorized",
                cache_policy="local_only_preserve_bytes",
            )
        return self.sources[key]["sha256"]

    def parquet(self, frame, relative, domain):
        path = CACHE / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(path, index=False)
        self.products.append(
            dict(
                path=str(path),
                sha256=sha(path),
                bytes=path.stat().st_size,
                rows=len(frame),
                domain=domain,
                quality_tier="Historical-proxy",
            )
        )
        return path

    def csv(self, frame, name):
        frame.to_csv(AUDIT / name, index=False)

    def load_identity(self):
        p = TOPIC / "data/raw/akshare/status/instrument_metadata_target_universe.csv"
        self.meta_sha = self.register(p, "identity")
        self.meta_source = p
        self.meta = pd.read_csv(
            p, dtype={"code": str}, parse_dates=["listing_date", "delist_date"]
        )
        if self.meta.instrument.duplicated().any():
            raise ValueError(
                "legacy code reuse needs explicit listing episode resolution"
            )
        self.meta["security_id"] = [
            sid(r.exchange, r.code, str(r.listing_date.date()))
            for r in self.meta.itertuples()
        ]
        cal = TOPIC / "data/qlib/cn_data_pit_largecap/calendars/day.txt"
        self.register(cal, "calendar")
        self.calendar = pd.DatetimeIndex(
            pd.to_datetime(pd.read_csv(cal, header=None)[0])
        )
        if self.calendar[-1] != END or self.calendar[0] != START:
            raise ValueError("legacy cutoff drift: review date configuration")
        self.discovery = []
        receipts = AUDIT / "source_attempts.jsonl"
        if receipts.exists():
            for line in receipts.read_text().splitlines():
                receipt = json.loads(line)
                if receipt.get("sha256") and not verify_receipt(receipt):
                    raise ValueError("source archive verification failed")
                self.discovery.append(receipt)
        extra, reconciliation = [], []
        for receipt in self.discovery:
            if not receipt.get("parsed_path") or not receipt["source_id"].startswith(
                "sse_"
            ):
                continue
            frame = pd.read_parquet(receipt["parsed_path"])
            for r in frame.to_dict("records"):
                code = str(r.get("A_STOCK_CODE") or r["COMPANY_CODE"]).zfill(6)
                instrument = "SH" + code
                listing = pd.to_datetime(
                    r["LIST_DATE"], format="%Y%m%d", errors="coerce"
                )
                delist = pd.to_datetime(
                    r["DELIST_DATE"], format="%Y%m%d", errors="coerce"
                )
                board = "star" if str(r["STOCK_TYPE"]) == "8" else "main_board"
                old = self.meta[self.meta.instrument.eq(instrument)]
                exists = len(old) > 0
                match = bool(exists and old.iloc[0].listing_date == listing)
                reconciliation.append(
                    dict(
                        instrument=instrument,
                        official_source=receipt["source_id"],
                        official_listing=str(listing.date())
                        if pd.notna(listing)
                        else None,
                        official_delisting=str(delist.date())
                        if pd.notna(delist)
                        else None,
                        legacy_present=exists,
                        listing_date_match=match,
                        delisting_date_match=bool(
                            exists
                            and (
                                pd.isna(old.iloc[0].delist_date)
                                and pd.isna(delist)
                                or old.iloc[0].delist_date == delist
                            )
                        ),
                        source_sha256=receipt["sha256"],
                        historical_membership_proved=False,
                    )
                )
                if not exists:
                    extra.append(
                        dict(
                            code=code,
                            instrument=instrument,
                            exchange="SH",
                            name=r.get("COMPANY_ABBR"),
                            listing_date=listing,
                            delist_date=delist,
                            board_bucket=board,
                            metadata_source=receipt["source_id"],
                            is_delisted=pd.notna(delist),
                            security_id=sid("SH", code, str(listing.date()))
                            if pd.notna(listing)
                            else None,
                            source_sha256=receipt["sha256"],
                            source_path=receipt["archive_path"],
                        )
                    )
        inventory = self.meta.copy()
        inventory["source_sha256"] = self.meta_sha
        inventory["source_path"] = str(p.resolve())
        inventory = pd.concat([inventory, pd.DataFrame(extra)], ignore_index=True)
        inventory["identity_status"] = (
            "PROVISIONAL_LISTING_EPISODE_NOT_CROSS_CODE_CERTIFIED"
        )
        inventory["quality_tier"] = "Historical-proxy"
        inventory["historical_name_known"] = False
        inventory["historical_status_known"] = False
        self.inventory = inventory.sort_values("instrument").reset_index(drop=True)
        self.csv(self.inventory.drop(columns=["source_path"]), "security_inventory.csv")
        self.parquet(self.inventory, "identity/security_inventory.parquet", "identity")
        self.csv(pd.DataFrame(reconciliation), "official_reconciliation.csv")
        # Normalized identity facts do not backdate today's names or state.
        facts = []
        for row in self.inventory.to_dict("records"):
            if pd.isna(row["listing_date"]):
                continue
            for field, value, effective in [
                ("listed", True, row["listing_date"]),
                ("code", row["instrument"], row["listing_date"]),
                ("exchange", row["exchange"], row["listing_date"]),
                ("board", row["board_bucket"], row["listing_date"]),
            ]:
                facts.append(self.fact(row, field, value, effective))
            if pd.notna(row["delist_date"]):
                facts.append(self.fact(row, "listed", False, row["delist_date"]))
        self.store = FactStore(facts)
        self.store.to_parquet(CACHE / "identity/facts.parquet")
        self.products.append(
            dict(
                path=str(CACHE / "identity/facts.parquet"),
                sha256=sha(CACHE / "identity/facts.parquet"),
                rows=len(facts),
                domain="identity",
                quality_tier="Historical-proxy",
            )
        )
        d1 = self.meta[
            (self.meta.listing_date <= "2026-04-30")
            & (self.meta.delist_date.isna() | (self.meta.delist_date > "2017-01-26"))
        ]
        comparison = self.meta[
            ["instrument", "security_id", "board_bucket", "listing_date", "delist_date"]
        ].copy()
        comparison["in_EP01_4915"] = True
        comparison["in_D1_4819"] = comparison.instrument.isin(d1.instrument)
        comparison["D1_exclusion_reason"] = np.where(
            comparison.in_D1_4819,
            "IN_SCOPE",
            np.where(
                comparison.delist_date.le(pd.Timestamp("2017-01-26")),
                "DELISTED_BEFORE_FIRST_MONTH_ORIGIN",
                "LISTED_AFTER_LAST_D0_ORIGIN",
            ),
        )
        self.csv(comparison, "universe_4915_4819_bridge.csv")
        self.identity_summary = dict(
            legacy_metadata=len(self.meta),
            D1_metadata=len(d1),
            excluded_from_D1=comparison.D1_exclusion_reason.value_counts().to_dict(),
            additional_observed_official=len(extra),
            provisional_inventory=len(self.inventory),
            complete_historical_population_certified=False,
            cross_code_identity_certified=False,
            official_historical_reconciliation="BLOCKED",
            certified_identity_facts=0,
        )
        write_json(AUDIT / "identity_summary.json", self.identity_summary)

    def fact(self, row, field, value, effective):
        f = dict.fromkeys(COLUMNS)
        logical = f"{row['security_id']}/{field}/{pd.Timestamp(effective).date()}"
        f.update(
            record_id=hashlib_id(logical + row["source_sha256"]),
            logical_key=logical,
            security_id=row["security_id"],
            field=field,
            value=value,
            event_time=effective,
            effective_time=effective,
            known_at=None,
            source_observed_at=self.now,
            ingested_at=self.now,
            source_uri=row["metadata_source"],
            source_path=row["source_path"],
            source_sha256=row["source_sha256"],
            unit="boolean" if isinstance(value, bool) else "identifier",
            original_version="legacy_or_official_snapshot_not_first_vintage",
            transform_sha256=self.transform,
            quality_tier="Historical-proxy",
            publication_evidence=None,
            reconstruction=None,
            supersedes=None,
        )
        return f

    def audit_quotes_and_shares(self):
        rows, coverage, quarantine, share_stats = [], [], [], []
        years = range(2017, pd.Timestamp(self.now).tz_convert("Asia/Shanghai").year + 1)
        for j, row in enumerate(self.inventory.itertuples()):
            old = TOPIC / f"data/raw/akshare/day/raw/{row.instrument}.csv"
            recovered = (
                EP28
                / f"outputs/local_cache/recovered_prices/{row.instrument}_raw.parquet"
            )
            p = old if old.exists() else recovered if recovered.exists() else None
            source_type = (
                "legacy_raw" if p == old else "EP28_recovered_raw" if p else "missing"
            )
            bars = pd.DataFrame(
                columns=["date", "open", "high", "low", "close", "volume", "money"]
            )
            bad_count = 0
            if p:
                digest = self.register(p, "raw_prices")
                bars = (
                    pd.read_csv(p, parse_dates=["date"])
                    if p.suffix == ".csv"
                    else pd.read_parquet(p)
                )
                bars["date"] = (
                    pd.to_datetime(bars.date).dt.tz_localize(None).dt.normalize()
                )
                numeric = [
                    c
                    for c in [
                        "open",
                        "high",
                        "low",
                        "close",
                        "volume",
                        "money",
                        "turnover_rate",
                    ]
                    if c in bars
                ]
                bars[numeric] = bars[numeric].apply(pd.to_numeric, errors="coerce")
                invalid = (
                    ~bars.date.isin(self.calendar)
                    | bars.date.duplicated(keep=False)
                    | bars[["open", "high", "low", "close"]].isna().any(axis=1)
                    | bars[["open", "high", "low", "close"]].le(0).any(axis=1)
                    | (bars.high < bars[["open", "close", "low"]].max(axis=1))
                    | (bars.low > bars[["open", "close", "high"]].min(axis=1))
                )
                if "volume" in bars:
                    invalid |= bars.volume.lt(0)
                for r in bars[invalid].to_dict("records"):
                    quarantine.append(
                        dict(
                            instrument=row.instrument,
                            date=r["date"],
                            reason="CALENDAR_DUPLICATE_OR_INVALID_OHLCV",
                            source_sha256=digest,
                        )
                    )
                bad_count = int(invalid.sum())
                bars = bars[~invalid].sort_values("date").copy()
                bars["security_id"] = row.security_id
                bars["quality_tier"] = "Historical-proxy"
                bars["source_sha256"] = digest
                bars["can_buy"] = pd.Series(
                    [None] * len(bars), index=bars.index, dtype="boolean"
                )
                bars["can_sell"] = pd.Series(
                    [None] * len(bars), index=bars.index, dtype="boolean"
                )
                bars["execution_reason"] = "BAR_PRESENCE_DOES_NOT_PROVE_FILL_OR_STATUS"
                self.parquet(bars, f"prices/{row.security_id}.parquet", "raw_prices")
            expected = self.calendar[self.calendar >= row.listing_date]
            if pd.notna(row.delist_date):
                expected = expected[expected < row.delist_date]
            valid_listed = bars[bars.date.isin(expected)]
            rows.append(
                dict(
                    instrument=row.instrument,
                    security_id=row.security_id,
                    board=row.board_bucket,
                    is_delisted=row.is_delisted,
                    source=source_type,
                    source_file=str(p.relative_to(TOPIC)) if p else None,
                    rows=len(bars),
                    listed_valid_rows=len(valid_listed),
                    expected_listed_sessions=len(expected),
                    missing_listed_sessions=len(expected) - len(valid_listed),
                    quarantined_rows=bad_count,
                    first_price=str(bars.date.min().date()) if len(bars) else None,
                    last_price=str(bars.date.max().date()) if len(bars) else None,
                    execution_status_certified=False,
                    source_failure=not bool(p),
                )
            )
            for year in years:
                wanted = expected[expected.year == year]
                present = (
                    valid_listed[valid_listed.date.dt.year == year]
                    if len(valid_listed)
                    else valid_listed
                )
                coverage.append(
                    dict(
                        field="raw_OHLCV",
                        year=year,
                        board=row.board_bucket,
                        expected_listed_sessions=len(wanted),
                        observed_rows=len(present),
                        missing_unclassified_or_source_failure=len(wanted)
                        - len(present),
                        original_version_certified_rows=0,
                        securities_expected=int(len(wanted) > 0),
                        securities_observed=int(len(present) > 0),
                        denominator="provisional_inventory_legacy_calendar",
                    )
                )
            share = TOPIC / f"data/raw/akshare/market_cap/{row.instrument}_shares.csv"
            s = pd.DataFrame()
            if share.exists():
                self.register(share, "shares")
                s = pd.read_csv(share)
                if ("变更日期" in s and "总股本" in s) or (
                    "share_date" in s and "total_share_asof" in s
                ):
                    normalized_input = "share_date" in s
                    if normalized_input and (
                        "share_unit" not in s or not s.share_unit.eq("shares").all()
                    ):
                        raise ValueError("unverified share units: " + str(share))
                    dates = pd.to_datetime(
                        s["share_date" if normalized_input else "变更日期"],
                        errors="coerce",
                    )
                    values = pd.to_numeric(
                        s["total_share_asof" if normalized_input else "总股本"],
                        errors="coerce",
                    )
                    normalized = pd.DataFrame(
                        dict(effective_date=dates, total_shares=values)
                    )
                    normalized["security_id"] = row.security_id
                    normalized["unit"] = "shares"
                    normalized["source_sha256"] = sha(share)
                    normalized["known_at"] = pd.NaT
                    normalized["quality_tier"] = "Historical-proxy"
                    self.parquet(
                        normalized, f"shares/{row.security_id}.parquet", "shares"
                    )
                    conflicts = int(
                        normalized.groupby("effective_date")
                        .total_shares.nunique()
                        .gt(1)
                        .sum()
                    )
                    positive = normalized[
                        normalized.total_shares.gt(0)
                        & normalized.effective_date.notna()
                    ]
                    share_stats.append(
                        dict(
                            instrument=row.instrument,
                            rows=len(s),
                            first_effective=positive.effective_date.min(),
                            last_effective=positive.effective_date.max(),
                            invalid_rows=int(len(normalized) - len(positive)),
                            conflicting_dates=conflicts,
                            earliest_expected=expected[0] if len(expected) else None,
                            historical_publication_certified=False,
                            declared_unit="shares_in_normalized_legacy_cache",
                        )
                    )
                else:
                    share_stats.append(
                        dict(
                            instrument=row.instrument,
                            rows=len(s),
                            invalid_rows=len(s),
                            conflicting_dates=None,
                            historical_publication_certified=False,
                            declared_unit="UNSUPPORTED_SCHEMA_BLOCKED",
                        )
                    )
            if j % 700 == 0:
                print("raw/share audit", j, "/", len(self.inventory), flush=True)
        q = pd.DataFrame(rows)
        self.quotes = q
        self.csv(q, "quote_security_coverage.csv")
        self.csv(
            pd.DataFrame(
                quarantine, columns=["instrument", "date", "reason", "source_sha256"]
            ),
            "quote_quarantine.csv",
        )
        self.csv(pd.DataFrame(share_stats), "share_history_audit.csv")
        cov = (
            pd.DataFrame(coverage)
            .groupby(["field", "year", "board", "denominator"], as_index=False)
            .sum(numeric_only=True)
        )
        cov["coverage_rate"] = cov.observed_rows.div(
            cov.expected_listed_sessions.replace(0, np.nan)
        )
        cov["strict_gate"] = "BLOCKED"
        self.csv(cov, "field_year_board_coverage.csv")
        old = EP05 / "outputs/publishable/tables/data_source_coverage_audit.csv"
        self.register(old, "legacy_source_gap")
        gap = pd.read_csv(old)
        join = gap.merge(
            q[["instrument", "source", "rows"]], on="instrument", how="left"
        )
        self.csv(join, "source_gap_318_229_228_bridge.csv")
        self.quote_summary = dict(
            raw_source_securities=int(q.source.ne("missing").sum()),
            legacy_sources=int(q.source.eq("legacy_raw").sum()),
            recovered_sources=int(q.source.eq("EP28_recovered_raw").sum()),
            unresolved_sources=int(q.source.eq("missing").sum()),
            rows=int(q.rows.sum()),
            quarantined_rows=int(q.quarantined_rows.sum()),
            share_history_files=len(share_stats),
            EP05_states=gap.support_state.value_counts().to_dict(),
            certified_status_rows=0,
            latest_raw_observation=q.last_price.dropna().max(),
            calendar_sessions=len(self.calendar),
        )
        write_json(AUDIT / "quote_summary.json", self.quote_summary)

    def audit_domains(self):
        inventories, year_rows = [], []
        specs = [
            (
                "financials",
                EP24 / "outputs/local_cache/public_financials",
                "REPORT_DATE",
            ),
            ("valuation", EP24 / "outputs/local_cache/public_valuation", "TRADE_DATE"),
            ("industry", EP24 / "outputs/local_cache/r32_industry", "published"),
            ("corporate_actions", EP24 / "outputs/local_cache/corporate_actions", None),
            ("macro", EP24 / "outputs/local_cache/public_yields", None),
        ]
        board_map = self.inventory.set_index("instrument").board_bucket.to_dict()
        self.domain_summaries = {}
        for domain, root, date_col in specs:
            total = 0
            for p in sorted(root.glob("*.parquet")):
                digest = self.register(p, domain)
                f = pd.read_parquet(p)
                total += len(f)
                rec = dict(
                    domain=domain,
                    file=p.name,
                    rows=len(f),
                    columns="|".join(f.columns),
                    source_sha256=digest,
                    original_version_certified=False,
                    first_observed_by_EP30=self.now,
                    known_at_certified=False,
                )
                # Keep wide source fields intact, in a separate explicitly-proxy partition.
                self.parquet(f, f"proxy/{domain}/{p.name}", domain)
                if date_col and date_col in f:
                    dates = pd.to_datetime(f[date_col], errors="coerce")
                    rec.update(
                        first_date=str(dates.min()),
                        last_date=str(dates.max()),
                        missing_date=int(dates.isna().sum()),
                    )
                    if domain == "financials":
                        notice = pd.to_datetime(f.NOTICE_DATE, errors="coerce")
                        update = pd.to_datetime(f.UPDATE_DATE, errors="coerce")
                        rec.update(
                            notice_missing=int(notice.isna().sum()),
                            update_after_notice=int((update > notice).sum()),
                            report_period_duplicates=int(
                                f.REPORT_DATE.duplicated(keep=False).sum()
                            ),
                            original_first_version_count=0,
                        )
                    if domain == "industry":
                        instruments = (
                            f.code.astype(str)
                            .str.zfill(6)
                            .map(lambda c: ("SH" if c.startswith("6") else "SZ") + c)
                        )
                    else:
                        code = p.stem.split(".")[0]
                        instruments = pd.Series(
                            [("SH" if code.startswith("6") else "SZ") + code] * len(f),
                            index=f.index,
                        )
                    yy = pd.DataFrame(
                        dict(
                            year=dates.dt.year,
                            board=instruments.map(board_map).fillna("out_of_inventory"),
                        )
                    )
                    for (year, board), group in yy.dropna().groupby(["year", "board"]):
                        year_rows.append(
                            dict(
                                domain=domain,
                                field=date_col,
                                year=int(year),
                                board=board,
                                observed_rows=len(group),
                                original_version_certified_rows=0,
                                denominator="source_observations_not_complete_population",
                            )
                        )
                inventories.append(rec)
            self.domain_summaries[domain] = dict(
                files=len(list(root.glob("*.parquet"))),
                rows_including_overlapping_pages=total,
                strict_gate="BLOCKED",
                reason="NO_COMPLETE_VERIFIED_FIRST_VINTAGE_OR_RIGHTS_LEDGER",
            )
            print(
                "domain inventory",
                domain,
                self.domain_summaries[domain]["files"],
                flush=True,
            )
        self.csv(pd.DataFrame(inventories), "domain_file_inventory.csv")
        if year_rows:
            y = (
                pd.DataFrame(year_rows)
                .groupby(
                    ["domain", "field", "year", "board", "denominator"], as_index=False
                )
                .sum(numeric_only=True)
            )
            y["strict_gate"] = "BLOCKED"
            self.csv(y, "domain_year_board_observations.csv")
        # Preserve raw industry releases and corporate action JSON page bytes as well as Parquet.
        for root in [
            EP24 / "outputs/local_cache/r32_industry",
            EP24 / "outputs/local_cache/corporate_actions",
        ]:
            for p in sorted(root.iterdir()):
                if p.is_file() and p.suffix in (".js", ".json", ".pdf"):
                    self.register(
                        p,
                        "industry_original_release"
                        if root.name == "r32_industry"
                        else "corporate_action_source",
                    )
        for p in sorted((TOPIC / "data/raw/akshare/status").rglob("*.csv")):
            self.register(p, "identity_and_status_evidence")
        write_json(AUDIT / "domain_summary.json", self.domain_summaries)

    def bridge(self):
        d0path = EP28 / "outputs/local_cache/d0_panel.parquet"
        d1path = EP28 / "outputs/local_cache/d1_label_census.parquet"
        self.register(d0path, "D0_frozen")
        self.register(d1path, "D1_frozen")
        d0 = pd.read_parquet(d0path)
        d1 = pd.read_parquet(d1path)
        self.d0 = d0
        for p in [
            EP28 / "outputs/audits/population_event_bounds.csv",
            EP28 / "outputs/audits/quote_coverage.csv",
            EP28 / "outputs/audits/delisted_source_attempts.jsonl",
        ]:
            self.register(p, "legacy_audit")
        b = d1.merge(
            d0[["date", "instrument", "y_6", "end_6"]],
            on=["date", "instrument"],
            how="outer",
            indicator=True,
        )
        b["D0_member"] = b["_merge"].isin(["both", "right_only"])
        b["D1_member"] = b["_merge"].isin(["both", "left_only"])
        b["D2_provisional_member"] = b["D1_member"]
        b["D2_strict_member"] = (
            False  # UNKNOWN admission, not proof of no historical securities
        )
        b["D2_strict_member_reason"] = "NO_CERTIFIED_HISTORICAL_IDENTITY_AND_STATUS"
        b["D2_price_label"] = np.nan
        b["D2_total_label"] = np.nan
        b["D2_executable_label"] = np.nan
        b["D2_label_reason"] = (
            "UNVERIFIED_EXECUTION_AND_COMPLETE_CORPORATE_ACTION_LEDGER"
        )
        b["legacy_return_difference"] = b["y_6"] - b["actual"]
        b["legacy_knownness_differs"] = b["y_6"].notna() != b["actual"].notna()
        b = b.drop(columns=["_merge"])
        self.parquet(b, "bridge/security_month_labels.parquet", "bridge")
        summary = []
        for name, f, val, end in [
            ("D0", d0, "y_6", "end_6"),
            ("D1", d1, "actual", "label_end"),
        ]:
            test = f[f.date.ge("2021-01-01")]
            summary.append(dict(population=name, **bounds(test, val, end)))
        test = d1[d1.date.ge("2021-01-01")]
        n = int(test.label_end.notna().sum())
        summary.append(
            dict(
                population="D2_strict_on_D1_origins_conditional_only",
                origins=len(test),
                mature=n,
                known=0,
                missing=n,
                censored=len(test) - n,
                events=None,
                rate_known=None,
                rate_lower=0.0,
                rate_upper=1.0,
            )
        )
        self.csv(pd.DataFrame(summary), "population_event_bounds.csv")
        self.bridge_summary = dict(
            D0_rows=len(d0),
            D1_rows=len(d1),
            union_rows=len(b),
            matched_rows=int((b.D0_member & b.D1_member).sum()),
            legacy_return_mismatch_max=float(b.legacy_return_difference.abs().max()),
            legacy_return_mismatch_count=int(
                b.legacy_return_difference.abs().gt(1e-12).sum()
            ),
            D2_strict_known_labels=0,
            D2_population_unbiased=False,
            caution="zero admitted strict records means blocked evidence, not an empty real market",
        )
        write_json(AUDIT / "bridge_summary.json", self.bridge_summary)
        self.csv(
            b.groupby("instrument", as_index=False).agg(
                D0_origins=("D0_member", "sum"),
                D1_origins=("D1_member", "sum"),
                D0_known=("y_6", "count"),
                D1_known=("actual", "count"),
                D2_known=("D2_total_label", "count"),
            ),
            "bridge_by_security.csv",
        )
        monthly = []
        for date, f in b.groupby("date"):
            for version, member, actual, end in [
                ("D0", "D0_member", "y_6", "end_6"),
                ("D1", "D1_member", "actual", "label_end"),
            ]:
                monthly.append(
                    dict(
                        date=date,
                        population=version,
                        **bounds(f[f[member]], actual, end),
                    )
                )
            mature = int(f.loc[f.D1_member, "label_end"].notna().sum())
            monthly.append(
                dict(
                    date=date,
                    population="D2_strict_conditional_D1",
                    origins=int(f.D1_member.sum()),
                    mature=mature,
                    known=0,
                    missing=mature,
                    censored=int(f.D1_member.sum()) - mature,
                    events=None,
                    rate_known=None,
                    rate_lower=0.0 if mature else None,
                    rate_upper=1.0 if mature else None,
                )
            )
        self.csv(pd.DataFrame(monthly), "bridge_by_month.csv")
        # Explicit per-horizon admission ledger. Reusing a 6m proxy is prohibited.
        label_rows = []
        for h in ["6_calendar_months", "20_sessions", "60_sessions", "120_sessions"]:
            for policy in ["price", "total", "executable"]:
                label_rows.append(
                    dict(
                        horizon=h,
                        return_policy=policy,
                        known=0,
                        status="BLOCKED",
                        reason="NEXT_OPEN_EXECUTION_UNVERIFIED"
                        if policy == "price"
                        else "EXECUTION_AND_RIGHTS_UNVERIFIED",
                        MFE_MAE="UNKNOWN",
                        legacy_6m_proxy_not_substituted=True,
                    )
                )
        self.csv(pd.DataFrame(label_rows), "bridge_by_label_contract.csv")
        # Compare inherited event-rate bounds with exact reproducible arithmetic.
        old = pd.read_csv(EP28 / "outputs/audits/population_event_bounds.csv")
        for name, new in [
            ("D0_fixed_EP27", summary[0]),
            ("D1_all_listed_in_metadata", summary[1]),
        ]:
            prior = old[old.population.eq(name)].iloc[0]
            for key in ["mature", "known", "missing", "events"]:
                if int(prior[key]) != new[key]:
                    raise ValueError(
                        "inherited label census mismatch " + name + "/" + key
                    )

    def timelines(self):
        q = self.quotes.merge(
            self.meta[["instrument", "listing_date", "delist_date"]],
            on="instrument",
            how="left",
        )
        lifetime = EP01 / "outputs/manifests/cache_manifest.csv"
        self.register(lifetime, "lifetime_ST_selection_bias")
        st = pd.read_csv(lifetime)
        st = set(st.loc[st.is_sh_lifetime_st_excluded.eq(True), "instrument"])
        shares = pd.read_csv(AUDIT / "share_history_audit.csv")
        strata = {
            "ordinary_SH": q[q.instrument.str.startswith("SH") & ~q.is_delisted],
            "ordinary_SZ": q[q.instrument.str.startswith("SZ") & ~q.is_delisted],
            "delisted_SH": q[q.instrument.str.startswith("SH") & q.is_delisted],
            "delisted_SZ": q[q.instrument.str.startswith("SZ") & q.is_delisted],
            "lifetime_ST": q[q.instrument.isin(st)],
            "share_change": q[
                q.instrument.isin(shares.loc[shares.rows.gt(1), "instrument"])
            ],
        }
        result = []
        for group, frame in strata.items():
            # Select only episodes overlapping the requested legacy window.
            frame = frame[
                frame.listing_date.le(END)
                & (frame.delist_date.isna() | frame.delist_date.gt(START))
            ]
            if frame.empty:
                continue
            r = frame.sort_values("instrument").iloc[0]
            result.append(
                dict(
                    stratum=group,
                    instrument=r.instrument,
                    listing=r.listing_date,
                    delisting=r.delist_date,
                    first_raw_quote=r.first_price,
                    last_raw_quote=r.last_price,
                    source=r.source,
                    known_at="UNKNOWN",
                    historical_status="UNKNOWN",
                    complete_rights="UNKNOWN",
                    terminal_equity="UNKNOWN",
                    lifetime_ST_diagnostic_only=bool(r.instrument in st),
                    independent_human_checked=False,
                    machine_consistency="ORDERED_DATES_SOURCE_HASHES_AUDITED",
                )
            )
        self.csv(pd.DataFrame(result), "representative_timelines.csv")

    def finalize(self):
        pd.DataFrame(self.sources.values()).sort_values("path").to_csv(
            MAN / "input_sources.csv", index=False
        )
        pd.DataFrame(self.products).sort_values("path").to_csv(
            MAN / "local_cache_manifest.csv", index=False
        )
        prior = json.loads((MAN / "prior_preservation.json").read_text())
        differences = [
            p for p, h in prior.items() if not Path(p).is_file() or sha(p) != h
        ]
        if differences:
            raise ValueError("upstream modified " + repr(differences[:5]))
        write_json(
            AUDIT / "validation.json",
            dict(
                prior_files_checked=len(prior),
                prior_files_changed=len(differences),
                frozen_contracts_unchanged=True,
                source_files_hashed=len(self.sources),
                normalized_partitions=len(self.products),
                original_vintages_not_fabricated=True,
                alpha_models_trained=0,
                requested_run_date=str(
                    pd.Timestamp(self.now).tz_convert("Asia/Shanghai").date()
                ),
                legacy_raw_cutoff=str(END.date()),
                later_market_history_gate="BLOCKED",
                independent_human_review_count=0,
                human_review_match_rate=None,
                source_observed_at=self.now,
                production_full_market_PIT_ready=False,
            ),
        )
        write_json(
            AUDIT / "summary.json",
            dict(
                identity=self.identity_summary,
                quotes=self.quote_summary,
                domains=self.domain_summaries,
                bridge=self.bridge_summary,
            ),
        )
        print("audit complete; old files unchanged", len(prior), flush=True)


def hashlib_id(text):
    import hashlib

    return hashlib.sha256(text.encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, default=CACHE)
    args = parser.parse_args()
    if args.cache != CACHE:
        raise SystemExit(
            "Set EP30_CACHE environment variable consistently for all commands"
        )
    a = Audit()
    a.load_identity()
    a.audit_quotes_and_shares()
    a.audit_domains()
    a.bridge()
    a.timelines()
    a.finalize()


if __name__ == "__main__":
    main()
