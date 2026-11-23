from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec
import sys
import numpy as np
import pandas as pd

here = Path(__file__).resolve().parent
out = here / "results"
parent = here.parent / "88_selected_margin_subindustry/results"
engine_path = here.parent / "64_mature_group_switch/account.py"
spec = spec_from_file_location("engine", engine_path)
engine = module_from_spec(spec)
spec.loader.exec_module(engine)
from core import dump, sha

targets_file = parent / "targets.parquet"
targets = pd.read_parquet(targets_file, filters=[("model","in",["stock_weight","original"])])
files = [targets_file, parent/"receipt.json", engine_path, Path(__file__), here/"PROTOCOL.md"]
engine.accounts.OUT = out
market, actions = engine.setup("flat")
op, cl = market.marks["flat"]
monthly_parts = []
daily_parts = []
for scope in ["2019","2020_flat","primary","later"]:
    path = parent / (scope+"_daily.parquet")
    files.append(path)
    reference = pd.read_parquet(path)
    for (phase, model), frame in reference[reference.model.isin(["stock_weight","original"])].groupby(["phase","model"]):
        frame = frame.sort_values("idx")
        first, last = int(frame.idx.min()), int(frame.idx.max())
        group = targets[(targets.phase == phase) & (targets.model == model) & targets.entry_idx.between(first,last-1)]
        plans = {i:(market.symbols.get_indexer(g.instrument),g.weight.to_numpy()) for i,g in group.groupby("entry_idx")}
        assert min(plans)==first and max(plans)+10==last
        units = np.zeros(market.n)
        expiry = np.full(market.n,-1)
        previous = np.zeros(market.n)
        prev_nav = 1.
        month = None
        for row in frame.itertuples():
            i = row.idx
            price = np.nan_to_num(op[i])
            entering = np.zeros(market.n)
            leaving = np.zeros(market.n)
            sell = (units>0)&(expiry<=i)&market.sell[i]
            retained = (units>0)&~sell
            leaving[sell] = units[sell]*price[sell]
            if i in plans:
                idx, weights = plans[i]
                w = np.zeros(market.n)
                w[idx] = weights
                entering = engine.buy_amounts(w*(market.buy[i]&market.members[i-1]&~retained),
                    prev_nav-previous.sum()+leaving.sum()*.998,units[retained]@price[retained],.001)
            routed = leaving.copy()
            for old,new,listing in actions:
                if i>=listing:
                    routed[new]+=routed[old]
                    routed[old]=0
            net = entering-routed
            fee = np.maximum(net,0)*.001 + np.maximum(-net,0)*.002
            units[sell]=0
            expiry[sell]=-1
            buy = entering>0
            units[buy]=entering[buy]/price[buy]
            expiry[buy]=i+10
            mark = op[i] if i==last else cl[i]
            assert np.isfinite(mark[units>0]).all()
            values = units*np.nan_to_num(mark)
            pnl = values-previous+leaving-entering-fee
            np.testing.assert_allclose([prev_nav+pnl.sum(),fee.sum(),net.clip(min=0).sum(),(-net).clip(min=0).sum()],
                [row.nav,row.fee,row.buy,row.sell],atol=1e-10,rtol=0)
            current_month = row.date.to_period("M")
            if month != current_month:
                month = current_month
                month_start = prev_nav
            ix = np.flatnonzero((pnl!=0)|(entering!=0)|(leaving!=0)|(fee!=0))
            daily_parts.append(pd.DataFrame(dict(scope=scope,phase=phase,model=model,date=row.date,month=str(month),
                instrument=market.symbols[ix],pnl=pnl[ix]/month_start,fee=fee[ix]/month_start,
                purchased=entering[ix]/month_start,sold=leaving[ix]/month_start)))
            previous=values
            prev_nav=row.nav
        complete = frame.date.dt.to_period("M").drop_duplicates().iloc[1:-1].astype(str)
        monthly_parts.append(pd.DataFrame(dict(scope=scope,phase=phase,model=model,month=complete)))
daily=pd.concat(daily_parts,ignore_index=True)
daily.to_parquet(out/"stock_days.parquet",index=False)
complete=pd.concat(monthly_parts)
keys=["scope","phase","month","model"]
joint=(complete.groupby(["scope","month"]).size()==20)
joint=joint[joint].reset_index()[["scope","month"]]
stocks=(daily.merge(complete,on=keys,how="inner",validate="m:1").merge(joint,on=["scope","month"])
        .groupby(["scope","month","instrument","model"])[["pnl","fee","purchased","sold"]].sum()/10)
wide=stocks.unstack("model",fill_value=0)
effects=wide.xs("stock_weight",axis=1,level="model")-wide.xs("original",axis=1,level="model")
effects*=1e4
effects.to_csv(out/"stock_month_bp.csv")
totals=effects.pnl.groupby(["scope","month"]).sum()
issuers=effects.pnl.groupby(["scope","instrument"]).sum()
summary=[]
ref_file=parent/"summary.csv"
files.append(ref_file)
ref=pd.read_csv(ref_file).query('model=="stock_weight" and ref=="original"').set_index("scope")
for scope,months in totals.groupby(level="scope"):
    months=months.droplevel("scope")
    company=issuers.loc[scope].sort_values(ascending=False)
    np.testing.assert_allclose(months.mean(),ref.at[scope,"monthly"],atol=1e-7)
    summary.append(dict(scope=scope,months=len(months),mean=months.mean(),ex3stocks=months.mean()-company.head(3).sum()/len(months),
        leaders=",".join(company.head(3).index),best=months.idxmax(),best_bp=months.max(),worst=months.idxmin(),worst_bp=months.min()))
pd.DataFrame(summary).to_csv(out/"summary.csv",index=False)
issuers.rename("sum_monthly_bp").to_csv(out/"issuer_totals.csv")
dump(out/"receipt.json",{str(f):sha(f) for f in files+[out/n for n in ["stock_days.parquet","stock_month_bp.csv","summary.csv","issuer_totals.csv"]]})
