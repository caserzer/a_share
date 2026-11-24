"""Rebuild the weekly CSI300 cohort under the archived H10 deployment universe."""
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
EP39 = HERE.parent
sys.path.insert(0, str(EP39))
from common import KEY, PRIVATE, sha

OUT = HERE / "results/data"
PREVIOUS = EP39 / "results/training_weekly/panel.parquet"
OUTER = EP39 / "results/panel.parquet"
EP37 = next(EP39.parent.glob("37_*"))
ORIGINAL78 = EP37 / "extensions/original78_rankic_20261118"
DICTIONARY = ORIGINAL78 / "outputs/original_78_features.csv"
FEATURES = pd.read_csv(DICTIONARY).feature.tolist()


def deployment_keys(weekly_dates):
    # Reconstruct from all upstream weekly keys, independently of score_eligible,
    # OOF score availability, trade gates, or any future observations.
    archive = pd.read_parquet(PRIVATE / "features.parquet", columns=KEY + FEATURES)
    panel = archive.loc[archive.signal_date.isin(weekly_dates)].copy()
    assert len(FEATURES) == 78 and not panel.duplicated(KEY).any()
    close = pd.read_parquet(PRIVATE / "qfq_close.parquet")
    member = pd.read_parquet(PRIVATE / "daily_members.parquet").reindex_like(close)
    day = close.index.get_indexer(panel.signal_date)
    stock = close.columns.get_indexer(panel.instrument)
    assert day.min() >= 60 and stock.min() >= 0
    dates = close.index.get_indexer(pd.DatetimeIndex(weekly_dates))
    expected_rows = int(member.iloc[dates].fillna(False).to_numpy(dtype=bool).sum())
    assert expected_rows == len(panel) and member.to_numpy()[day, stock].all()
    valid = (np.isfinite(close) & close.gt(0)).rolling(61).sum().eq(61)
    price = close.to_numpy()
    skip55 = price[day - 5, stock] / price[day - 60, stock] - 1
    recent5 = price[day, stock] / price[day - 5, stock] - 1
    eligible = (valid.to_numpy()[day, stock]
                & (skip55 != 0) & (recent5 != 0)
                & panel[FEATURES].notna().mean(axis=1).ge(.8))
    return panel.loc[eligible, KEY]


def recompute_context(old):
    eligible = deployment_keys(old.signal_date.unique())
    panel = eligible.merge(old, on=KEY, how="left", validate="1:1", indicator=True)
    assert panel.pop("_merge").eq("both").all()
    groups = panel.groupby("signal_date")
    panel["ret5_pct"] = groups.ret5.rank(pct=True)
    panel["oversold"] = (panel.ret5.lt(0) & panel.ret5_pct.le(.10)).astype("boolean").where(panel.ret5.notna())
    panel["score_pct"] = groups.score.rank(pct=True)
    panel["pool_ret10"] = groups.ret10.transform("mean")
    panel["target_rank"] = groups.ret10.rank() / (groups.ret10.transform("count") + 1) - .5
    panel["selected"] = pd.array([pd.NA] * len(panel), dtype="boolean")
    scored = panel.loc[panel.score.notna()].sort_values(KEY[:1] + ["score", "instrument"])
    groups = scored.groupby("signal_date")
    panel.loc[scored.index, "selected"] = (
        groups.cumcount(ascending=False) < groups.instrument.transform("size") // 10
    ).to_numpy()
    assert panel.groupby("signal_date").score.apply(lambda x: x.isna().all() or x.notna().all()).all()
    assert panel.selected.isna().equals(panel.score.isna())

    known_path = np.isfinite(panel.hold_low10) & np.isfinite(panel.prior_low5)
    known_return = np.isfinite(panel.ret10)
    panel["breach"] = panel.hold_low10.lt(panel.prior_low5).astype("boolean").where(known_path)
    panel["terminal_loss"] = panel.ret10.lt(0).astype("boolean").where(known_return)
    breach = panel.breach.fillna(False)
    loss = panel.terminal_loss.fillna(False)
    gain = panel.ret10.gt(0)
    conditions = [~known_path & ~known_return, ~known_path, ~known_return,
                  breach & loss, ~breach & gain, breach & gain, ~breach & loss]
    labels = ["路径及终值未知", "路径未知", "终值未知", "持续下跌", "止跌反弹",
              "破低后收涨", "守低仍收跌"]
    panel["outcome"] = np.select([x.to_numpy(dtype=bool) for x in conditions], labels, default="期末持平")
    panel["outcome"] = panel.outcome.astype("category")
    assert (panel.maturity == panel.exit_date).all()
    assert (panel.signal_date < panel.entry_date).all() and (panel.entry_date < panel.maturity).all()
    return panel.sort_values(KEY).reset_index(drop=True)


