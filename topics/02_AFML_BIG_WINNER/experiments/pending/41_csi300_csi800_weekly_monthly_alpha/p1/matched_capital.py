"""Report a second denominator: invest each sleeve fully in its supported matched seats."""
from engine import *
sys.path.insert(0,str(HERE))
from summarize import grouped,stats

def main():
    m=load()
    pairs=pd.read_parquet(RESULT/'pairs.parquet')
    picks={}
    for (e,tol),g in pairs.groupby(['entry_idx','caliper']):
        for arm in ['head','runner']:
            picks.setdefault((tol,arm),{})[e]=m.symbols.get_indexer(g[arm])
    rows=[]
    for (tol,arm),p in picks.items():
        packed=pack(m,p)
        for s,r in enumerate(RANGES,1):
            rows.append(simulate(m,packed,r).assign(segment=s,caliper=tol,arm=arm))
    daily=pd.concat(rows).reset_index()
    daily.to_parquet(RESULT/'matched_invested_daily.parquet',index=False)
    mon=grouped(daily,['segment','caliper','arm'],m.days)
    outs=[]
    for tol,g in mon.groupby('caliper'):
        z=g.set_index(['arm','segment','month'])[['net','gross','fee']]
        result=stats((z.loc['head']-z.loc['runner']).reset_index())
        outs.append(result.assign(caliper=tol))
    pd.concat(outs).to_csv(RESULT/'matched_invested_summary.csv',index=False)
if __name__=='__main__':main()
