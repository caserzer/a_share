from pathlib import Path
import pandas as pd, numpy as np
HERE=Path(__file__).resolve().parent; OLD=next(HERE.parents[2].glob('41_*'))
def run():
    c=pd.read_parquet(HERE/'corners.parquet')
    old=pd.read_parquet(OLD/'p2/results/funded_daily.parquet').query('mul==1')
    validate=[]
    for (sc,arm),g in c[c.state==c.rule].groupby(['scope','state']):
        d=old[(old.scope==sc)&(old.arm==arm)].set_index('idx');end=d.index.max();e=g.entry_idx.to_numpy()
        lhs=d.pre.reindex(e).to_numpy();r=d.pre.reindex(e+10).to_numpy();r[e+10==end]=d.at[end,'nav']
        dif=max(abs(g.whole0.to_numpy()-lhs).max(),abs(g.whole1.to_numpy()-r).max())
        assert dif<1.e-10;validate.append((sc,arm,len(g),dif))
    pd.DataFrame(validate,columns=['scope','arm','dates','max_corner_error']).to_csv(HERE/'parity.csv',index=False)
    cs=c[c.state=='hold'].copy()
    for col in ['gross','fee']:cs[col]/=cs.sleeve0
    detail=cs.pivot(index=['scope','entry_idx','phase'],columns='rule',values=['gross','fee','net','sleeve0'])
    phase=[]
    for (sc,off),group in detail.groupby(level=['scope','phase']):
        for typ in ['ordinary','capital']:
            w=np.ones(len(group)) if typ=='ordinary' else group.sleeve0.tree.to_numpy()
            phase.append((sc,off,typ,len(w),*[np.average(group[col].tree-group[col]['rank'],weights=w)*1e4 for col in ['gross','fee','net']]))
    for sc,group in detail.groupby(level='scope'):
        for typ in ['ordinary','capital']:
            w=np.ones(len(group)) if typ=='ordinary' else group.sleeve0.tree.to_numpy()
            phase.append((sc,'all',typ,len(w),*[np.average(group[col].tree-group[col]['rank'],weights=w)*1e4 for col in ['gross','fee','net']]))
    pd.DataFrame(phase,columns='scope phase denominator dates gross_bp fee_bp net_bp'.split()).to_csv(HERE/'phase_comparison.csv',index=False)
    c['whole']=c.whole1/c.whole0-1
    d=c[c.state!='hold'].pivot(index=['scope','entry_idx','phase'],columns=['state','rule'],values='whole')*1e4
    tt=d['tree','tree'];rr=d['rank','rank'];tr=d['tree','rank'];rt=d['rank','tree']
    v=pd.DataFrame(dict(decision=.5*(tt-tr+rt-rr),prior_state=.5*(tt-rt+tr-rr),total=tt-rr,interaction=tt-tr-rt+rr))
    assert (v.decision+v.prior_state-v.total).abs().max()<1e-9
    v.to_parquet(HERE/'corner_attribution.parquet');v.groupby(level=['scope','phase']).mean().to_csv(HERE/'corner_phase.csv')
    age=pd.read_parquet(HERE/'age_daily.parquet')
    role=pd.read_parquet(HERE/'age_roles.parquet')
    age['month']=age.date.dt.strftime('%Y-%m')
    age['net']=age.gross-age.fee
    orig=old[old.arm.isin(['tree','rank'])].copy().sort_values(['scope','arm','date'])
    orig['month']=orig.date.dt.strftime('%Y-%m')
    nav=orig.groupby(['scope','arm','month']).nav.last()
    start=nav.groupby(level=['scope','arm']).shift()
    starts=start.rename('opening').reset_index();starts=starts.merge(orig.groupby(['scope','arm']).month.max().rename('last'),on=['scope','arm'])
    starts=starts[starts.month.ne(starts['last'])&starts.opening.notna()]
    x=age.groupby(['scope','arm','month','age'])[['gross','fee','net']].sum().reset_index().merge(starts,on=['arm','scope','month'])
    for field in ['gross','net','fee']:x[field]*=1e4/x.opening
    avg=x.groupby(['scope','age','arm'])[['gross','fee','net']].mean().unstack('arm')
    gap=avg.xs('tree',level=1,axis=1)-avg.xs('rank',level=1,axis=1)
    gap.to_csv(HERE/'age_month_gap.csv')
    orig_n=(nav/start-1).rename('net').reset_index().merge(starts,on=['scope','arm','month'])
    ck=x.groupby(['scope','arm','month']).net.sum().rename('replayed').reset_index().merge(orig_n)
    assert (ck.replayed-ck.net*10000).abs().max()<1.e-8
    role=role.merge(starts,on=['scope','arm','month'])
    role['net']=(role.gross-role.fee)/role.opening*1e4
    months=starts.groupby(['scope','arm']).size().rename('months')
    for dims,out in [(['next_status','role'],'status'),(['future_member','role'],'future20')]:
        acc=role.groupby(['scope','arm']+dims).net.sum().to_frame().join(months).assign(per_month=lambda z:z.net/z.months)
        diff=acc.per_month.unstack('arm').fillna(0);diff['gap']=diff.tree-diff['rank'];diff.to_csv(HERE/(out+'_capital_gap.csv'))
    print(gap.to_string());print(v.groupby(level='scope').mean().to_string())
if __name__=='__main__':run()
