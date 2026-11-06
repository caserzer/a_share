"""Positive-news lead-lag implications with reverse and cross-industry controls."""
import numpy as np
import pandas as pd
from context6 import CACHE,OLD,OUT,KEY,js,sha


def regression(g,kind):
    scale=np.maximum(g.risk126.to_numpy(float),.005)
    if kind=='forward':lead=g.leader21.to_numpy();own21=g.peer21.to_numpy();own63=g.peer63.to_numpy();y=g.peer_y.to_numpy()
    elif kind=='reverse':lead=g.peer21.to_numpy();own21=g.leader21.to_numpy();own63=g.leader63.to_numpy();y=g.leader_y.to_numpy()
    else:lead=g.other_leader21.to_numpy();own21=g.peer21.to_numpy();own63=g.peer63.to_numpy();y=g.peer_y.to_numpy()
    values=[lead.clip(min=0)/scale,lead.clip(max=0)/scale,own21/scale,own63/scale,g.market21.to_numpy()/scale,
        np.log(scale),g.log_members.to_numpy()]
    x=np.column_stack([np.ones(len(g))]+[np.clip(v,-5,5) for v in values]);y=np.clip(y/scale,-5,5)
    # The market term is collinear with some controls on exceptional zero-market days;
    # use the minimum-norm fixed design and disclose rank, rather than select covariates.
    beta=np.linalg.lstsq(x,y,rcond=None)[0]
    return dict(positive_slope=float(beta[1]),negative_slope=float(beta[2]),n=len(g),design_rank=int(np.linalg.matrix_rank(x)))


def run():
    f=pd.read_parquet(CACHE/'mechanism_features.parquet');f=f[f.common_complete&f.date.ge('2024-01-01')].copy()
    y=pd.read_parquet(CACHE/'forward_peer_outcomes.parquet')
    f=f.merge(y,on='row_id',validate='many_to_one')
    frames=[]
    for bm,g in f.groupby('benchmark'):
        market=pd.read_parquet(OLD/f'{bm}.parquet').close
        future=market.shift(-21)/market-1;past=market/market.shift(21)-1
        g=g.copy();g['peer_y']=g.peer_future21-g.date.map(future);g['leader_y']=g.leader_future21-g.date.map(future)
        g['market21']=g.date.map(past)
        g=g[g[['peer_y','leader_y','risk126','market21']].notna().all(axis=1)]
        frames.append(g)
    f=pd.concat(frames,ignore_index=True);rows=[]
    for key,g in f.groupby(['frequency','benchmark','level','date']):
        if len(g)<10:continue
        for kind in ['forward','reverse','other_industry']:
            r=regression(g,kind);r.update(zip(['frequency','benchmark','level','date'],key));r['kind']=kind;rows.append(r)
    d=pd.DataFrame(rows);d.to_csv(OUT/'lead_lag_daily_regressions.csv',index=False)
    p=d.pivot(index=['frequency','benchmark','level','date'],columns='kind',values='positive_slope').reset_index()
    p['H1_positive_lead']=p['forward'];p['H1_forward_minus_reverse']=p['forward']-p['reverse']
    p['H1_forward_minus_other']=p['forward']-p.other_industry;p['month']=p.date.dt.to_period('M').astype(str)
    cols=['H1_positive_lead','H1_forward_minus_reverse','H1_forward_minus_other']
    p.groupby(['frequency','benchmark','level','month'])[cols].mean().groupby('month').mean().reset_index().to_csv(OUT/'monthly_mechanism_effects.csv',index=False)
    d.groupby(['frequency','benchmark','level','kind'])[['positive_slope','negative_slope','n']].mean().reset_index().to_csv(OUT/'lead_lag_summary.csv',index=False)
    js(OUT/'mechanism_audit.json',dict(observations=len(f),cross_section_regressions=len(d),
        common_forward_reverse_placebo_sample=True,source_features_sha256=sha(CACHE/'mechanism_features.parquet'),
        outcome_available_max=str(f.outcome_available_at.max()),causal_identification=False))
    print('V6 mechanism regressions',len(d),flush=True)


if __name__=='__main__':run()
