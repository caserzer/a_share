import numpy as np
import pandas as pd

from labels_and_maturity import infer_labels
from volume_price_features import build_features


def test_future_scalar_qfq_reanchor_preserves_features(bars):
    old = build_features(bars, bars.date)
    for col in ["qfq_open", "qfq_high", "qfq_low", "qfq_close"]:
        bars[col] *= 0.1
    new = build_features(bars, bars.date)
    for col in old.select_dtypes(include=["number"]).columns:
        np.testing.assert_allclose(old[col], new[col], rtol=1e-10, atol=1e-10, equal_nan=True)


def test_future_factor_step_cannot_rewrite_old_features(bars):
    before = build_features(bars, bars.date)
    bars.loc[400:, "qfq_divisor"] = 2
    bars.loc[400:, ["qfq_open", "qfq_close", "qfq_high", "qfq_low"]] /= 2
    after = build_features(bars, bars.date)
    pd.testing.assert_frame_equal(before.iloc[:400], after.iloc[:400])


def test_unreconciled_code_chain_blocks_label(bars):
    bars.loc[310:, "factor_chain_id"] = "new_unmatched_code"
    label = infer_labels(bars, bars.date, [bars.date.iloc[300]], 20)
    assert pd.isna(label.value.iloc[0])
    assert label.reason.iloc[0] == "UNRECONCILED_CODE_CHANGE_FACTOR_SCALE"


def test_unreconciled_code_chain_blocks_feature_ratios(bars):
    bars.loc[310:, "factor_chain_id"] = "new_unmatched_code"
    f = build_features(bars,bars.date)
    assert pd.isna(f.mom20.iloc[315])
    assert pd.isna(f.breakthrough_strength.iloc[315])


def test_volume_split_does_not_change_turnover_sensitivity(bars):
    old = build_features(bars, bars.date)
    bars.loc[350:, "volume"] *= 2
    new = build_features(bars, bars.date)
    pd.testing.assert_series_equal(old.mavd_turnover, new.mavd_turnover)
    assert abs(old.mavd.iloc[400]-new.mavd.iloc[400]) > 0.1
