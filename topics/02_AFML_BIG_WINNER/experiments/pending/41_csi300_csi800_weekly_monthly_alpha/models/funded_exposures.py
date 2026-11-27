"""Mark actual post-rebalance holdings at the execution open, using prior-close covariates."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'p2'))
from inputs import market,SEGMENTS
from book import State,step

def main():
    m,actions=market();results=HERE/'results'
    frame=pd.read_parquet('/tmp/ep41_model_inputs_v1/panel.parquet')
    stocks=[c for c in pd.read_csv(next(HERE.parents[1].glob('37_*/extensions/original78*/outputs/original_78_features.csv'))).feature if not c.startswith('market_')]
    frame=frame[frame.outer].copy()
    valid=frame[stocks].notna()
    counts=frame.groupby(['signal_date','l1_name'])[stocks].transform('count')
    fall=(counts.lt(5)|np.repeat(frame.l1_name.eq('未知').to_numpy()[:,None],len(stocks),axis=1))&valid
    frame['fallback_fraction']=fall.sum(axis=1)/valid.sum(axis=1)
    frame['any_fallback']=fall.any(axis=1)
    frame['low_vol']=frame.groupby('signal_date').vol20.rank(pct=True)<=.2
    fields=['vol20','low_vol','any_fallback','fallback_fraction']
    cards={e:g.set_index('instrument')[fields+['l1_name']] for e,g in frame.groupby('entry_idx')}
    raw=pd.read_parquet(results/'target_lists.parquet')
    accounts=pd.read_parquet(results/'funded_daily.parquet').query('hold==10').set_index(['arm','segment','date'])
    rows=[];sectors=[]
    for arm in ['R','M1_raw','M1_global','M1_industry','top_M1_industry','I_free_industry','I_fixed_industry']:
        targets={m.days.get_loc(r.date)+1:m.symbols.get_indexer(r.instruments) for r in raw[raw.arm.eq(arm)].itertuples()}
        for scope,start,end in SEGMENTS:
            a,b=m.days.get_indexer([start,end]);state=State.empty(m.n)
            for e in range(a,b+1):
                plan=targets.get(e) if e+10<=b else None
                row,_=step(m,actions,state,a,b,e,plan,1)
                assert abs(row['nav']-accounts.loc[(arm,scope,m.days[e]),'nav'])<1e-10
                if plan is None:continue
                dollars=state.units.sum(axis=0)*np.nan_to_num(m.marks['flat'][0][e])
                value=pd.Series(dollars[dollars>0],index=m.symbols[dollars>0]);nav=value.sum()+state.cash.sum()
                cov=cards[e].reindex(value.index)
                record=dict(arm=arm,scope=scope,date=m.days[e],cash_fraction=state.cash.sum()/nav,known_factor_weight=value[cov.vol20.notna()].sum()/nav)
                for c in fields:record[c]=float(cov[c].astype(float).mul(value).sum()/nav)
                rows.append(record)
                weights=value.groupby(cov.l1_name.fillna('未知或当日不合格')).sum()/nav
                for sector,w in weights.items():sectors.append((arm,scope,m.days[e],sector,w))
    pd.DataFrame(rows).to_csv(results/'funded_style.csv',index=False)
    pd.DataFrame(sectors,columns=['arm','scope','date','industry','nav_fraction']).to_parquet(results/'funded_sectors.parquet',index=False)
if __name__=='__main__':main()
