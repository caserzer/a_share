import json
import pandas as pd
import pytest
from archive import sha
from backfill_build import reconcile_prices
from backfill_dataset import D2BackfillDataset
from backfill_financials import parse_main_page, parse_bse_listing
from backfill_listings import explicit_listing_dates


def test_source_conflict_blocks_only_conflicting_field_and_keeps_evidence():
    f = pd.DataFrame(
        [
            dict(
                date=pd.Timestamp("2026-05-29"),
                close=10,
                open=9,
                money=100.49,
                volume=8,
                source_provider="BaoStock",
                source_sha256="a",
            ),
            dict(
                date=pd.Timestamp("2026-05-29"),
                close=11,
                open=9,
                money=100,
                volume=8,
                source_provider="Sina",
                source_sha256="b",
            ),
        ]
    )
    out, conflicts = reconcile_prices(f)
    assert pd.isna(out.iloc[0].close)
    assert out.iloc[0].open == 9
    assert out.iloc[0].money == 100.49
    assert out.iloc[0].source_sha256s == ["a", "b"]
    assert [r["field"] for r in conflicts] == ["close"]
    assert out.iloc[0].can_buy is None


def test_amount_difference_exceeding_rounding_precision_is_not_silently_selected():
    f = pd.DataFrame(
        [
            dict(
                date=pd.Timestamp("2026-05-29"),
                money=100.8,
                source_provider="BaoStock",
                source_sha256="a",
            ),
            dict(
                date=pd.Timestamp("2026-05-29"),
                money=100,
                source_provider="Sina",
                source_sha256="b",
            ),
        ]
    )
    out, conflicts = reconcile_prices(f)
    assert pd.isna(out.iloc[0].money)
    assert conflicts[0]["field"] == "money"


def test_real_bse_report_columns_are_separated_and_negative_sign_is_preserved():
    text = """第三节 会计数据和财务指标
    单位：元 2025 年 2024 年 本年比上年增减% 2023 年
    营业收入 212,838,536.28 217,795,993.08 -2.28% 202,572,099.73
    归属于上市公司股东的净利润 -19,607,358.15 32,950,382.04 -159.51% 31,656,453.36
    资产总计 807,179,733.18 854,633,052.93 -5.55% 772,878,448.26"""
    values = {r["field"]: r["value"] for r in parse_main_page(text, 2025)}
    assert values == dict(
        revenue=212838536.28, net_profit_parent=-19607358.15, total_assets=807179733.18
    )
    assert parse_main_page(text, 2024) == []
    assert parse_main_page(text.replace("单位：元", "单位：万元"), 2025) == []
    assert parse_main_page(text.replace("单位：元", ""), 2025) == []


def test_listing_proof_requires_explicit_event_clause_and_bse_market():
    assert explicit_listing_dates(
        "本公司股票将于2022年12月27日在北京证券交易所上市。"
    ) == {"2022-12-27"}
    assert explicit_listing_dates("2022年12月27日 董事会") == set()
    assert (
        parse_bse_listing("股票上市交易所 北京证券交易所 上市时间2020年7月27日") is None
    )
    assert (
        parse_bse_listing("股票上市交易所 北京证券交易所 上市时间2021年11月15日")
        == "2021-11-15"
    )


@pytest.fixture
def dataset(tmp_path):
    paths = {}

    def save(name, f):
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        f.to_parquet(p, index=False)
        paths[name] = sha(p)

    save(
        "securities.parquet",
        pd.DataFrame(
            [
                dict(
                    security_id="stable",
                    instrument="SH600000",
                    exchange="SH",
                    listing_date=pd.Timestamp("1999-11-10"),
                    delist_date=pd.NaT,
                    bse_listing_proxy=pd.NaT,
                    identity_date_conflict=False,
                )
            ]
        ),
    )
    save(
        "calendar.parquet",
        pd.DataFrame(
            dict(date=pd.to_datetime(["2026-05-28", "2026-05-29", "2026-06-01"]))
        ),
    )
    save(
        "prices/stable.parquet",
        pd.DataFrame(
            dict(
                date=pd.to_datetime(["2026-05-28", "2026-05-29"]),
                close=[10.0, 11.0],
                close_conflict=[False, True],
            )
        ),
    )
    save(
        "shares/stable.parquet",
        pd.DataFrame(
            dict(
                effective_date=pd.to_datetime(
                    ["2026-05-01", "2026-06-01", "2026-06-01"]
                ),
                total_shares=[100, 200, 300],
                source_sha256=["old", "new1", "new2"],
            )
        ),
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            dict(
                sealed_at="2026-10-21T19:00:00+08:00",
                files=[dict(relative_path=k, sha256=v) for k, v in paths.items()],
            )
        )
    )
    return D2BackfillDataset(tmp_path, manifest, baseline=False)


