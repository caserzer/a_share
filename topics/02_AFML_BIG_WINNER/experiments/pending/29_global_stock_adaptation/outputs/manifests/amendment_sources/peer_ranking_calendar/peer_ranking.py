"""Descriptive discrimination on preformed actual peer pairs; no new peer rule."""
from common import *


def pair_concordance(target_p,peer_p,target_y,peer_y):
    p=np.asarray(target_p);q=np.asarray(peer_p);y=np.asarray(target_y);v=np.asarray(peer_y)
    mask=np.isfinite(y)&np.isfinite(v)&(y!=v)
    difference=(p[mask]-q[mask])*(y[mask]-v[mask])
    return np.where(difference>0,1.,np.where(difference<0,0.,.5)),mask


def main():
    cohort=json.loads((EP/'configs/target_cohort.yaml').read_text());stocks=[r['instrument'] for r in cohort['companies']]
    rows=[];intervals=[]
    for foundation in ['M_R','L2']:
        raw=pd.read_parquet(CACHE/f'real_{foundation}_all.parquet')
        raw=raw[(raw.date>=C['prediction_start'])&raw.actual.notna()]
        peers=pd.read_parquet(CACHE/f'real_{foundation}_peers.parquet')
        cols=['date','instrument','actual']+C['formal_models']
        pairs=peers.merge(raw[cols],on=['date','instrument'],validate='many_to_one')
        other=raw[cols].rename(columns={c:'peer_'+c for c in cols if c!='date'}).rename(columns={'peer_instrument':'peer'})
        pairs=pairs.merge(other,on=['date','peer'],validate='many_to_one')
        for population,z in [('D0',pairs),('cohort40_targets',pairs[pairs.instrument.isin(stocks)])]:
            for date,g in z.groupby('date'):
                for name in C['formal_models']:
                    values,mask=pair_concordance(g[name],g['peer_'+name],labels(g.actual),labels(g.peer_actual))
                    rows.append(dict(foundation=foundation,population=population,date=date,model=name,
                        directed_pairs=len(g),discordant_outcome_pairs=int(mask.sum()),
                        concordance=float(values.mean()) if len(values) else np.nan,
                        target_companies=g.instrument.nunique(),peer_companies=g.peer.nunique()))
    frame=pd.DataFrame(rows);frame.to_csv(OUT/'peer_pair_ranking.csv',index=False)
    for (foundation,population),g in frame.groupby(['foundation','population']):
        pivot=g.pivot(index='date',columns='model',values='concordance')
        for a,b in [('GPI','G'),('GP','G'),('GI','G'),('GPI','GP')]:
            delta=pivot[a]-pivot[b]
            if delta.notna().any():
                for block in [6,12]:intervals.append(dict(foundation=foundation,population=population,candidate=a,baseline=b,**ci(delta,block)))
    pd.DataFrame(intervals).to_csv(OUT/'peer_pair_intervals.csv',index=False)


if __name__=='__main__':main()
