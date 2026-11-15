"""Independent endpoint lookup, fixed-group and date/annual aggregation checks."""
import pandas as pd
from scipy.stats import rankdata
from common import *
K=KEY+['date']
def close(a,b):np.testing.assert_allclose(a,b,rtol=1e-11,atol=1e-12,equal_nan=True)
def run():
    out=ROOT/'outputs/r110';rec=json.loads((out/'receipt.json').read_text())
    for p,h in rec['reads'].items():assert sha(p)==h,p
    for n,h in rec['outputs'].items():assert sha(out/n)==h,n
    m=pd.read_parquet(out/'member_outcomes.parquet');base=pd.read_parquet(ROOT/'outputs/r108/member_ledger.parquet')
    keys=K+['security_id'];assert not m.duplicated(keys).any()
    b=base.set_index(keys).reindex(pd.MultiIndex.from_frame(m[keys]));assert len(b)==len(m)
    close(m.prior_cap_rank,b.prior_cap_rank);assert (m.signal_month.to_numpy()==b.signal_month.to_numpy()).all()
    s=pd.read_parquet(CACHE/'extension_v2/products/panel.parquet').set_index(['month','security_id'])
    ix=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index)
    calendar={v:max(t for t in ix if t.to_period('M')==v) for v in ix.to_period('M').unique() if v.end_time.normalize()<=ix.max()}
    valid=np.ones(len(m),dtype=bool)
    for name,offset in [('entry',1),('exit',2)]:
        months=m.signal_month+offset;assert months.equals(m[name+'_month'])
        expected=months.map(calendar);pd.testing.assert_series_equal(expected,m[name+'_expected'],check_names=False)
        z=s.reindex(pd.MultiIndex.from_arrays([months,m.security_id]))
        for col in ['date','qfq_close','close_chain','listed']:
            left=m[name+'_'+col].reset_index(drop=True);right=z[col].reset_index(drop=True)
            assert left.isna().equals(right.isna())
            pd.testing.assert_series_equal(left[left.notna()],right[right.notna()],check_names=False)
        v=m[name+'_qfq_close'];valid &= (m[name+'_date'].eq(expected)&m[name+'_listed'].eq(True)&v.gt(0)&np.isfinite(v)).to_numpy()
    chain=m.entry_close_chain;valid &= (chain.notna()&~chain.isin(['','__MISSING__'])&chain.eq(m.exit_close_chain)).to_numpy()
    expected=(m.exit_qfq_close/m.entry_qfq_close-1).to_numpy();expected[~valid]=np.nan;close(expected,m.future_return)
    p=pd.read_parquet(out/'industry_outcomes.parquet');orig=pd.read_parquet(ROOT/'outputs/r108/industry_features.parquet')
    pd.testing.assert_frame_equal(p[orig.columns],orig)
    groups=m.groupby(K);lookup=p.set_index(K)
    for key,g in groups:
        row=lookup.loc[key];status='incomplete_members'
        if g.entry_expected.isna().any() or g.exit_expected.isna().any():status='not_mature_in_complete_calendar'
        elif g.prior_cap_rank.isna().any():status='ranking_unavailable'
        elif g.future_return.notna().all():status='complete'
        assert row.future_status==status
        for a,b in [('entry_expected','entry_expected'),('maturity_date','exit_expected')]:
            assert (pd.isna(row[a]) and pd.isna(g[b].iloc[0])) or row[a]==g[b].iloc[0]
        assert row.future_members==len(g) and row.future_known==g.future_return.notna().sum()
        if status=='complete':
            lead=g.loc[g.prior_cap_rank<=3,'future_return'];follow=g.loc[g.prior_cap_rank>3,'future_return'];assert len(lead)==3 and len(follow)>=2
            close([row.future_leader,row.future_follower,row.catchup],[sum(lead)/len(lead),sum(follow)/len(follow),sum(follow)/len(follow)-sum(lead)/len(lead)])
        else:assert pd.isna(row.catchup) and pd.isna(row.future_follower) and pd.isna(row.future_leader)
    assert p.loc[~pd.MultiIndex.from_frame(p[K]).isin(groups.groups),'future_status'].eq('no_original_members').all()
    d=pd.read_csv(out/'date_metrics.csv',parse_dates=['date'])
    count=0
    for cohort in ['main80','strict100']:
        q=p[p.leader_spread.notna() & (p.strict_complete if cohort=='strict100' else True)]
        for key,g in q.groupby(['era','level','date']):
            for stratum in ['positive','nonpositive','all_ic']:
                h=g if stratum=='all_ic' else g[g.leader_spread.gt(0) if stratum=='positive' else g.leader_spread.le(0)]
                if not len(h):continue
                row=d[(d.era==key[0])&(d.level==key[1])&(d.date==key[2])&(d.cohort==cohort)&(d.stratum==stratum)];assert len(row)==1;row=row.iloc[0];count+=1
                v=h[h.future_status=='complete'];assert row.signals==len(h) and row.complete==len(v)
                if stratum=='all_ic':
                    ic=np.nan
                    if len(v)>=20 and v.leader_spread.nunique()>1 and v.catchup.nunique()>1:ic=np.corrcoef(rankdata(v.leader_spread),rankdata(v.catchup))[0,1]
                    close(row.ic,ic)
                else:
                    vals=[v.future_leader.mean(),v.future_follower.mean(),v.catchup.mean()]
                    rates=[np.mean(v.future_follower.to_numpy()>0),np.mean(v.catchup.to_numpy()>0),np.mean((v.catchup.to_numpy()>0)&(v.future_follower.to_numpy()>0))] if len(v) else [np.nan]*3
                    close(row[['leader','follower','catchup','follower_positive','catchup_positive','catchup_with_follower_rise']].to_numpy(dtype=float),vals+rates)
    assert count==len(d)
    metrics=['leader','follower','catchup','follower_positive','catchup_positive','catchup_with_follower_rise','ic']
    for name,ks in [('summary',['era','level','cohort','stratum']),('annual_metrics',['era','level','cohort','stratum','year'])]:
        z=pd.read_csv(out/f'{name}.csv');assert len(z)==d.groupby(ks).ngroups
        for key,g in d.groupby(ks):
            mask=np.ones(len(z),dtype=bool)
            for k,value in zip(ks,key):mask &= z[k].eq(value)
            assert mask.sum()==1;close(z.loc[mask,metrics].to_numpy(dtype=float)[0],[g[c].dropna().to_numpy().mean() if g[c].notna().any() else np.nan for c in metrics])
    coverage=pd.read_csv(out/'coverage.csv').set_index(['era','level','status','future_status'])['rows']
    expected=p.groupby(['era','level','status','future_status']).size()
    pd.testing.assert_series_equal(coverage.sort_index(),expected.sort_index(),check_names=False)
    js(out/'verification.json',dict(status='PASS',members=len(m),industry_rows=len(p),date_rows=len(d),complete_signal_outcomes=rec['complete_signal_outcomes'],adopted=False))
    print('PASS',len(m),'member endpoints and',len(d),'date summaries')
if __name__=='__main__':run()
