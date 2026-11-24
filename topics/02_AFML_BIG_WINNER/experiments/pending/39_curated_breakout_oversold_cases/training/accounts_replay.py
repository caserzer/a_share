"""Replay quarterly EP39 scores with EP38's continuous-account implementation."""
import argparse
from pathlib import Path
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd

EP39 = Path(__file__).resolve().parents[1]
EP38 = next(EP39.parent.glob("38_*")) / "three_track"
EP36 = next(EP39.parent.glob("36_*")) / "private"
WIDE = Path(os.environ.get("EP39_MARKET", Path.home() / ".cache/a_share/ep38_three_track/market"))
OUT = EP39 / "results/training_accounts"
sys.path.insert(0, str(EP38))
from experiment import Experiment
from shared import setup, accounts
import account

COSTS = {"base": 1, "zero": 0, "double": 2}
KEY = ["signal_date", "instrument"]


def make_market(pool):
    account.PRIVATE = accounts.PRIVATE = EP36 if pool == "CSI300" else WIDE
    # Market writes its suspension audit; keep that side effect inside EP39.
    accounts.OUT = OUT / pool
    accounts.OUT.mkdir(parents=True, exist_ok=True)
    return setup("flat")


class Replay(Experiment):
    """Only the score provider changes. All fills, maturities and fees use EP38.run."""
    def __init__(self, market, actions, scores):
        self.m, self.actions = market, actions
        self.open, self.close = market.marks["flat"]
        frame = scores.sort_values(KEY)
        self.groups = [(market.days.get_loc(date) + 1, g) for date, g in frame.groupby("signal_date")]
        self.entries = np.array([e for e, _ in self.groups])
        self.ids = [market.symbols.get_indexer(g.instrument) for _, g in self.groups]
        assert min(map(min,self.ids)) >= 0
        self.scores = [(g.score.to_numpy(), None, None, None) for _, g in self.groups]
        # EP38 detail mode echoes labels in an unused return table; none enter replay.
        self.y = [np.full(len(g), np.nan) for _, g in self.groups]
        assert np.isfinite(frame.score).all() and not frame.duplicated(KEY).any()
        assert len(self.entries) == 139 and np.diff(self.entries).min() == np.diff(self.entries).max() == 10

    def calibration(self, weights):
        return self.scores

    def execute(self, start, stop, cost, detail=False, books=None):
        return self.run(start, stop, "original", (1.,)*5, .001*COSTS[cost],
                        .002*COSTS[cost], detail=detail, books=books)


def gap_from(exc, ex):
    payload = exc.args[0]
    if not isinstance(payload,tuple) or payload[0] not in ("open","valuation"):
        raise exc
    reason, date, names = payload
    return {"date": pd.Timestamp(date), "reason": reason,
            "symbols": ",".join(names), "idx": int(ex.m.days.get_loc(date))}


def longest_prefix(ex, start, stop, cost):
    """Retry to an actual common liquidation endpoint; settle terminal fees there."""
    end = stop
    failures = []
    while end > start:
        try:
            ex.execute(start, end, cost)
            return end, failures
        except ValueError as exc:
            gap = gap_from(exc, ex)
            failures.append(gap)
            # A missing close may still permit valuation/liquidation at this morning's open.
            side = "right" if gap["reason"] == "valuation" else "left"
            bound = np.searchsorted(ex.entries + 10, gap["idx"], side=side)
            end = min(end - 1, bound)
    return start, failures


def outside_attribution(ex, windows, orders, books, start, end, mem300):
    """Actual signed P&L attribution of each H10's pretrade and newly filled holdings."""
    result = []
    op = ex.open
    by_day = {}
    for i, g in orders.groupby("idx"):
        by_day[i] = (ex.m.symbols.get_indexer(g.instrument), g.net_amount.to_numpy())
    for t, win in zip(range(start,end),windows.itertuples()):
        e, x = ex.entries[t], ex.entries[t]+10
        u, cash, _ = books[t]
        u = u.copy()
        opening = np.nan_to_num(op[e])
        nav0 = cash + u@opening
        members = mem300[e-1]
        for a,b,listing in ex.actions:
            if e >= listing and u[a] > 0:
                u[b] += u[a]*op[e,a]/op[e,b]
                u[a] = 0.
        last = opening
        pnl = np.zeros(ex.m.n)
        traded = np.zeros(ex.m.n)
        for i in range(e,x+1):
            conversion = [(a,b) for a,b,listing in ex.actions if i==listing and u[a]>0]
            if i not in (e,x) and i not in by_day and not conversion:
                continue
            assert np.isfinite(op[i,u>1e-12]).all()
            price = np.nan_to_num(op[i])
            pnl += u*(price-last)
            for a,b in conversion:
                u[b] += u[a]*price[a]/price[b]
                u[a] = 0.
            if i in by_day and (i < x or t == end-1):
                idx,flow = by_day[i]
                u[idx] += flow/price[idx]
                traded[idx] += abs(flow)
                pnl[idx] -= np.where(flow>0, .001*flow, -.002*flow)
            if i == e:
                outside_weight = (u[~members]@price[~members])/nav0
            last = price
        np.testing.assert_allclose(pnl.sum()/nav0,win.net,atol=1e-9,rtol=0)
        np.testing.assert_allclose(traded.sum()/nav0,win.turnover,atol=1e-9,rtol=0)
        result.append((outside_weight,pnl[~members].sum()/nav0,traded[~members].sum()/nav0))
    return result


