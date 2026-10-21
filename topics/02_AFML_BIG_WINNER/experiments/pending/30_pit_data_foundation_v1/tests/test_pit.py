import pandas as pd
import pytest
from archive import archive_bytes, sha, verify_receipt
from pit import COLUMNS, Calendar, FactStore, reconstruct_valuation


@pytest.fixture
def fact(tmp_path):
    p = tmp_path / "original.txt"
    p.write_text("original source (synthetic fixture)")
    f = dict.fromkeys(COLUMNS)
    f.update(
        record_id="original",
        logical_key="s/earnings/2020",
        security_id="s",
        field="earnings",
        value=100.0,
        event_time="2020-12-31",
        effective_time="2020-12-31",
        known_at="2021-03-01 16:00",
        source_observed_at="2026-10-21",
        ingested_at="2026-10-21",
        source_uri="issuer/notice1",
        source_path=str(p),
        source_sha256=sha(p),
        unit="CNY",
        original_version="1",
        transform_sha256="a" * 64,
        quality_tier="PIT-certified",
        publication_evidence="synthetic-original-release",
    )
    return f


def test_historical_and_archived_are_distinct(fact):
    s = FactStore([fact])
    assert s.get_asof("s", "earnings", "2021-03-01 15:00").value is None
    assert s.get_asof("s", "earnings", "2021-03-02").value == 100
    assert s.get_asof("s", "earnings", "2021-03-02", mode="archived").value is None
    assert s.get_asof("s", "earnings", "2026-10-22", mode="archived").value == 100


@pytest.mark.parametrize(
    "field,value",
    [
        ("is_st", True),
        ("total_shares", 999999),
        ("earnings", -100),
        ("qfq_factor", 99),
        ("industry", "TODAY"),
    ],
)
def test_future_injection_and_truncation_invariant(fact, field, value):
    base = {**fact, "field": field, "value": 10, "logical_key": "s/" + field}
    original = FactStore([base])
    future = {
        **base,
        "record_id": "future",
        "known_at": "2025-01-01",
        "value": value,
        "supersedes": "original",
    }
    original.append([future])
    before = original.get_asof("s", field, "2021-03-02")
    truncated = FactStore(
        original.facts[
            original.facts.known_at <= pd.Timestamp("2021-03-02", tz="Asia/Shanghai")
        ]
    )
    assert before == truncated.get_asof("s", field, "2021-03-02")
    assert before.value == 10
    assert original.get_asof("s", field, "2025-01-02").value == value


def test_effective_time_prevents_today_shares_backfill(fact):
    s = FactStore(
        [
            {
                **fact,
                "effective_time": "2026-01-01",
                "known_at": "2021-01-01",
                "field": "shares",
            }
        ]
    )
    assert s.get_asof("s", "shares", "2025-01-01").value is None


def test_date_only_publication_after_holiday():
    c = Calendar(["2024-04-30", "2024-05-06", "2024-05-07"])
    assert c.publication_time("2024-04-30") == pd.Timestamp(
        "2024-05-06 09:30", tz="Asia/Shanghai"
    )
    assert pd.isna(c.publication_time("2024-05-07"))
    assert c.publication_time("2024-04-30 16:10", True) == pd.Timestamp(
        "2024-04-30 16:10", tz="Asia/Shanghai"
    )


@pytest.mark.parametrize(
    "change",
    [
        {"known_at": None},
        {"publication_evidence": None},
        {"source_sha256": "0" * 64},
        {"unit": None},
    ],
)
def test_strict_requires_evidence(fact, change):
    with pytest.raises(ValueError):
        FactStore([{**fact, **change}])


def test_reconstruction_requires_recipe(fact):
    with pytest.raises(ValueError):
        FactStore([{**fact, "quality_tier": "PIT-reconstructed"}])
    f = {
        **fact,
        "quality_tier": "PIT-reconstructed",
        "reconstruction": "page 1 times 10000 CNY",
    }
    assert (
        FactStore([f]).get_asof("s", "earnings", "2021-04-01").status
        == "PIT-reconstructed"
    )


def test_proxy_never_promoted(fact):
    s = FactStore(
        [
            {
                **fact,
                "quality_tier": "Historical-proxy",
                "known_at": None,
                "publication_evidence": None,
            }
        ]
    )
    assert s.get_asof("s", "earnings", "2021-04-01").value is None
    assert (
        s.get_asof("s", "earnings", "2021-04-01", "Historical-proxy").status
        == "Historical-proxy"
    )
    assert (
        s.get_asof(
            "s", "earnings", "2021-04-01", "Historical-proxy", mode="archived"
        ).value
        is None
    )


