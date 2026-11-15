"""Delayed monthly fixed-member catch-up diagnostic; no executable return claim."""
import pandas as pd
from common import *
K=KEY+['date']

def summaries(p):
    rows=[]
    for cohort in ['main80','strict100']:
        q=p[p.leader_spread.notna() & (p.strict_complete if cohort=='strict100' else True)].copy()
        q['stratum']=np.where(q.leader_spread.gt(0),'positive','nonpositive')
        for key,g in q.groupby(['era','level','date','stratum']):
            v=g[g.future_status.eq('complete')]
            rows.append(dict(zip(['era','level','date','stratum'],key),cohort=cohort,signals=len(g),complete=len(v),leader=v.future_leader.mean(),follower=v.future_follower.mean(),catchup=v.catchup.mean(),follower_positive=v.future_follower.gt(0).mean() if len(v) else np.nan,catchup_positive=v.catchup.gt(0).mean() if len(v) else np.nan,catchup_with_follower_rise=(v.catchup.gt(0)&v.future_follower.gt(0)).mean() if len(v) else np.nan))
        for key,g in q.groupby(['era','level','date']):
            v=g[g.future_status.eq('complete')];ic=np.nan
            if len(v)>=20 and v.leader_spread.nunique()>1 and v.catchup.nunique()>1:ic=v.leader_spread.corr(v.catchup,method='spearman')
            rows.append(dict(zip(['era','level','date'],key),stratum='all_ic',cohort=cohort,signals=len(g),complete=len(v),ic=ic))
    d=pd.DataFrame(rows);d['year']=d.date.dt.year
    metrics=['leader','follower','catchup','follower_positive','catchup_positive','catchup_with_follower_rise','ic']
    annual=d.groupby(['era','level','cohort','stratum','year'])[metrics].mean().reset_index()
    overall=d.groupby(['era','level','cohort','stratum'])[metrics].mean().reset_index()
    return d,annual,overall

def run():
    out=ROOT/'outputs/r110';out.mkdir(exist_ok=True)
    paths=[ROOT/'outputs/r108/member_ledger.parquet',ROOT/'outputs/r108/industry_features.parquet',CACHE/'extension_v2/products/panel.parquet',CACHE/'forecast_v5/CSI_ALL.parquet']
    m=pd.read_parquet(paths[0],columns=K+['security_id','prior_cap_rank','signal_month']);p=pd.read_parquet(paths[1])
    s=pd.read_parquet(paths[2],columns=['month','date','security_id','qfq_close','close_chain','listed'])
    assert not s.duplicated(['month','security_id']).any()
    ix=pd.DatetimeIndex(pd.read_parquet(paths[3]).index);cal=pd.Series(ix,index=ix.to_period('M')).groupby(level=0).max();cal=cal[cal.index.end_time.normalize()<=ix.max()]
    for name,offset in [('entry',1),('exit',2)]:
        m[name+'_month']=m.signal_month+offset;m[name+'_expected']=m[name+'_month'].map(cal)
        z=s.rename(columns={c:name+'_'+c for c in s.columns if c!='security_id'})
        m=m.merge(z,on=[name+'_month','security_id'],how='left',validate='many_to_one')
    valid=m.entry_date.eq(m.entry_expected)&m.exit_date.eq(m.exit_expected)&m.entry_listed.eq(True)&m.exit_listed.eq(True)
    valid &=np.isfinite(m.entry_qfq_close)&m.entry_qfq_close.gt(0)&np.isfinite(m.exit_qfq_close)&m.exit_qfq_close.gt(0)
    valid &= m.entry_close_chain.notna()&~m.entry_close_chain.isin(['','__MISSING__'])&m.entry_close_chain.eq(m.exit_close_chain)
    m['future_return']=(m.exit_qfq_close/m.entry_qfq_close-1).where(valid);m['side']=np.where(m.prior_cap_rank.le(3),'leader','follower')
    rows=[]
    for key,g in m.groupby(K,sort=False):
        status='incomplete_members'
        if g.exit_expected.isna().any() or g.entry_expected.isna().any():status='not_mature_in_complete_calendar'
        elif g.prior_cap_rank.isna().any():status='ranking_unavailable'
        elif g.future_return.notna().all():status='complete'
        a=g.loc[g.side.eq('leader'),'future_return'].mean() if status=='complete' else np.nan
        b=g.loc[g.side.eq('follower'),'future_return'].mean() if status=='complete' else np.nan
        rows.append(dict(zip(K,key),future_status=status,entry_expected=g.entry_expected.iloc[0],maturity_date=g.exit_expected.iloc[0],future_members=len(g),future_known=int(g.future_return.notna().sum()),future_leader=a,future_follower=b,catchup=b-a))
    p=p.merge(pd.DataFrame(rows),on=K,how='left',validate='one_to_one');p['future_status']=p.future_status.fillna('no_original_members')
    m.to_parquet(out/'member_outcomes.parquet',index=False);p.to_parquet(out/'industry_outcomes.parquet',index=False)
    d,a,o=summaries(p)
    for name,frame in [('date_metrics',d),('annual_metrics',a),('summary',o)]:frame.to_csv(out/f'{name}.csv',index=False)
    coverage=p.groupby(['era','level','status','future_status']).size().rename('rows').reset_index();coverage.to_csv(out/'coverage.csv',index=False)
    js(out/'receipt.json',dict(reads={str(x):sha(x) for x in paths+[Path(__file__),ROOT/'protocols/r110.json']},outputs={x.name:sha(x) for x in out.iterdir() if x.suffix in ['.parquet','.csv']},rows=len(p),members=len(m),available_signals=int(p.leader_spread.notna().sum()),complete_signal_outcomes=int((p.leader_spread.notna()&p.future_status.eq('complete')).sum()),adopted=False))
    print(o[['era','level','cohort','stratum','catchup','follower','ic']].to_string(index=False))
if __name__=='__main__':run()
