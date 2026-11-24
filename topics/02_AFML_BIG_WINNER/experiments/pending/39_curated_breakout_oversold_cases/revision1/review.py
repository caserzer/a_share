"""Summarize matched H10 accounts and attach realized outcomes to frozen swap decisions."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
EP = HERE.parent
sys.path.insert(0, str(EP/"training"))
from compare import interval

RES = HERE/"results"
OUT = RES/"review"
SEEDS = (39, 139, 239, 339, 439)
WEIGHTED = [f"random_{s}" for s in SEEDS]
SHUFFLED = [f"shuffle_{s}" for s in SEEDS]
REFERENCES = {"full":["full"], "natural":["natural"], "legacy_local":["legacy_local"],
              "weighted_random_mean":WEIGHTED, "shuffle_mean":SHUFFLED}


def account_contrasts():
    windows = pd.read_parquet(RES/"accounts/windows.parquet")
    common = windows[windows.series.eq("common")]
    contrasts = {"natural":["full","shuffle_mean","legacy_local"],
                 "hard":["full","natural","weighted_random_mean","shuffle_mean"],
                 "legacy_local":["full","shuffle_mean"]}
    outputs, summaries = [], []
    for (pool, scope, cost), g in common.groupby(["pool","scope","cost"]):
        indices = ["segment","signal_date"]
        table = g.pivot(index=indices, columns="model", values=["net","fee","turnover","gross"])
        assert not table.isna().any().any()
        for model, names in contrasts.items():
            for ref in names:
                fields = {}
                for col in ["net","fee","gross","turnover"]:
                    fields[col] = table[col][model] - table[col][REFERENCES[ref]].mean(axis=1,skipna=False)
                dif = pd.DataFrame(fields).reset_index()
                dif["net_bp"] = dif.net*1e4
                dif["gross_bp"] = dif.gross*1e4
                dif["fee_bp"] = dif.fee*1e4
                desc = dict(pool=pool,scope=scope,cost=cost,model=model,reference=ref)
                outputs.append(dif.assign(**desc))
                for seg, part in [("all",dif), *[(str(i),h) for i,h in dif.groupby("segment")]]:
                    lo, hi = interval(part)
                    summaries.append(desc | dict(segment=seg,n=len(part),segments=part.segment.nunique(),
                        net_bp=part.net_bp.mean(),low=lo,high=hi,gross_bp=part.gross_bp.mean(),
                        fee_bp=part.fee_bp.mean(),turnover=part.turnover.mean(),
                        wins=int(part.net.gt(1e-12).sum()),losses=int(part.net.lt(-1e-12).sum()),
                        within_numerical_tie=int(part.net.abs().le(1e-12).sum())))
    pd.concat(outputs, ignore_index=True).to_parquet(OUT/"paired_windows.parquet",index=False)
    pd.DataFrame(summaries).to_csv(OUT/"comparisons.csv",index=False)
    return common[common.cost.eq("base") & common.model.eq("full")][["pool","scope",*indices]]


def evaluate_seats(common_dates):
    panel = pd.read_parquet(EP/"results/panel.parquet",columns=["pool","signal_date","instrument","name",
        "ret10","hold_low10","prior_low5","entry_buy","exit_sell","selected","oversold"])
    panel["breach"] = (panel.hold_low10 < panel.prior_low5).astype("boolean").mask(
        panel.hold_low10.isna() | panel.prior_low5.isna())
    panel["fillable"] = panel.entry_buy.fillna(False) & panel.exit_sell.fillna(False)
    keys=["pool","signal_date","instrument"]
    swap = pd.read_parquet(RES/"decisions/swaps.parquet")
    for side in ["outgoing","incoming"]:
        fields = ["name","ret10","breach","entry_buy","exit_sell","fillable","selected","oversold"]
        quotes = panel[keys+fields].rename(columns={"instrument":side,**{f:f"{side}_{f}" for f in fields}})
        swap = swap.merge(quotes,on=["pool","signal_date",side],how="left",validate="m:1")
    assert swap.outgoing_selected.all() and swap.outgoing_oversold.all()
    assert not swap.incoming_selected.any() and not swap.incoming_oversold.any()
    swap["both_fillable"] = (swap.outgoing_fillable & swap.incoming_fillable &
        swap.outgoing_ret10.notna() & swap.incoming_ret10.notna())
    swap["equal_cash_bp"] = ((swap.incoming_ret10-swap.outgoing_ret10)*.998/1.001*1e4).where(swap.both_fillable)
    swap = swap.merge(common_dates,on=["pool","scope","signal_date"],how="left",validate="m:1")
    swap.to_parquet(OUT/"swap_outcomes.parquet",index=False)

    calendar = pd.read_csv(RES/"decisions/dates.csv", parse_dates=["signal_date"])
    calendar = calendar.merge(common_dates,on=["pool","scope","signal_date"],how="left",validate="m:1")
    result = []
    for slice_name in ["all_scored","common_accounts"]:
        cal, legs = calendar, swap
        if slice_name == "common_accounts":
            cal = cal[cal.segment.notna()]
            legs = legs[legs.segment.notna()]
        for (pool,scope,model), x in cal.groupby(["pool","scope","model"]):
            s = legs[legs.pool.eq(pool) & legs.scope.eq(scope) & legs.model.eq(model)]
            reviewed=panel[(panel.pool==pool)&panel.selected&panel.oversold.eq(True)&panel.signal_date.isin(x.signal_date)]
            nloss = int(s.outgoing_ret10.lt(0).sum())
            ngain = int(s.outgoing_ret10.gt(0).sum())
            assert len(reviewed)==x.review.sum() and len(s)==x.changed.sum()
            result.append(dict(pool=pool,scope=scope,model=model,window_set=slice_name,dates=len(x),
                total_seats=x.seats.sum(),reviewed=len(reviewed),changed=len(s),change_dates=x.changed.gt(0).sum(),
                review_known_ret=reviewed.ret10.count(),losses_to_find=reviewed.ret10.lt(0).sum(),
                gains_to_keep=reviewed.ret10.gt(0).sum(),avoided_losses=nloss,missed_gains=ngain,
                unchanged_price=s.outgoing_ret10.eq(0).sum(),unknown_return=s.outgoing_ret10.isna().sum(),
                missed_gains_after_breach=(s.outgoing_ret10.gt(0)&s.outgoing_breach.eq(True)).sum(),
                breach_and_loss_avoided=(s.outgoing_ret10.lt(0)&s.outgoing_breach.eq(True)).sum(),
                avoided_loss_abs_bp=-1e4*s.loc[s.outgoing_ret10.lt(0),"outgoing_ret10"].mean(),
                missed_gain_bp=1e4*s.loc[s.outgoing_ret10.gt(0),"outgoing_ret10"].mean(),
                both_fillable=int(s.both_fillable.sum()),outgoing_mean_bp=s.loc[s.both_fillable,"outgoing_ret10"].mean()*1e4,
                incoming_mean_bp=s.loc[s.both_fillable,"incoming_ret10"].mean()*1e4,
                equal_cash_bp=s.equal_cash_bp.mean()))
    pd.DataFrame(result).to_csv(OUT/"seats.csv",index=False)


def main():
    OUT.mkdir(exist_ok=True,parents=True)
    common_dates=account_contrasts()
    evaluate_seats(common_dates)


if __name__=="__main__":
    main()