def test_conflict_keeps_both_sources(fact):
    s = FactStore(
        [
            fact,
            {**fact, "record_id": "other", "source_uri": "other/notice", "value": 101},
        ]
    )
    r = s.get_asof("s", "earnings", "2021-04-01")
    assert (
        r.reason == "UNRESOLVED_SOURCE_CONFLICT"
        and len(r.records) == 2
        and r.value is None
    )


def test_append_only_and_tamper(fact):
    s = FactStore([fact])
    with pytest.raises(ValueError):
        s.append([fact])
    from pathlib import Path

    Path(fact["source_path"]).write_text("tampered")
    assert s.get_asof("s", "earnings", "2021-04-01").reason == "SOURCE_HASH_MISMATCH"


def test_parquet_roundtrip_and_qlib_provenance(fact, tmp_path):
    s = FactStore([fact])
    p = tmp_path / "facts.parquet"
    s.to_parquet(p)
    recovered = FactStore.from_parquet(p)
    assert s.snapshot_manifest("2026-10-22") == recovered.snapshot_manifest(
        "2026-10-22"
    )
    assert s.get_asof("s", "earnings", "2021-04-01") == recovered.get_asof(
        "s", "earnings", "2021-04-01"
    )
    f, receipt = s.qlib_frame([("s", "earnings", "2021-04-01")])
    assert f.index.names == ["datetime", "instrument"] and f.iloc[0]["$earnings"] == 100
    assert receipt.iloc[0].record_ids == ["original"]
    p.write_bytes(b"bad")
    with pytest.raises(ValueError):
        FactStore.from_parquet(p)


def test_archive_content_addressed_and_tamper(tmp_path):
    p, h = archive_bytes(b"fixture", tmp_path)
    assert archive_bytes(b"fixture", tmp_path) == (p, h)
    assert verify_receipt({"archive_path": str(p), "sha256": h})
    p.write_bytes(b"changed")
    with pytest.raises(ValueError):
        archive_bytes(b"fixture", tmp_path)


def test_universe_existence_not_strategy_or_status(fact):
    s = FactStore([{**fact, "field": "listed", "value": True}])
    u = s.universe_asof("2021-04-01")
    assert len(u) == 1 and u.iloc[0].can_buy is None
    assert u.iloc[0].can_buy_reason == "NO_ELIGIBLE_RECORD"
    s.append(
        [
            {
                **fact,
                "record_id": "delist",
                "field": "listed",
                "value": False,
                "effective_time": "2022-01-01",
                "known_at": "2022-01-01",
            }
        ]
    )
    assert s.universe_asof("2023-01-01").empty
    assert len(s.universe_asof("2021-04-01")) == 1


def test_valuation_negative_and_missing_denominator():
    f = reconstruct_valuation(10, 100, earnings_ttm=-2, equity=20, sales_ttm=None)
    assert (
        f["market_cap_cny"] == 1000
        and f["pe"] is None
        and f["pb"] == 50
        and f["ps"] is None
    )
    assert reconstruct_valuation(None, 100)["status"] == "UNKNOWN"


def test_correction_new_document_uri_preserves_original(fact):
    correction = {
        **fact,
        "record_id": "corrected",
        "source_uri": "issuer/notice2",
        "value": 200.0,
        "known_at": "2022-01-01",
        "supersedes": "original",
    }
    s = FactStore([fact, correction])
    assert s.get_asof("s", "earnings", "2021-06-01").value == 100
    assert s.get_asof("s", "earnings", "2022-06-01").value == 200
    assert len(s.facts) == 2


def test_proxy_snapshot_lists_actual_archived_bytes(fact):
    s = FactStore(
        [
            {
                **fact,
                "quality_tier": "Historical-proxy",
                "known_at": None,
                "publication_evidence": None,
            }
        ]
    )
    assert s.snapshot_manifest("2021-01-01")["record_count"] == 0
    assert s.snapshot_manifest("2026-10-22")["record_count"] == 1


def test_units_conflict_not_silently_merged(fact):
    s = FactStore(
        [
            fact,
            {
                **fact,
                "record_id": "other",
                "source_uri": "vendor/units",
                "unit": "10000_CNY",
            },
        ]
    )
    assert (
        s.get_asof("s", "earnings", "2021-06-01").reason == "UNRESOLVED_SOURCE_CONFLICT"
    )
