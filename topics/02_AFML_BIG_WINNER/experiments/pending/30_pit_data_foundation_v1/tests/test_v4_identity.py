import json

import pandas as pd
import pytest
import numpy as np

import v4_cninfo
from v4_dataset import D2V4Dataset
from pit import FactStore, AsOfResult
from v4_offline_replay import copy_replay_inputs
from v4_identity import slice_price_aliases
from v4_pipeline import classify_report, usable_time


def test_code_change_slices_retained_old_quotes_and_new_code_backfill():
    old = pd.DataFrame(
        dict(date=["2025-02-14", "2025-02-17", "2025-02-18"], open=[10, 10, 10])
    )
    new = pd.DataFrame(
        dict(date=["2025-02-14", "2025-02-17", "2025-02-18"], open=[99, 11, 12])
    )
    f = slice_price_aliases(old, new, "2025-02-17")
    assert f.open.tolist() == [10, 11, 12]
    assert not f.date.duplicated().any()


def test_duplicate_quotes_inside_one_valid_interval_are_not_silently_collapsed():
    old = pd.DataFrame(dict(date=["2025-02-14"] * 2, open=[10, 11]))
    new = pd.DataFrame(dict(date=["2025-02-17"], open=[12]))
    with pytest.raises(ValueError, match="overlap"):
        slice_price_aliases(old, new, "2025-02-17")


def test_independent_opinion_is_not_an_original_full_annual_report():
    assert (
        classify_report("退市刚泰:独立董事关于公司2020年度报告相关事项的独立意见")[
            "form"
        ]
        == "ancillary"
    )
    assert classify_report("退市刚泰:2020年年度报告(更正后)")["is_revision"] is True
    assert (
        classify_report("长生1:2018年年度报告(补发)")["report_period"] == "2018-12-31"
    )


def test_issuer_link_never_makes_an_earlier_report_usable_before_identity_proof():
    published = pd.Timestamp("2024-04-30 09:30", tz="Asia/Shanghai")
    proof = pd.Timestamp("2024-05-07 09:30", tz="Asia/Shanghai")
    assert usable_time(published, proof) == proof
    assert pd.isna(usable_time(published, pd.NaT))


class FakeHTTP:
    def __init__(self, pages):
        self.pages = iter(pages)

    def fetch(self, source_id, url, data, method):
        assert data["pageSize"] == 30
        assert method == "POST"
        return json.dumps(next(self.pages)).encode(), dict(sha256="a" * 64)


def row(code="300114"):
    return dict(
        instrument="SZ" + code, org_id="org", security_id="old", report_year=2024
    )


def notice(code, identifier="1"):
    return dict(
        secCode=code,
        announcementId=identifier,
        announcementTime=1742860800000,
        announcementTitle="2024年年度报告",
    )


def test_same_org_without_verified_code_mapping_does_not_authorize_a_new_code(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(v4_cninfo, "V4", tmp_path)
    http = FakeHTTP([dict(totalAnnouncement=1, announcements=[notice("302132")])])
    with pytest.raises(ValueError, match="issuer filter"):
        v4_cninfo.search(http, row())
    assert not list(tmp_path.rglob("*.json"))


def test_verified_code_link_preserves_its_later_knowledge_boundary(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(v4_cninfo, "V4", tmp_path)
    (tmp_path / "normalized").mkdir()
    pd.DataFrame(
        [
            dict(
                canonical_security_id="old",
                new_instrument="SZ302132",
                known_at="2025-04-01 09:30+08:00",
                source_sha256="b" * 64,
            )
        ]
    ).to_parquet(tmp_path / "normalized/security_id_redirects.parquet")
    http = FakeHTTP([dict(totalAnnouncement=1, announcements=[notice("302132")])])
    result = v4_cninfo.search(http, row())
    assert (
        result["announcements"][0]["identity_link_known_at"] == "2025-04-01 09:30+08:00"
    )
    assert result["complete"] is True


@pytest.mark.parametrize("second_total,second_id", [(2, "1"), (3, "2")])
def test_repeated_or_drifting_pages_never_become_complete(
    tmp_path, monkeypatch, second_total, second_id
):
    monkeypatch.setattr(v4_cninfo, "V4", tmp_path)
    http = FakeHTTP(
        [
            dict(totalAnnouncement=2, announcements=[notice("300114")]),
            dict(
                totalAnnouncement=second_total,
                announcements=[notice("300114", second_id)],
            ),
        ]
    )
    with pytest.raises(ValueError, match="duplicate|unstable"):
        v4_cninfo.search(http, row())
    assert not list(tmp_path.rglob("*.json"))


@pytest.mark.parametrize(
    "field",
    [
        "can_buy",
        "listed",
        "financial:reviewed_reported_revenue:2018-12-31",
        "trading_code",
    ],
)
def test_reader_unavailable_fields_fail_closed_without_using_an_alias_loop_variable(
    field,
):
    reader = D2V4Dataset.__new__(D2V4Dataset)
    reader._sid = lambda _: "canonical"
    reader.finance = reader.prior_finance = reader.states = reader.aliases = (
        reader.code_changes
    ) = FactStore()
    reader.intervals = pd.DataFrame(columns=["security_id"])
    reader.base = None
    result = reader.get_asof("canonical", field, "2017-01-03 15:00")
    assert result.value is None and result.status == "UNKNOWN"


def test_reviewed_negative_membership_is_python_false_not_missing():
    reader = D2V4Dataset.__new__(D2V4Dataset)
    reader._sid = lambda _: "canonical"

    class NegativeStore:
        facts = pd.DataFrame([dict(security_id="canonical", field="listed")])

        def get_asof(self, *args):
            return AsOfResult(np.bool_(False), "PIT-reconstructed", "ORIGINAL_REMOVAL")

    reader.finance = reader.prior_finance = reader.aliases = reader.code_changes = (
        FactStore()
    )
    reader.states = NegativeStore()
    result = reader.get_asof("canonical", "listed", "2024-01-23 09:30")
    assert result.value is False and result.status == "PIT-reconstructed"


def test_frozen_replay_keeps_nested_baseline_source_helpers(tmp_path):
    release = tmp_path / "release"
    helper = release / "inputs/source/src/v3_bridge.py"
    helper.parent.mkdir(parents=True)
    helper.write_bytes(b"frozen bridge helper")
    copy_replay_inputs(release, tmp_path / "replay")
    assert (
        tmp_path / "replay/inputs/source/src/v3_bridge.py"
    ).read_bytes() == helper.read_bytes()
