"""Independently reconcile the corrected population, model fits, decisions and account books."""
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

HERE = Path(__file__).resolve().parent
EP = HERE.parent
RES = HERE / "results"
FIT = RES / "fit"
ACC = RES / "accounts"
PRIOR = EP / "results"
NARROW = next(EP.parent.glob("37_*")) / "extensions/original78_rankic_20261118"
WIDE = Path(os.environ.get("EP39_MARKET", Path.home()/".cache/a_share/ep38_three_track/market"))
COLS = pd.read_csv(NARROW / "outputs/original_78_features.csv").feature.tolist()
KEY = ["signal_date","instrument"]
OUTER = ["pool",*KEY]
DAY = OUTER[:2]
BOOK = ["pool","scope","model","series","segment","cost"]
SEEDS = [39,139,239,339,439]
FITS = ["natural","hard",*[f"random_{s}" for s in SEEDS]]
ARMS = ["full",*FITS,"legacy_local",*[f"shuffle_{s}" for s in SEEDS]]
COSTS = {"zero":0,"base":1,"double":2}


def close(actual, expected, tol=1e-10):
    np.testing.assert_allclose(actual, expected, atol=tol, rtol=0, equal_nan=True)


def indexed(frame, keys):
    return frame.set_index(keys, verify_integrity=True).sort_index()


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def model_checks(panel):
    weekly = pd.read_parquet(RES/"data/weekly.parquet")
    shared_dates = pd.DatetimeIndex(weekly.signal_date.unique()).intersection(panel.signal_date.unique())
    shared = indexed(weekly[weekly.signal_date.isin(shared_dates)],KEY)
    outer300 = indexed(panel[panel.pool.eq("CSI300") & panel.signal_date.isin(shared_dates)],KEY)
    pd.testing.assert_index_equal(shared.index,outer300.index)
    pd.testing.assert_series_equal(shared.oversold,outer300.oversold,check_dtype=False)
    pd.testing.assert_series_equal(shared.selected,outer300.selected,check_dtype=False)
    close(shared.ret10, outer300.ret10)
    # Calculate the lower 10% directly on the complete corrected same-day universe.
    rank = weekly.groupby("signal_date").ret5.rank(pct=True)
    flag = weekly.ret5.lt(0) & rank.le(.10)
    pd.testing.assert_series_equal(flag,weekly.oversold,check_names=False,check_dtype=False)
    natural = indexed(weekly.loc[flag],KEY)
    weights = indexed(pd.read_parquet(FIT/"extra_weight_membership.parquet"),KEY)
    pd.testing.assert_index_equal(weights.index,natural.index)
    labels = {"loss":natural.ret10.lt(0).where(natural.ret10.notna()),
              "breach":natural.hold_low10.lt(natural.prior_low5).where(natural.hold_low10.notna() & natural.prior_low5.notna())}
    for name in FITS[2:]:
        observed = weights[weights[name]].reset_index().groupby(["signal_date","selected"]).size()
        hard = weights[weights.hard].reset_index().groupby(["signal_date","selected"]).size()
        pd.testing.assert_series_equal(observed,hard)
    scores = indexed(pd.read_parquet(FIT/"scores.parquet"),OUTER+["model"])
    assert set(scores.index.get_level_values("model")) == set(FITS)
    validation = panel[panel.oversold.eq(True)]
    for model in FITS:
        pd.testing.assert_index_equal(scores.xs(model,level="model").index,indexed(validation,OUTER).index)
    test_frames=[]
    for pool,src in [("CSI300",NARROW/"local_cache/h10_features.parquet"),("CSI800",WIDE/"wide_features.parquet")]:
        cases=validation[validation.pool.eq(pool)]
        x=pd.read_parquet(src,columns=KEY+COLS,filters=[("signal_date","in",list(cases.signal_date.unique()))])
        joined=cases[OUTER].merge(x,on=KEY,validate="1:1")
        assert len(joined)==len(cases)
        test_frames.append(joined)
    test=pd.concat(test_frames,ignore_index=True)
    params=json.loads((FIT/"models.json").read_text())
    folds=indexed(pd.read_csv(FIT/"folds.csv",parse_dates=["max_maturity","cutoff_exclusive"]),["quarter","head","model"])
    max_prob_error=0.
    max_grad=0.
    checked=0
    for q, future in test.groupby(test.signal_date.dt.to_period("Q")):
        maturity=natural.maturity.lt(q.start_time)
        assert natural[maturity].index.get_level_values("signal_date").max()<q.start_time
        for head, y in labels.items():
            mask=maturity & y.notna()
            train=natural[mask]
            yf=y[mask].to_numpy(dtype=float)
            raw=train[COLS].to_numpy(dtype=float)
            med=np.nan_to_num(np.nanmedian(raw,axis=0),nan=0.)
            filled=np.where(np.isnan(raw),med,raw)
            ave=filled.mean(axis=0)
            sd=filled.std(axis=0)
            sd[sd<1e-12]=1.
            record=params[str(q)][head]
            assert record["columns"]==COLS and set(record["models"])==set(FITS)
            for name, expected in [("median",med),("mean",ave),("sd",sd)]:
                close(record["transform"][name],expected)
            xs=(filled-ave)/sd
            xx=future[COLS].to_numpy(dtype=float)
            xx=(np.where(np.isnan(xx),med,xx)-ave)/sd
            tidx=pd.MultiIndex.from_frame(future[OUTER])
            for model in FITS:
                row=folds.loc[(str(q),head,model)]
                assert (row.known,row.positives,row.negatives,row.mature_oversold)==(len(yf),sum(yf),len(yf)-sum(yf),maturity.sum())
                assert row.cutoff_exclusive==q.start_time and row.max_maturity==train.maturity.max()<q.start_time
                w=np.ones(len(train)) if model=="natural" else 1+weights.loc[train.index,model].to_numpy(dtype=float)
                assert row.doubled==int((w>1).sum()) and row.warmup_rows==int(train.selected.isna().sum())
                c=record["models"][model]
                beta=np.asarray(c["coef"])
                intercept=c["intercept"]
                actual=scores.xs(model,level="model").loc[tidx]
                err=np.abs(expit(np.einsum("ij,j->i",xx,beta)+intercept)-actual[head+"_prob"].to_numpy()).max()
                max_prob_error=max(max_prob_error,float(err))
                assert err < 1e-10
                close(actual[head+"_prior"],yf.mean())
                residual=(expit(np.einsum("ij,j->i",xs,beta)+intercept)-yf)*w
                grad=max(np.max(np.abs(np.einsum("ij,i->j",xs,residual)+beta)),abs(residual.sum()))/w.sum()
                max_grad=max(max_grad,float(grad))
                assert grad<1e-4,(q,head,model,grad)
                checked+=len(future)
    assert len(folds)==322 and checked==len(scores)*2
    return dict(fits=len(folds),probabilities=checked,maximum_probability_error=max_prob_error,
                maximum_normalized_objective_gradient=max_grad,shared_dates=len(shared_dates),shared_stock_dates=len(shared)),scores