def detail(ex,start,end,cost,mem300):
    books = {} if mem300 is not None and cost == "base" else None
    w,d,_,_,o = ex.execute(start,end,cost,True,books)
    windows = pd.DataFrame(w,columns=["entry_idx","net","fee","turnover"])
    d = pd.DataFrame(d,columns=["idx","date","nav","cash","buy","sell","fees"])
    o = pd.DataFrame(o,columns=["idx","instrument","net_amount","pretrade_nav"])
    m = ex.m
    windows["signal_date"] = m.days[windows.entry_idx.to_numpy()-1]
    windows["entry_date"] = m.days[windows.entry_idx.to_numpy()]
    windows["exit_date"] = m.days[windows.entry_idx.to_numpy()+10]
    windows["gross"] = windows.net + windows.fee
    if books is not None:
        attrib = outside_attribution(ex,windows,o,books,start,end,mem300)
        windows[["outside300_weight","outside300_net","outside300_turnover"]] = attrib
    o["date"] = m.days[o.idx.to_numpy(dtype=int)]
    mult = COSTS[cost]
    o["fee"] = np.where(o.net_amount > 0,.001*o.net_amount,-.002*o.net_amount)*mult
    np.testing.assert_allclose(d.cash, 1+(d.sell-d.buy-d.fees).cumsum(), rtol=0, atol=1e-9)
    np.testing.assert_allclose(o.fee.sum(),d.fees.sum(),atol=1e-9)
    np.testing.assert_allclose((1+windows.net).prod(),d.nav.iloc[-1],atol=1e-9)
    stats = dict(start=d.date.iloc[0],end=d.date.iloc[-1],n=len(windows),
                 net_bp=windows.net.mean()*1e4,gross_bp=windows.gross.mean()*1e4,
                 fee_bp=windows.fee.mean()*1e4,turnover=windows.turnover.mean(),
                 paid_fees=d.fees.sum(),nav=d.nav.iloc[-1],
                 cagr=d.nav.iloc[-1]**(252/(len(windows)*10))-1,
                 mdd=(d.nav/d.nav.cummax().clip(lower=1)-1).min())
    return windows,d,o,stats


