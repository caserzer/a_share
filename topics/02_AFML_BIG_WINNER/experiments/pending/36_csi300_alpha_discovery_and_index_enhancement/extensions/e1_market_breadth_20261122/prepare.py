"""Prepare historical predictors, reference matches and placebo targets before evaluation."""
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

ROOT = Path(__file__).resolve().parent
EP = ROOT.parents[1]
sys.path.insert(0, str(EP / "src"))
from common import PRIVATE, OUT, sha, save_json
from train import TrainTransform
from backtest import Inputs
from e1_return_attribution import industry_map

D = ROOT / "results"
OLD = OUT / "diagnostics/e1_down_down_account_20261117"
MODELS = ["E1", "flag", "interaction"]
KEY = ["signal_date", "instrument"]
SEED = 361122
PRIMARY = pd.Timestamp("2025-03-03")
END = pd.Timestamp("2026-10-16")
PREDS = OUT / "fold_predictions/expanding"


def build():
    f = pd.read_parquet(PRIVATE / "features.parquet")
    prices = pd.read_parquet(PRIVATE / "qfq_close.parquet")
    pos = prices.index.get_indexer(f.signal_date)
    sym = prices.columns.get_indexer(f.instrument)
    assert min(pos) >= 0 and min(sym) >= 0
    array = prices.to_numpy()
    for name, recent, previous in [("trend", 5, 60), ("short", 0, 5)]:
        f[name] = np.where(pos >= previous, array[pos-recent, sym] / array[pos-previous, sym]-1, np.nan)
    known = f.trend.notna() & f.short.notna()
    f["dd"] = ((f.trend < 0) & (f.short < 0)).astype(float).where(known)
    f["breadth"] = f.dd.where(f.score_eligible).groupby(f.signal_date).transform("mean")
    f["product"] = f.dd * f.breadth
    return f


def train_models(f):
    dictionary = pd.read_csv(EP / "configs/feature_dictionary.csv")
    core = dictionary.loc[dictionary.group.eq("core"), "feature"].tolist()
    assert len(core) == 78
    labels = pd.read_parquet(PRIVATE / "labels.parquet", columns=KEY + ["h10_mature", "target_z"])
    fits, predictions = [], []
    for file in sorted(PREDS.glob("*.parquet")):
        quarter = pd.Period(file.stem, freq="Q")
        old = pd.read_parquet(file, columns=KEY + ["score"], filters=[("model_id", "==", "E1")])
        receipt = json.loads((OUT / f"manifests/expanding_{quarter}.json").read_text())
        mature = labels.loc[labels.h10_mature < quarter.start_time].dropna(subset=["target_z"])
        train = f.loc[f.score_eligible & (f.signal_date < quarter.start_time)].merge(mature, on=KEY, validate="1:1")
        assert len(train) == receipt["train_rows"] and train.h10_mature.max() < quarter.start_time
        test = f.loc[f.score_eligible & (f.signal_date.dt.to_period("Q") == quarter)]
        pred = test[KEY + ["dd", "short", "trend", "breadth"]].copy()
        for model, extra in zip(MODELS, [[], ["dd"], ["dd", "product"]]):
            cols = core + extra
            t = TrainTransform().fit(train[cols])
            ridge = Ridge(alpha=10).fit(t.transform(train[cols]), train.target_z)
            scores = ridge.predict(t.transform(test[cols]))
            pred[model] = scores
            fits.append(dict(quarter=str(quarter), model=model, n=len(train), max_maturity=train.h10_mature.max(),
                             flag_coef=ridge.coef_[78] if extra else None,
                             interaction_coef=ridge.coef_[79] if len(extra)==2 else None))
        check = pred.merge(old.dropna(), on=KEY, validate="1:1")
        error = abs(check.E1-check.score).max()
        assert len(check) == len(test) == old.score.count() and error < 1e-8, (quarter, error)
        fits[-3]["baseline_replay_error"] = error
        predictions.append(pred)
    pd.DataFrame(fits).to_csv(D / "folds.csv", index=False)
    return pd.concat(predictions, ignore_index=True)


