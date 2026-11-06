"""As-of size leaders, disjoint peers, and backward-estimated market residuals."""
import json
import numpy as np
import pandas as pd
from context6 import ROOT,V5,EP,CACHE,OLD,OUT,KEY,GROUPS,sha,js,freeze


def window_returns(price,chain,volume,start,end):
    valid=(start>=0)&(end<len(price));a=np.clip(start,0,len(price)-1);z=np.clip(end,0,len(price)-1)
    valid &= np.isfinite(price[a])&np.isfinite(price[z])&(chain[a]==chain[z])&(chain[a]!='__MISSING__')
    valid &= (volume[a]>0)&(volume[z]>0)
    active=np.r_[0,np.cumsum(np.isfinite(price)&(volume>0))]
    fraction=(active[z+1]-active[a])/(z-a+1)
    valid &= fraction>=.8
    with np.errstate(divide='ignore',invalid='ignore'):
        result=price[z]/price[a]-1
    return np.where(valid,result,np.nan)


def avg(x,minimum_fraction=.8,all_required=False):
    n=np.isfinite(x).sum(axis=1)
    threshold=x.shape[1] if all_required else np.ceil(x.shape[1]*minimum_fraction)
    return np.divide(np.nansum(x,axis=1),n,out=np.full(len(x),np.nan),where=(n>=threshold)&(n>0))