def decision_checks(panel,scores):
    plans=pd.read_parquet(RES/"decisions/planned.parquet")
    encoded=plans.pivot(index=OUTER,columns="model",values="score").sort_index()
    assert set(encoded)==set(ARMS) and np.isfinite(encoded.to_numpy()).all()
    orig=indexed(panel,OUTER)
    pd.testing.assert_index_equal(encoded.index,orig.index)
    close(encoded.full,orig.score)
    ranks=encoded.groupby(level=DAY).rank(method="first")
    size=encoded.groupby(level=DAY).full.transform("size")
    picks=ranks.gt(size-size//10,axis=0)
    assert picks.full.eq(orig.selected).all()
    targets=pd.read_parquet(ACC/"targets.parquet")
    for model,t in targets.groupby("model"):
        ix=indexed(t,OUTER).index
        pd.testing.assert_index_equal(ix,picks.index[picks[model]])
        close(indexed(t,OUTER).weight,1/(size.loc[ix]//10))
    assert set(targets.model)==set(ARMS)
    loss=scores.loss_prob.unstack("model")
    old=indexed(pd.read_parquet(PRIOR/"training_fit/scores.parquet",filters=[("model","=","oversold_curated")]),OUTER)
    # Read the actual selected stocks, independently reconstruct the expected target
    # from the original D10, and compare it to every planned and every executed target.
    swaps=pd.read_parquet(RES/"decisions/swaps.parquet")
    assert not swaps.duplicated(DAY+["model","outgoing"]).any()
    assert not swaps.duplicated(DAY+["model","incoming"]).any()
    by_model={(x,y,z):g.sort_values("slot") for (x,y,z),g in swaps.groupby(DAY+["model"])}
    counts=0
    for (pool,date),g in panel.groupby(DAY):
        base=set(g.loc[g.selected,"instrument"])
        review=g[g.selected & g.oversold.eq(True)].sort_values("instrument").instrument.tolist()
        candid=g[~g.selected & g.oversold.eq(False)].sort_values(["score","instrument"],ascending=False).instrument
        risk=loss.loc[(pool,date)].loc[review]
        legacy=old.loc[(pool,date)].loc[review,"score"]
        n=min(int(risk.natural.gt(.50).sum()),len(candid))
        for model in ARMS:
            if model=="full":
                drop=[]
            elif model=="legacy_local":
                drop=legacy.sort_values(kind="stable").index[:n].tolist()
            elif model.startswith("shuffle_"):
                rng=np.random.default_rng([int(model.split("_")[1]),int(pool[3:]),int(date.strftime("%Y%m%d"))])
                drop=[review[i] for i in rng.permutation(len(review))[:n]]
            else:
                drop=risk[model].sort_values(ascending=False,kind="stable").index[:n].tolist()
            incoming=candid.iloc[:len(drop)].tolist()
            s=by_model.get((pool,date,model))
            if len(drop):
                assert drop==s.outgoing.tolist() and incoming==s.incoming.tolist()
            else:
                assert s is None
            active=picks.loc[(pool,date),model]
            assert set(active.index[active])==(base-set(drop)).union(incoming)
            counts+=len(drop)
    assert counts==len(swaps)
    return dict(targets=len(targets),swap_pairs=counts,planned_scores=len(plans),decision_groups=panel.groupby(DAY).ngroups*len(ARMS))


def accounts_checks():
    windows=pd.read_parquet(ACC/"windows.parquet")
    daily=pd.read_parquet(ACC/"daily.parquet")
    orders=pd.read_parquet(ACC/"orders.parquet")
    assert set(windows.model)==set(ARMS) and set(windows.cost)==set(COSTS)
    assert not windows.duplicated(BOOK+["signal_date"]).any() and not daily.duplicated(BOOK+["idx"]).any()
    assert not orders.duplicated(BOOK+["idx","instrument"]).any()
    close(orders.fee,orders.cost.map(COSTS)*np.where(orders.net_amount>0,.001*orders.net_amount,-.002*orders.net_amount))
    trades=orders.assign(buy=orders.net_amount.clip(lower=0),sell=-orders.net_amount.clip(upper=0)).groupby(BOOK+["idx"]).agg(buy=("buy","sum"),sell=("sell","sum"),fees=("fee","sum"),open_nav=("pretrade_nav","first"))
    cash=indexed(daily,BOOK+["idx"])
    assert trades.index.isin(cash.index).all()
    trade_days=trades.reindex(cash.index)
    close(cash[["buy","sell","fees"]],trade_days[["buy","sell","fees"]].fillna(0),tol=1e-9)
    cash["open_nav"]=trade_days.open_nav
    close(cash.cash,1+(cash.sell-cash.buy-cash.fees).groupby(level=BOOK).cumsum(),tol=1e-9)
    for key,w in windows.groupby(BOOK):
        w=w.sort_values("entry_idx")
        book=cash.loc[key]
        start=w.entry_idx.to_numpy()
        assert (np.diff(start)==10).all() and book.index.equals(pd.Index(range(start[0],start[-1]+11)))
        pre=book.loc[start,"open_nav"].to_numpy()
        assert np.isfinite(pre).all()
        end=np.r_[pre[1:],book.nav.iloc[-1]]
        close(w.net,end/pre-1)
        close(w.gross,w.net+w.fee)
        cum_fees=np.r_[0,book.fees.cumsum().to_numpy()]
        cum_traded=np.r_[0,(book.buy+book.sell).cumsum().to_numpy()]
        boundaries=np.r_[start-start[0],len(book)]
        close(w.fee,np.diff(cum_fees[boundaries])/pre)
        close(w.turnover,np.diff(cum_traded[boundaries])/pre)
    common=windows[windows.series.eq("common")]
    counts={}
    for (pool,scope),w in common.groupby(["pool","scope"]):
        keys=["segment","signal_date","entry_date","exit_date"]
        dates=w.loc[w.model.eq("full")&w.cost.eq("base"),keys].sort_values(keys).reset_index(drop=True)
        for _,other in w.groupby(["model","cost"]):
            pd.testing.assert_frame_equal(dates,other[keys].sort_values(keys).reset_index(drop=True))
        counts[pool+"_"+scope]=dates.groupby("segment").size().tolist()
    first=pd.read_parquet(PRIOR/"training_accounts/daily.parquet",filters=[("series","=","native"),("model","=","full")])
    second=daily[daily.series.eq("native")&daily.model.eq("full")]
    before,after=(indexed(x,BOOK+["idx"]) for x in [first,second])
    pd.testing.assert_index_equal(before.index,after.index)
    cols=["cash","nav","fees","sell","buy"]
    close(before[cols],after[cols],tol=1e-9)
    return dict(windows=len(windows),daily_rows=len(daily),orders=len(orders),common_segments=counts,original_native_days=len(before),maximum_original_nav_error=float((before.nav-after.nav).abs().max()))


def review_checks():
    report=RES/"review/comparisons.csv"
    if not report.exists():
        return {"status":"not_yet_generated"}
    summary=pd.read_csv(report,dtype={"segment":str})
    derived=pd.read_parquet(RES/"review/paired_windows.parquet")
    windows=pd.read_parquet(ACC/"windows.parquet",filters=[("series","=","common")])
    fields=["net","fee","turnover","gross"]
    keys=["pool","scope","cost"]
    groups=keys+["model","reference"]
    ref_sets={"weighted_random_mean":[f"random_{s}" for s in SEEDS],"shuffle_mean":[f"shuffle_{s}" for s in SEEDS]}
    books={}
    for group,x in windows.groupby(keys):
        books[group]=x.pivot(index=["segment","signal_date"],columns="model",values=fields)
    receipts=indexed(summary,groups+["segment"])
    intervals=0
    for key,actual in derived.groupby(groups):
        b=books[key[:3]]
        ref=ref_sets.get(key[-1],[key[-1]])
        a=indexed(actual,["segment","signal_date"])
        pd.testing.assert_index_equal(a.index,b.index)
        for col in fields:
            delta=b[col][key[-2]]-b[col][ref].mean(axis=1)
            close(a[col],delta)
        for name,part in [("all",a),*[(str(s),p) for s,p in a.groupby(level="segment")]]:
            record=receipts.loc[key+(name,)]
            assert len(part)==record.n and record["wins"]==(part.net>1e-12).sum() and record["losses"]==(part.net< -1e-12).sum()
            close([record.net_bp,record.fee_bp,record.gross_bp,record.turnover],
                  [part.net.mean()*1e4,part.fee.mean()*1e4,part.gross.mean()*1e4,part.turnover.mean()])
            if key[2]=="base" and key[-2]=="natural" and key[-1] in {"full","shuffle_mean"} and name=="all":
                rng=np.random.default_rng(3901)
                simulated=np.zeros(10000)
                for _,segment in part.groupby(level="segment"):
                    series=segment.net.to_numpy()*1e4
                    n=len(series)
                    blocks=(n+2)//3
                    starts=rng.integers(n,size=(10000,blocks))
                    select=(starts[:,:,None]+np.arange(3))%n
                    simulated+=series[select.reshape(10000,-1)[:,:n]].sum(axis=1)
                close(np.quantile(simulated/len(part),[.025,.975]),[record.low,record.high])
                intervals+=1
    return {"status":"PASS","paired_windows":len(derived),"summary_rows":len(summary),"principal_intervals":intervals}


def main():
    panel=pd.read_parquet(PRIOR/"panel.parquet")
    fits,scores=model_checks(panel)
    selection=decision_checks(panel,scores)
    accounts=accounts_checks()
    comparisons=review_checks()
    external=set()
    for filename,key in [(RES/"data/receipt.json","inputs_sha256"),(FIT/"receipt.json","inputs"),(RES/"decisions/receipt.json","hashes")]:
        for name, expected in json.loads(filename.read_text())[key].items():
            path=Path(name)
            assert sha(path)==expected,(path,filename)
            if not path.is_relative_to(HERE):
                external.add(path)
    external.update([PRIOR/"training_accounts/daily.parquet",EP/"training/accounts_replay.py"])
    internal=[f for f in HERE.rglob("*") if f.is_file() and "__pycache__" not in f.parts
              and (f.suffix not in {".md",".pyc"} or f.name=="PROTOCOL.md") and f.name!="verification.json"]
    result=dict(status="PASS",models=fits,decisions=selection,accounts=accounts,comparisons=comparisons,
        inputs_sha256={str(f):sha(f) for f in sorted(external)},
        revision_sha256={str(f.relative_to(HERE)):sha(f) for f in sorted(internal)})
    (RES/"verification.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print({k:v for k,v in result.items() if not k.endswith("sha256")},flush=True)


if __name__ == "__main__":
    main()

