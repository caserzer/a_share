import pandas as pd
from expand_bridge import expand_membership


def test_new_official_members_not_dropped_or_given_legacy_labels():
    dates = pd.DatetimeIndex(["2020-01-31", "2020-02-28"])
    inv = pd.DataFrame(
        [
            dict(
                instrument="SH1",
                security_id="one",
                board_bucket="main_board",
                listing_date=pd.Timestamp("2019-01-01"),
                delist_date=pd.NaT,
            ),
            dict(
                instrument="SH2",
                security_id="two",
                board_bucket="star",
                listing_date=pd.Timestamp("2020-02-01"),
                delist_date=pd.NaT,
            ),
        ]
    )
    legacy = pd.DataFrame(
        [
            dict(
                date=d,
                instrument="SH1",
                D0_member=True,
                D1_member=True,
                y_6=0.1,
                actual=0.1,
                D2_total_label=None,
            )
            for d in dates
        ]
    )
    out = expand_membership(inv, dates, legacy)
    assert len(out) == 3
    added = out[out.instrument.eq("SH2")]
    assert len(added) == 1 and added.iloc[0].D2_added_vs_D1
    assert pd.isna(added.iloc[0].actual) and pd.isna(added.iloc[0].D2_total_label)
    assert out[out.instrument.eq("SH1")].actual.eq(0.1).all()
    assert not out.D2_strict_member.any()