def replay_pool(pool,scores,panel,outputs):
    m,actions = make_market(pool)
    member300 = pd.read_parquet(EP36/"daily_members.parquet").reindex_like(
        pd.DataFrame(index=m.days,columns=m.symbols)).fillna(False).to_numpy(bool) if pool=="CSI800" else None
    models = {name: Replay(m,actions,g) for name,g in scores.groupby("model")}
    entries = models["full"].entries
    selected = []
    for name,g in scores.groupby("model"):
        expected=panel[KEY].merge(g[KEY],on=KEY,how="outer",indicator=True,validate="1:1")
        assert expected._merge.eq("both").all(), (pool,name)
        g = g.sort_values(["signal_date","score","instrument"])
        group = g.groupby("signal_date",sort=False)
        n=group.score.transform("size")
        picked = g[group.cumcount() >= n-n//10].copy()
        picked["weight"] = 1/picked.groupby("signal_date").score.transform("size")
        selected.append(picked)
    targets=pd.concat(selected).merge(panel[KEY+["selected","scope","in_legacy300","breakout","oversold"]],
                                     on=KEY,how="left",validate="m:1")
    assert targets.loc[targets.model.eq("full"),"selected"].all()
    outputs["targets"].append(targets.rename(columns={"selected":"full_selected"}))
    for scope,start,stop in [("primary",0,100),("later",100,139)]:
        # Cache only discovered prefix lengths, not per-name orders and stock arrays.
        boundaries={}
        tasks=[]
        for name,ex in models.items():
            for cost in COSTS:
                end,fails=longest_prefix(ex,start,stop,cost)
                boundaries[(name,cost,start,stop)]=(end,fails)
                if end>start:
                    tasks.append(("native",1,name,cost,start,end))
                outputs["gaps"].extend(dict(pool=pool,scope=scope,series="native",segment=1,model=name,
                     cost=cost,requested_start=m.days[entries[start]],requested_exit=m.days[entries[stop-1]+10],**f) for f in fails)
        pos=start;segment=0
        while pos<stop:
            segment+=1
            failures=[]
            end=stop
            for name,ex in models.items():
                for cost in COSTS:
                    key=(name,cost,pos,stop)
                    if key not in boundaries: boundaries[key]=longest_prefix(ex,pos,stop,cost)
                    upto,gs=boundaries[key];end=min(end,upto)
                    failures.extend(dict(pool=pool,scope=scope,series="common",segment=segment,model=name,cost=cost,
                        requested_start=m.days[entries[pos]],requested_exit=m.days[entries[stop-1]+10],**f) for f in gs)
            if end>pos:
                tasks.extend(("common",segment,name,cost,pos,end) for name in models for cost in COSTS)
            if end==stop:break
            # Set next fresh common book strictly after earliest failed mark.
            first_bad=min(f["idx"] for f in failures)
            outputs["gaps"].extend(f for f in failures if f["idx"]==first_bad)
            next_start=np.searchsorted(entries, first_bad,side="right")
            assert next_start>pos
            pos=next_start
        grouped={}
        for series,segment,name,cost,a,b in tasks:
            grouped.setdefault((name,cost,a,b),[]).append((series,segment))
        for (name,cost,a,b),uses in grouped.items():
            w,d,o,stats=detail(models[name],a,b,cost,member300)
            for series,segment in uses:
                tags=dict(pool=pool,scope=scope,model=name,cost=cost,series=series,segment=segment)
                for k,data in [("windows",w),("daily",d),("orders",o)]:
                    outputs[k].append(data.assign(**tags))
                outputs["summary"].append(tags|stats)
        print(pool,scope,"segments",segment,"replays",len(grouped),flush=True)


def check_parity(daily,windows,pool):
    prefix="" if pool=="CSI300" else "wide_"
    ref="original" if pool=="CSI300" else "transfer"
    out={}
    for scope in ["primary","later"]:
        meta=(daily.pool==pool)&(daily.series=="native")&(daily.model=="full")&(daily.scope==scope)
        actual=daily[meta]
        archive=pd.read_parquet(EP38/"results"/(prefix+"daily.parquet"),
                   filters=[("model","=",ref),("scope","=",scope)])
        x=actual.merge(archive,on=["date","cost"],validate="1:1",suffixes=("","_archive"))
        assert len(x)==len(archive)==len(actual)
        for k in ["nav","cash","fees","buy","sell"]:
            np.testing.assert_allclose(x[k],x[k+"_archive"],atol=1e-9,rtol=0)
        out[scope]=dict(days=len(x)//3,max_abs_nav_error=float((x.nav-x.nav_archive).abs().max()))
        if pool=="CSI800":
            y=windows.query("pool==@pool and series=='native' and scope==@scope and cost=='base' and model=='full'")
            a=pd.read_csv(EP38/"results/wide_coverage.csv",parse_dates=["signal_date"]).query("scope==@scope and model==@ref")
            z=y.merge(a,on="signal_date",validate="1:1")
            assert len(z)==len(a)==len(y)
            for k,col in [("outside300_weight","outside300_weight"),("outside300_net","outside300_contribution"),("outside300_turnover","outside300_traded")]:
                left=k+"_x" if k==col else k; right=col+"_y" if k==col else col
                np.testing.assert_allclose(z[left],z[right],atol=1e-9,rtol=0)
    return out


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--scores",type=Path,default=EP39/"results/training_fit/scores.parquet")
    args=parser.parse_args()
    scores=pd.read_parquet(args.scores,columns=["pool","model",*KEY,"score"])
    panel=pd.read_parquet(EP39/"results/panel.parquet",columns=["pool",*KEY,"selected","scope","in_legacy300","breakout","oversold"])
    outputs={k:[] for k in ["targets","orders","windows","daily","summary","gaps"]}
    for pool in ["CSI300","CSI800"]:
        replay_pool(pool,scores[scores.pool==pool],panel[panel.pool==pool],outputs)
    frames={k:pd.concat(outputs[k],ignore_index=True) for k in ["targets","orders","windows","daily"]}
    parity={pool:check_parity(frames["daily"],frames["windows"],pool) for pool in ["CSI300","CSI800"]}
    for k,f in frames.items():
        f.to_parquet(OUT/(k+".parquet"),index=False)
    pd.DataFrame(outputs["summary"]).to_csv(OUT/"account_summary.csv",index=False)
    pd.DataFrame(outputs["gaps"]).to_csv(OUT/"gaps.csv",index=False)
    with args.scores.open("rb") as handle:parity["scores_sha256"]=hashlib.file_digest(handle,"sha256").hexdigest()
    (OUT/"parity.json").write_text(json.dumps(parity,indent=2)+"\n")
    print(parity,flush=True)

if __name__=="__main__":
    main()