def build():
    freeze()
    audit=json.loads((V5/'outputs/daily_input_audit.json').read_text())
    f=pd.read_parquet(OLD/'features.parquet');f=f[f.features_ready].copy()
    jpath=CACHE.parent/'extension_v2/products/assignments.parquet'
    joined=pd.read_parquet(jpath)
    v4=json.loads((V5.parent/'v4_adaptive_6_18_months/outputs/audits/inputs.json').read_text())
    from pathlib import Path
    release=Path(v4['price_release'])
    days=pd.DatetimeIndex(pd.read_parquet(release/'inputs/inputs/baseline/normalized/calendar.parquet').date).sort_values()
    ids=sorted(joined.security_id.unique());mapping={s:i for i,s in enumerate(ids)}
    n=len(days);t=np.arange(n)
    specs={'ret21':(t-21,t),'ret63':(t-63,t),'lag21':(t-42,t-21),'future21':(t,t+21)}
    matrices={k:np.full((n,len(ids)),np.nan) for k in specs};reads={str(jpath):sha(jpath)}
    assert reads[str(jpath)]==audit['reads'][str(jpath)]
    for i,sid in enumerate(ids):
        p=release/f'normalized/prices_qfq/{sid}.parquet';h=sha(p);assert h==audit['reads'][str(p)];reads[str(p)]=h
        b=pd.read_parquet(p,columns=['date','qfq_close','close_conflict','factor_chain_id','volume']).set_index('date').reindex(days)
        price=pd.to_numeric(b.qfq_close).where(b.close_conflict.eq(False)&pd.to_numeric(b.qfq_close).gt(0)).to_numpy(float)
        chain=b.factor_chain_id.fillna('__MISSING__').to_numpy();vol=pd.to_numeric(b.volume).to_numpy(float)
        for name,(start,end) in specs.items():matrices[name][:,i]=window_returns(price,chain,vol,start,end)
        if (i+1)%1000==0:print('V6 verified stock partitions',i+1,flush=True)
    groups={k:g for k,g in joined.groupby(KEY+['month'])}
    f['asof_month']=f.membership_asof.dt.to_period('M')
    records=[];outcomes=[]
    for key,g in f.groupby(KEY+['asof_month'],sort=False):
        members=groups.get(key)
        rankable=members is not None and members.cap.notna().all() and members.unresolved.eq(0).all() and len(members)>=6
        row=pd.DataFrame({'row_id':g.row_id.to_numpy(),'rank_complete':bool(rankable)})
        y=pd.DataFrame({'row_id':g.row_id.to_numpy()})
        if rankable:
            members=members.sort_values(['cap','security_id'],ascending=[False,True])
            leaders=np.array([mapping[s] for s in members.security_id.iloc[:3]])
            peers=np.array([mapping[s] for s in members.security_id.iloc[3:]])
            ix=days.get_indexer(g.date);assert (ix>=0).all()
            row['leader_codes']=';'.join(members.instrument.iloc[:3])
            row['rank_asof']=members.date.iloc[0]
            row['leader_log_cap']=np.log(members.cap.iloc[:3].mean())
            for name,mat in matrices.items():
                lead=avg(mat[np.ix_(ix,leaders)],all_required=True);peer=avg(mat[np.ix_(ix,peers)])
                if name=='future21':
                    y['leader_future21']=lead;y['peer_future21']=peer
                    y['outcome_available_at']=[days[k+21] if k+21<n else pd.NaT for k in ix]
                else:
                    row['leader_'+name]=lead;row['peer_'+name]=peer
                    if name in ['ret21','lag21']:
                        x=mat[np.ix_(ix,peers)];breadth=np.where(np.isfinite(x),(x>0).astype(float),np.nan)
                        row['peer_breadth_'+name]=avg(breadth)
            row['peer_count']=len(peers)
        records.append(row);outcomes.append(y)
    additions=pd.concat(records,ignore_index=True);outcomes=pd.concat(outcomes,ignore_index=True)
    result=f.drop(columns='asof_month').merge(additions,on='row_id',validate='one_to_one')
    outcomes.to_parquet(CACHE/'forward_peer_outcomes.parquet',index=False)
    # Daily market beta is shifted one day: today's move cannot change today's exposure estimate.
    daily=pd.read_parquet(OLD/'daily_industries.parquet')
    residuals=[]
    for bm in ['CSI300','CSI_ALL']:
        market=pd.read_parquet(OLD/f'{bm}.parquet').close
        mr=market.pct_change(fill_method=None)
        for key,g in daily.groupby(KEY+['block'],sort=False):
            g=g.sort_values('date').copy();r=g.nav.pct_change(fill_method=None);m=g.date.map(mr)
            beta=(r.rolling(126,min_periods=63).cov(m)/m.rolling(126,min_periods=63).var()).shift(1)
            residual=r-beta*m
            g['beta_residual21']=residual.rolling(21,min_periods=21).sum()
            downside=residual.where(m<0)
            g['down_resilience63']=downside.rolling(63,min_periods=10).mean()
            g['risk126']=r.rolling(126,min_periods=63).std()*np.sqrt(21)
            g['benchmark']=bm
            residuals.append(g[KEY+['date','benchmark','beta_residual21','down_resilience63','risk126']])
    residuals=pd.concat(residuals,ignore_index=True)
    panels=[]
    for bm in ['CSI300','CSI_ALL']:
        market=pd.read_parquet(OLD/f'{bm}.parquet').close
        ret21=market/market.shift(21)-1;ret63=market/market.shift(63)-1;lag21=market.shift(21)/market.shift(42)-1
        r=result.merge(residuals[residuals.benchmark.eq(bm)],on=KEY+['date'],validate='many_to_one')
        r['leader21']=r.leader_ret21-r.date.map(ret21);r['peer21']=r.peer_ret21-r.date.map(ret21)
        r['leader63']=r.leader_ret63-r.date.map(ret63);r['peer63']=r.peer_ret63-r.date.map(ret63)
        r['leader_pos21']=r.leader21.clip(lower=0);r['leader_neg21']=r.leader21.clip(upper=0)
        r['leader_gap21']=r.leader21-r.peer21
        r['leader_gap_lag21']=r.leader_lag21-r.peer_lag21
        r['peer_breadth21']=r.peer_breadth_ret21
        r['peer_breadth_change']=r.peer_breadth_ret21-r.peer_breadth_lag21
        r['diffusion_interaction']=r.leader_gap_lag21.clip(lower=0)*r.peer_breadth_change.clip(lower=0)
        r['reverse_pos21']=r.peer21.clip(lower=0);r['reverse_neg21']=r.peer21.clip(upper=0)
        # Fixed permutation by code within same day/level: never chosen by predictive outcome.
        r=r.sort_values(['date','level','frequency','industry_code'])
        for _,ix in r.groupby(['date','level','frequency']).groups.items():
            valid=r.loc[ix];valid=valid[valid.leader21.notna()]
            if len(valid)>1:r.loc[valid.index,'other_leader21']=np.roll(valid.leader21.to_numpy(),1)
        r['other_pos21']=r.other_leader21.clip(lower=0);r['other_neg21']=r.other_leader21.clip(upper=0)
        r['common_complete']=r[sum(GROUPS.values(),[])+['other_leader21','leader63','risk126']].notna().all(axis=1)
        r['h3_complete']=r[GROUPS['H3']].notna().all(axis=1)
        panels.append(r)
    features=pd.concat(panels,ignore_index=True)
    assert not any('future' in c or c=='y' for c in features.columns)
    features.to_parquet(CACHE/'mechanism_features.parquet',index=False)
    coverage=features.groupby(['benchmark','frequency','level']).agg(rows=('row_id','size'),rank_known=('rank_complete','sum'),
        common_complete=('common_complete','sum'),h3_complete=('h3_complete','sum')).reset_index()
    coverage.to_csv(OUT/'feature_coverage.csv',index=False)
    facts=EP.parent/'30_pit_data_foundation_v1/outputs/pit_v4/reviewed_fact_summary.json'
    js(OUT/'fundamental_audit.json',dict(status='BLOCKED_DATA',latest_reviewed_fact_summary=json.loads(facts.read_text()),
        source=str(facts),sha256=sha(facts),reason='selected report versions cannot support representative industry revenue/profit improvement breadth'))
    js(OUT/'feature_audit.json',dict(reads=reads,features_sha256=sha(CACHE/'mechanism_features.parquet'),
        forward_outcomes_sha256=sha(CACHE/'forward_peer_outcomes.parquet'),rows=len(features),
        feature_cutoff='at or before origin',ranking='prior month-end exact archived mark; known_at unavailable',
        return_quote_rule='positive trading volume at both endpoints and >=80% active observations within window',
        strict_PIT='BLOCKED_DATA'))
    print('V6 mechanism features',len(features),'complete',features.common_complete.sum(),flush=True)


if __name__=='__main__':build()
