"""Paired account comparisons. Random-arm averages are taken within the same window."""
from pathlib import Path
import numpy as np
import pandas as pd

RES=Path(__file__).resolve().parents[1]/"results"
OUT=RES/"training_review"
SEEDS=[39,139,239,339,439]


def interval(part):
    rng=np.random.default_rng(3901)
    sums=np.zeros(10000)
    for _,seg in part.groupby("segment"):
        x=seg.sort_values("signal_date").net_bp.to_numpy()
        n=len(x)
        block=min(3,n)
        start=rng.integers(0,n,size=(len(sums),(n+block-1)//block,1))
        ix=(start+np.arange(block))%n
        sums+=x[ix.reshape(len(sums),-1)[:,:n]].sum(axis=1)
    return np.quantile(sums/len(part),[.025,.975])


def main():
    w=pd.read_parquet(RES/"training_accounts/windows.parquet")
    w=w[w.series.eq("common")]
    rows=[]
    keys=["segment","signal_date"]
    for (pool,scope,cost),g in w.groupby(["pool","scope","cost"]):
        assert not g.duplicated(keys+["model"]).any()
        for task in ["breakout","oversold"]:
            curated=task+"_curated"
            seeds=[f"{task}_random_{seed}" for seed in SEEDS]
            groups={"full":["full"],"random_mean":seeds,**{s:[s] for s in seeds}}
            for reference,models in groups.items():
                diffs={}
                for field in ["net","fee","turnover"]:
                    table=g.pivot(index=keys,columns="model",values=field)
                    ref=table[models].mean(axis=1,skipna=False)
                    assert ref.notna().all() and table[curated].notna().all()
                    diffs[field]=table[curated]-ref
                part=pd.DataFrame(diffs).reset_index()
                part["net_bp"]=1e4*part.net
                part["gross_bp"]=1e4*(part.net+part.fee)
                part["fee_bp"]=1e4*part.fee
                rows.append(part.assign(task=task,reference=reference,pool=pool,scope=scope,cost=cost))
    changes=pd.concat(rows,ignore_index=True)
    changes.to_parquet(OUT/"paired_windows.parquet",index=False)
    sums=[]
    for key,g in changes.groupby(["pool","scope","cost","task","reference"]):
        for segment,part in [("all",g)]+[(str(j),h) for j,h in g.groupby("segment")]:
            lo,hi=interval(part)
            sums.append(dict(zip(["pool","scope","cost","task","reference"],key))|dict(segment=segment,
                n=len(part),segments=part.segment.nunique(),net_bp=part.net_bp.mean(),low=lo,high=hi,
                gross_bp=part.gross_bp.mean(),fee_bp=part.fee_bp.mean(),turnover=part.turnover.mean(),
                wins=int(part.net.gt(0).sum()),first_signal=part.signal_date.min(),last_signal=part.signal_date.max()))
    summary=pd.DataFrame(sums);summary.to_csv(OUT/"paired_summary.csv",index=False)
    # Monthly realized net returns are computed within each independent book only.
    d=pd.read_parquet(RES/"training_accounts/daily.parquet")
    d=d[d.series.eq("common") & d.cost.eq("base")].copy()
    d["month"]=pd.to_datetime(d.date).dt.to_period("M").astype(str)
    book=["pool","scope","segment","model"]
    end=d.sort_values("date").groupby(book+["month"]).nav.last().reset_index()
    end["month_net"]=end.nav/end.groupby(book).nav.shift().fillna(1.)-1
    table=end.pivot(index=["pool","scope","segment","month"],columns="model",values="month_net")
    months=[]
    for task in ["breakout","oversold"]:
        random=[f"{task}_random_{s}" for s in SEEDS]
        part=table[[task+"_curated","full"]].copy()
        part["vs_full_bp"]=1e4*(part[task+"_curated"]-part.full)
        part["vs_random_bp"]=1e4*(part[task+"_curated"]-table[random].mean(axis=1,skipna=False))
        months.append(part[["vs_full_bp","vs_random_bp"]].reset_index().assign(task=task))
    pd.concat(months,ignore_index=True).to_csv(OUT/"paired_months.csv",index=False)


if __name__=="__main__":main()
