from fund_fit import *
import json,re
from rank_population import transform
S=F/'strict'
def run():
    panel=pd.read_parquet(S/'panel.parquet')
    idx=F/'originals';all_indices=[json.loads(p.read_text()) for p in idx.glob('[0-9]*.json')]
    status=[];intervals=[]
    for s in all_indices:
        code=s['issuer'];complete=s['status']=='complete_index'
        filename=F/'amendments'/(code+'.json')
        info=json.loads(filename.read_text()) if filename.exists() else {}
        secondary=info.get('status','unavailable')
        status.append((code,s['status'],len(s['items']),secondary,info.get('seen',0)))
        which=panel.instrument.str[2:].eq(code) if complete else None
        if complete and secondary!='complete':panel.loc[which,A+N]=np.nan
        if secondary=='complete':
            for dt,title,aid in info['amendments']:
                if re.search('制度|章程|议事|中介|购买资产|关联交易|责任追究|募集说明书',title):continue
                # Conservatively suppress potentially affected TTM and stability lookbacks.
                # Count 12 subsequent fiscal quarters before treating an unresolved correction as expired.
                start=pd.Timestamp(dt);end=start+pd.DateOffset(years=3)
                if end<panel.signal_date.min():continue
                review=which&(panel.signal_date>start)&(panel.signal_date<=end)
                panel.loc[review,A+N]=np.nan
                intervals.append((code,start,end,title,aid))
    pd.DataFrame(status,columns='code index_status reports secondary_status secondary_notices'.split()).to_csv(S/'issuer_status.csv',index=False)
    pd.DataFrame(intervals,columns='code start end title id'.split()).to_csv(S/'revision_exclusions.csv',index=False)
    grp=panel.groupby('signal_date');G=panel.groupby(['signal_date','industry'])
    for a in A:
        panel['raw_'+a]=grp[a].rank()/(grp[a].transform('count')+1)-.5
        n=G[a].transform('count');panel['n_'+a]=(G[a].rank()/(n+1)-.5).where((n>=10)&~panel.industry.isin(['未知','冲突']))
    panel.to_parquet(S/'qualified_panel.parquet',index=False)
    refs=frozen(True);outer=refs[refs.signal_date>=pd.Timestamp('2021-01-08')].copy();v=outer[KEY].merge(panel,on=KEY[:2],validate='1:1')
    v=transform(v)
    for a in A+N:v['valid_'+a]=v[a].notna().astype(int)
    v['joint_raw']=v[A].notna().all(axis=1).astype(int);v['joint_neutral']=v[N].notna().all(axis=1).astype(int);v['denom']=1
    cols=['valid_'+a for a in A+N]+['joint_raw','joint_neutral','denom']
    v.groupby('signal_date')[cols].sum().to_csv(S/'F2_coverage.csv')
    v.groupby([v.signal_date.dt.year,'industry'])[cols].sum().to_csv(S/'F2_year_industry.csv')
    # Zero columns reduce algebraically to R78 under the frozen missing-to-zero preprocessor.
    m=book(True);rpack=pack(m,outer,outer.refit_R)
    assert not panel[N].notna().any().any(),'strict industry support exists; train the supported neutral arms'
    account(m,rpack,800,'Fstrict','neutral',trace=True)
    equivalence=[('neutral','R78'),('missing','all six missing flags are constant'),('residual','no neutral observations'),('quality_gate','no eligible quality score'),('common_support','no common stock days')]+[(n,'no within-industry support') for n in N]
    pd.DataFrame(equivalence,columns=['arm','reason']).to_csv(S/'strict_equivalence.csv',index=False)
    # Run raw-anchor diagnostics on every supported date even when the neutral requirement fails.
    wk=pd.read_parquet(LOCAL/'wide_features.parquet',columns=KEY[:2]+['weekly_ok']);wk=wk[wk.weekly_ok]
    wp=transform(wk[KEY[:2]].merge(panel,on=KEY[:2],validate='1:1'))
    f=weekly(True).merge(wp[KEY[:2]+V],on=KEY[:2],how='left',validate='1:1');f[V]=f[V].fillna(0)
    all_scores=[];days=m.days
    for q,g in outer.groupby(outer.signal_date.dt.to_period('Q')):
        x=read_features(q,True).merge(g[KEY+['refit_R']],on=KEY,validate='1:1').merge(v[KEY[:2]+V],on=KEY[:2],how='left',validate='1:1')
        x[V]=x[V].fillna(0);train=f[f.exit_idx<days.searchsorted(q.start_time)];out=x[KEY+['refit_R']].copy()
        for a,cs in [('raw',V)]+list(zip(A,[[v] for v in V])):
            cv=COL+cs
            out[a]=ci.predict(x[cv],ci.ridge(train,cv,'target_rank')) if (train[cs]!=0).any().any() else out.refit_R
        all_scores.append(out)
    combined=pd.concat(all_scores);combined.to_parquet(S/'raw_scores.parquet',index=False)
    for a in ['raw']+A:account(m,pack(m,combined,combined[a]),800,'Fstrict_raw',a)
if __name__=='__main__':run()
