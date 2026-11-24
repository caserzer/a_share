"""Rebuild weekly CSI300 training rows and strictly prior-quarter case-matching scores."""
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd

EP39 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EP39))
from common import KEY, PRIVATE, metadata, sha

EP37 = next(EP39.parent.glob("37_*"))
ORIGINAL = EP37 / "extensions/original78_rankic_20261118"
sys.path.insert(0, str(ORIGINAL))
from model import ridge, predict

OUT = EP39 / "results/training_weekly"
DICTIONARY = ORIGINAL / "outputs/original_78_features.csv"
COLS = pd.read_csv(DICTIONARY).feature.to_list()
BASE = "RANK_MSE_78"
FIELDS = ["qfq_close", "qfq_high", "qfq_low", "qfq_open", "open", "opening_trade_status_v2", "limits/daily"]


def base_panel(last_cutoff):
    f = pd.read_parquet(PRIVATE/"features.parquet", columns=KEY + COLS + ["score_eligible"])
    y = pd.read_parquet(PRIVATE/"labels.parquet", columns=KEY + ["h10", "target_z", "h10_mature", "entry_date"])
    f = f[f.score_eligible & (f.signal_date < last_cutoff)].merge(y, on=KEY, validate="1:1")
    f = f.rename(columns={"h10_mature": "maturity"})
    # Keep all signal-eligible names in percentile/seat calculations, even if the future quote is unavailable.
    valid = f.target_z.notna()
    ranks = f.loc[valid].groupby("signal_date").h10
    f["target_rank"] = ranks.rank(method="average") / (ranks.transform("count") + 1) - .5
    return f