def prepare_targets(p):
    inp = Inputs()
    rng = np.random.default_rng(SEED)
    old = pd.read_csv(OLD / "selection.csv", parse_dates=["signal_date"])
    schedule = pd.read_csv(OLD / "schedule.csv", parse_dates=["signal_date"])
    targets, matches, baskets, monthly = [], [], [], []
    for date, g in p[p.signal_date.isin(schedule.signal_date)].groupby("signal_date"):
        g = g.set_index("instrument").sort_index()
        industry = industry_map(inp, date)
        g["industry"] = industry.reindex(g.index)
        k = len(g) // 5
        for model in MODELS:
            top = g.sort_values([model, "instrument"]).tail(k).index
            g[model+"_q5"] = g.index.isin(top)
        q = g[g.E1_q5]
        orig = old[old.signal_date == date].set_index("instrument")
        assert set(q.index)==set(orig.index) and np.array_equal(q.dd.eq(1), orig.selected.reindex(q.index))
        dd = q[q.dd.eq(1)]
        non = g[~g.E1_q5 & g.dd.eq(1)]
        sd = g.groupby("industry")[["trend", "short"]].std(ddof=0)
        count = len(dd)
        monthly.append(dict(signal_date=date, eligible=len(g), known=g.dd.count(), breadth=g.dd.mean(),
                            breadth_ex_q5=g.loc[~g.E1_q5,"dd"].mean(), q5=k, count=count,
                            q5_share=q.dd.mean(), dd_max_stock=1/count if count else np.nan,
                            dd_max_industry=dd.industry.value_counts(normalize=True).max(),
                            q5_max_industry=q.industry.value_counts(normalize=True).max()))
        for name, row in dd.iterrows():
            pool = non[non.industry.eq(row.industry)]
            if row.industry=="UNKNOWN" or pool.empty:
                continue
            deviations = (pool[["trend","short"]]-row[["trend","short"]].astype(float)).abs()
            # Zero industry dispersion implies exact equality on that dimension.
            scales = sd.loc[row.industry]
            feasible = deviations.le(.5*scales).all(axis=1)
            if feasible.any():
                distance = deviations.loc[feasible].div(scales.replace(0,1)).pow(2).sum(axis=1)
                peer = distance.idxmin()
                matches.append(dict(signal_date=date, selected=name, peer=peer, industry=row.industry,
                                    distance=float(np.sqrt(distance.loc[peer]))))
        # Index of each draw is stable across months; overlapping target and control is intentional.
        groups = [(q.index[q.industry == ind].to_numpy(), len(group)) for ind,group in dd.groupby("industry")]
        for draw in range(100):
            picks = [rng.choice(universe, size=n, replace=False) for universe,n in groups]
            names = np.concatenate(picks).tolist() if picks else []
            baskets.append(dict(signal_date=date,draw=draw,instruments="|".join(names)))
        targets.append(g.reset_index().assign(signal_date=date))
    pd.DataFrame(monthly).to_csv(D/"schedule.csv",index=False)
    pd.DataFrame(matches).to_csv(D/"matches.csv",index=False)
    pd.DataFrame(baskets).to_csv(D/"random_targets.csv.gz",index=False)
    pd.concat(targets).to_parquet(D/"monthly_candidates.parquet",index=False)


def main():
    D.mkdir(exist_ok=True)
    if (D/"selection.json").exists():
        raise RuntimeError("Sealed selection exists; use a separate output directory for a new run")
    inputs = [PRIVATE/(n+".parquet") for n in ["features","labels","qfq_close","qfq_open","open",
                "opening_trade_status_v2","daily_members","industry","limits/daily","weights/snapshots","suspensions/daily"]]
    inputs += list(PREDS.glob("*.parquet")) + list((OUT/"manifests").glob("expanding_20*Q?.json"))
    inputs += [OLD/(n+".csv") for n in ["selection","schedule","DD_daily","E1_daily"]]
    inputs += [EP/"configs/feature_dictionary.csv", PRIVATE/"net_excess_20261116/H00300.CSI.json"]
    inputs += [EP/"src"/(n+".py") for n in ["train","backtest","alpha_economics","portfolio","common",
                                             "suspension_sensitivity","e1_return_attribution"]]
    inputs += [ROOT/"PROTOCOL.md", Path(__file__)]
    save_json(D/"inputs.json",{str(s.relative_to(EP)):sha(s) for s in sorted(inputs)})
    p = train_models(build())
    p.to_parquet(D/"weekly_predictions.parquet",index=False)
    prepare_targets(p)
    save_json(D/"selection.json",{s.name:sha(s) for s in sorted(D.iterdir()) if s.is_file()})
    print("Sealed",len(p),"weekly predictions and all monthly target sets",flush=True)


if __name__=="__main__":
    main()