def reconcile(panel, old, outer):
    shared = sorted(set(outer.signal_date) & set(panel.signal_date))
    assert len(shared) == 48
    before = old[old.signal_date.isin(shared)].set_index(KEY).sort_index()
    actual = panel[panel.signal_date.isin(shared)].set_index(KEY).sort_index()
    frozen = outer[outer.signal_date.isin(shared)].set_index(KEY).sort_index()
    pd.testing.assert_index_equal(actual.index, frozen.index)
    assert len(actual) == 14079
    previous = before.loc[actual.index]
    for field in ["oversold", "breakout", "selected", "entry_date", "maturity"]:
        reference = frozen["exit_date" if field == "maturity" else field]
        assert actual[field].eq(reference).fillna(False).all(), field
    for field in ["score", "score_pct", "ret10", "ret5", "ret5_pct", "prior_low5", "hold_low10"]:
        np.testing.assert_allclose(actual[field], frozen[field], atol=1e-12, rtol=0, equal_nan=True, err_msg=field)
    daily = actual.groupby(level="signal_date").size().rename("aligned_rows").to_frame()
    daily["archived_test_rows"] = frozen.groupby(level="signal_date").size()
    daily["old_weekly_rows"] = before.groupby(level="signal_date").size()
    daily["removed_old_rows"] = daily.old_weekly_rows - daily.aligned_rows
    for name in ["oversold", "selected"]:
        daily["old_" + name + "_diff"] = previous[name].ne(frozen[name]).groupby(level="signal_date").sum()
        daily["aligned_" + name + "_diff"] = actual[name].ne(frozen[name]).groupby(level="signal_date").sum()
    daily["max_abs_original_score_diff"] = (actual.score - frozen.score).abs().groupby(level="signal_date").max()
    return daily


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    old = pd.read_parquet(PREVIOUS)
    prior_receipt = EP39 / "results/training_weekly/receipt.json"
    assert sha(PREVIOUS) == json.loads(prior_receipt.read_text())["panel_sha256"]
    outer = pd.read_parquet(OUTER)
    outer = outer[outer.pool.eq("CSI300")]
    panel = recompute_context(old)
    audit = reconcile(panel, old, outer)
    audit.to_csv(OUT / "shared_dates.csv")
    full_cutoff = outer.signal_date.dt.to_period("Q").max().start_time
    natural = panel.loc[panel.oversold.fillna(False) & panel.maturity.lt(full_cutoff)]
    summaries = []
    for cutoff in sorted(outer.signal_date.dt.to_period("Q").unique()):
        rows = natural[natural.maturity.lt(cutoff.start_time)]
        summaries.append(dict(quarter=str(cutoff), train_cutoff_exclusive=str(cutoff.start_time.date()),
            rows=len(rows), dates=rows.signal_date.nunique(), path_known=int(rows.breach.count()),
            return_known=int(rows.terminal_loss.count()), no_original_score=int(rows.score.isna().sum()),
            original_d10=int(rows.selected.sum()), **{str(k): int(v) for k, v in rows.outcome.value_counts().items()}))
    pd.DataFrame(summaries).to_csv(OUT / "natural_oversold_by_quarter.csv", index=False)
    path = OUT / "weekly.parquet"
    temporary = path.with_suffix(".tmp")
    panel.to_parquet(temporary, index=False, compression="zstd")
    temporary.replace(path)
    sources = [Path(__file__), PREVIOUS, prior_receipt, OUTER, PRIVATE / "features.parquet",
               PRIVATE / "qfq_close.parquet", PRIVATE / "daily_members.parquet", DICTIONARY,
               EP37 / "code/data_models.py", ORIGINAL78 / "run.py"]
    receipt = dict(source_rows=len(old), aligned_rows=len(panel), removed_rows=len(old)-len(panel),
        dates=panel.signal_date.nunique(), shared_dates=len(audit), shared_aligned_rows=int(audit.aligned_rows.sum()),
        shared_removed=int(audit.removed_old_rows.sum()), original_shared_oversold_mismatches=int(audit.old_oversold_diff.sum()),
        aligned_shared_oversold_mismatches=int(audit.aligned_oversold_diff.sum()),
        aligned_shared_d10_mismatches=int(audit.aligned_selected_diff.sum()),
        max_abs_shared_score_error=float(audit.max_abs_original_score_diff.max()),
        last_training_cutoff_exclusive=str(full_cutoff.date()), mature_natural_last_fold=summaries[-1],
        score_definition="Fixed original model OOF score, reranked over aligned same-day eligible universe.",
        target_definition="breach is strict future path low < historical 5-day low; terminal_loss is known H10 return < 0. Unknowns are separate for each endpoint. No future execution gate filter.",
        maturity="Both labels used only for maturity strictly before each quarterly deployment.",
        source_boundary="Historical adjusted prices and historical constituent archives. First-quarter OOF baseline score unavailable; natural trigger rows retained.",
        inputs_sha256={str(p): sha(p) for p in sources}, outputs_sha256={p.name:sha(p) for p in [path,OUT/"shared_dates.csv",OUT/"natural_oversold_by_quarter.csv"]})
    (OUT/"receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False)+"\n")
    print({k:v for k,v in receipt.items() if "sha256" not in k})


if __name__ == "__main__":
    main()