def test_new_proxy_never_satisfies_strict_pit(dataset):
    assert dataset.get_asof("SH600000", "close", "2026-05-28 15:00").value is None
    assert (
        dataset.get_asof(
            "SH600000", "close", "2026-05-28 15:00", "Historical-proxy"
        ).value
        == 10
    )


def test_daily_close_not_visible_intraday_and_conflict_cannot_be_carried_over(dataset):
    assert (
        dataset.get_asof(
            "SH600000", "close", "2026-05-29 14:59", "Historical-proxy"
        ).value
        == 10
    )
    after = dataset.get_asof(
        "SH600000", "close", "2026-05-29 15:00", "Historical-proxy"
    )
    assert after.value is None and after.reason == "UNRESOLVED_SOURCE_CONFLICT"


def test_future_share_changes_and_same_date_disagreements(dataset):
    assert (
        dataset.get_asof(
            "SH600000", "total_shares", "2026-05-29", "Historical-proxy"
        ).value
        == 100
    )
    assert (
        dataset.get_asof(
            "SH600000", "total_shares", "2026-06-01", "Historical-proxy"
        ).reason
        == "UNRESOLVED_SHARE_SOURCE_CONFLICT"
    )


def test_downloaded_history_cannot_become_an_old_archived_snapshot(dataset):
    r = dataset.get_asof(
        "SH600000", "close", "2026-05-28 15:00", "Historical-proxy", "archived"
    )
    assert r.value is None and r.reason == "BACKFILL_NOT_ARCHIVED_BY_DECISION_TIME"
    assert dataset.snapshot_manifest("2026-05-28")["status"] == "UNAVAILABLE"


def test_tampered_parquet_is_rejected_even_after_a_previous_read(dataset):
    path = dataset.root / "prices/stable.parquet"
    dataset.get_asof("SH600000", "close", "2026-05-28 15:00", "Historical-proxy")
    path.write_bytes(b"tamper")
    with pytest.raises(ValueError, match="changed sealed partition"):
        dataset.get_asof("SH600000", "close", "2026-05-28 15:00", "Historical-proxy")


def test_original_pilot_code_cutover_precedes_the_rest_of_the_market(dataset):
    dataset.inventory["instrument"] = "BJ920799"
    dataset.inventory["exchange"] = "BJ"
    dataset.inventory["bse_listing_proxy"] = pd.Timestamp("2021-11-15")
    dataset.aliases = pd.DataFrame(
        [
            dict(
                security_id="stable",
                historical_instrument="BJ830799",
                valid_from=pd.NaT,
                valid_to=pd.Timestamp("2025-05-06"),
            ),
            dict(
                security_id="stable",
                historical_instrument="BJ920799",
                valid_from=pd.Timestamp("2025-05-06"),
                valid_to=pd.NaT,
            ),
        ]
    )
    assert (
        dataset.get_asof("BJ830799", "code", "2025-04-30", "Historical-proxy").value
        == "830799"
    )
    assert (
        dataset.get_asof("BJ830799", "code", "2025-05-06", "Historical-proxy").value
        == "920799"
    )
    assert (
        dataset.get_asof("BJ920799", "code", "2025-09-30", "Historical-proxy").value
        == "920799"
    )
    assert (
        dataset.universe_asof("2025-04-30", "Historical-proxy").iloc[0].instrument
        == "BJ830799"
    )
    assert (
        dataset.universe_asof("2025-05-06", "Historical-proxy").iloc[0].instrument
        == "BJ920799"
    )