def rolling_scores(f, expected):
    f["score"] = np.nan
    audit = []
    grouped = f.groupby(f.signal_date.dt.to_period("Q"))
    for quarter, eligible in grouped:
        matured = f[f.maturity.lt(quarter.start_time) & f.target_rank.notna()]
        if len(matured):
            assert matured.maturity.max() < quarter.start_time <= eligible.signal_date.min()
            assert matured.signal_date.max() < quarter.start_time
            fit = ridge(matured, COLS, "target_rank")
            f.loc[eligible.index,"score"] = predict(eligible[COLS], fit)
        audit.append(dict(quarter=str(quarter), first_signal=eligible.signal_date.min(),
                          last_signal=eligible.signal_date.max(), eligible_rows=len(eligible),
                          train_rows=len(matured), train_dates=matured.signal_date.nunique(),
                          max_maturity=matured.maturity.max(), oof_available=bool(len(matured))))
    receipts = pd.DataFrame(audit)
    # Check all outer-training cutoffs, including the last, which has no later scoring rows in this file.
    for row in expected.itertuples():
        cutoff = pd.Period(row.fold,freq="Q").start_time
        mat = f[f.maturity.lt(cutoff) & f.target_rank.notna()]
        assert len(mat)==row.train_rows and mat.signal_date.nunique()==row.train_dates, row.fold
        assert mat.maturity.max()==pd.Timestamp(row.max_label_maturity),row.fold
    f["score_pct"] = f.groupby("signal_date").score.rank(pct=True)
    f["selected"] = pd.array([pd.NA]*len(f),dtype="boolean")
    # Same stable score / instrument tie break and floor(n/10) seats as the original deciles.
    scored=f[f.score.notna()].sort_values(["signal_date","score","instrument"],kind="stable")
    groups=scored.groupby("signal_date")
    selected=(groups.cumcount(ascending=False)<(groups.instrument.transform("size")//10))
    f.loc[scored.index,"selected"] = selected.to_numpy()
    archived=pd.read_parquet(ORIGINAL/"local_cache/weekly_predictions.parquet",columns=KEY+[BASE])
    v=f[KEY+["score"]].merge(archived,on=KEY,validate="1:1")
    assert len(v)==(archived.signal_date<=f.signal_date.max()).sum()
    np.testing.assert_allclose(v.score,v[BASE],rtol=0,atol=1e-10)
    return receipts, len(v), (v.score-v[BASE]).abs().max()


def case_fields(p):
    close=pd.read_parquet(PRIVATE/"qfq_close.parquet")
    idx, col = close.index.get_indexer(p.signal_date), close.columns.get_indexer(p.instrument)
    assert idx.min()>=20 and col.min()>=0 and idx.max()+11<len(close.index)

    def read(name):
        field=pd.read_parquet(PRIVATE/(name+".parquet"))
        assert field.index.equals(close.index) and field.columns.equals(close.columns)
        return field

    def at(frame,increment=0):
        return frame.to_numpy()[idx+increment,col]

    high,low,op=[read(name) for name in ("qfq_high","qfq_low","qfq_open")]
    np.testing.assert_array_equal(p.entry_date,close.index[idx+1])
    np.testing.assert_array_equal(p.maturity,close.index[idx+11])
    p["close"]=at(close)
    p["entry_open"]=at(op,1)
    p["exit_open"]=at(op,11)
    p["exit_date"]=p.maturity
    p["ret10"]=p.exit_open/p.entry_open-1
    np.testing.assert_allclose(p.ret10,p.h10,atol=1e-12,rtol=0,equal_nan=True)
    p["entry_gap"]=p.entry_open/p.close-1
    p["prior_high20"]=at(high.shift(1).rolling(20).max())
    p["prior_low5"]=at(low.rolling(5).min())
    p["ret5"]=p.close/at(close,-5)-1
    np.testing.assert_allclose(p.ret5,p.mom5,equal_nan=True,atol=1e-12,rtol=0)
    p["breakout_pct"]=p.close/p.prior_high20-1
    p["breakout"]=p.close.gt(p.prior_high20).astype("boolean").mask(p.breakout_pct.isna())
    context=p.groupby("signal_date")
    p["ret5_pct"]=context.ret5.rank(pct=True)
    p["oversold"]=(p.ret5.lt(0)&p.ret5_pct.le(.10)).astype("boolean").mask(p.ret5.isna())
    p["pool_ret10"]=context.ret10.transform("mean")
    lo_path=np.column_stack([at(low,j) for j in range(1,11)])
    close_path=np.column_stack([at(close,j) for j in range(1,11)])
    p["hold_low10"]=lo_path.min(axis=1)
    p["mae10"]=p.hold_low10/p.entry_open-1
    known=np.isfinite(close_path).all(axis=1)&p.prior_high20.notna()
    above=(close_path>=p.prior_high20.to_numpy()[:,None]).sum(axis=1)
    p["above_high_days"]=np.where(known,above,np.nan)
    status=read("opening_trade_status_v2")
    raw=read("open")
    limits=pd.read_parquet(PRIVATE/"limits/daily.parquet")
    limits["instrument"]=limits.ts_code.str[-2:]+limits.ts_code.str[:6]
    limits["date"]=pd.to_datetime(limits.trade_date)
    quotes=limits.set_index(["date","instrument"])
    assert quotes.index.is_unique
    for lag,out,side in ((1,"entry_buy","buy"),(11,"exit_sell","sell")):
        bound=quotes.reindex(pd.MultiIndex.from_arrays([close.index[idx+lag],p.instrument]))
        up,down=bound.up_limit.to_numpy(float),bound.down_limit.to_numpy(float)
        px,adj,st=at(raw,lag),at(op,lag),at(status,lag)
        known=np.isfinite(px)&(px>0)&np.isfinite(adj)&(adj>0)&np.isfinite(up)&np.isfinite(down)&(up>down)&(st==1)
        gate=pd.array(px<up-1e-6 if side=="buy" else px>down+1e-6,dtype="boolean")
        gate[~known]=pd.NA
        gate[st==0]=False
        p[out]=gate
    p=metadata(p)
    p[["industry","name"]]=p[["industry","name"]].fillna("未知")
    p["scope"]="train"
    p["pool"]="CSI300"
    return p


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    outer_dates=pd.read_parquet(EP39/"results/panel.parquet",columns=["signal_date"])
    last_cutoff=outer_dates.signal_date.dt.to_period("Q").max().start_time
    foldfile=ORIGINAL/"outputs/folds.csv"
    outer_folds=pd.read_csv(foldfile)
    expected=outer_folds[(outer_folds.model==BASE) & (pd.PeriodIndex(outer_folds.fold,freq="Q").start_time<=last_cutoff)]
    assert len(expected)==outer_dates.signal_date.dt.to_period("Q").nunique()
    p=base_panel(last_cutoff)
    audit,n_check,max_err=rolling_scores(p,expected)
    p=case_fields(p)
    assert len(p)==len(p.drop_duplicates(KEY))
    assert p.target_rank.isna().equals(p.target_z.isna())
    assert p.selected.isna().equals(p.score.isna())
    path=OUT/"panel.parquet"
    temp=path.with_suffix(".tmp")
    p.to_parquet(temp,index=False,compression="zstd")
    audit.to_csv(OUT/"oof_folds.csv",index=False)
    files=[PRIVATE/(name+".parquet") for name in ["features","labels","industry",*FIELDS]]
    files.extend([DICTIONARY,foldfile,ORIGINAL/"model.py",ORIGINAL/"local_cache/weekly_predictions.parquet",
                  EP39/"results/panel.parquet",EP39/"common.py",Path(__file__)])
    receipt=dict(rows=len(p),signal_dates=p.signal_date.nunique(),first_signal=str(p.signal_date.min().date()),
                 last_signal=str(p.signal_date.max().date()),last_outer_train_cutoff=str(last_cutoff.date()),
                 eligible_rows_unscored=int(p.score.isna().sum()),first_oof=str(p.loc[p.score.notna(),"signal_date"].min().date()),
                 available_target_rows=int(p.target_rank.notna().sum()),outer_folds_reconciled=len(expected),
                 archived_score_rows=n_check,max_archived_score_error=max_err,
                 inputs={str(f):sha(f) for f in files},panel_sha256=sha(temp))
    (OUT/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    temp.replace(path)
    print({k:v for k,v in receipt.items() if k!="inputs"},flush=True)


if __name__=="__main__":
    main()
