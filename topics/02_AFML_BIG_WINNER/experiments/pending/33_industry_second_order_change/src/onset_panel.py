"""R07 process timing, state development and retrospective references. No payoff fitting."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from onset_replay import EP,SOURCE,KEY,load,describe_features,sha

OUT=EP/'outputs/r07'
METHODS=['slowdown','pressure_easing','improvement_acceleration','broad_confirmation','long_confirmation','old_top10','positive_but_slowing']


def make_panel():
    d,m,weeks=load();wid={t:i for i,t in enumerate(weeks)};chunks=[]
    for _,g in d.groupby(KEY,sort=True):
        f=describe_features(g,m)
        f['low_count_change']=f.new_low_count10-f.new_low_count10.shift(5)
        f=f[f.date.isin(weeks)].copy();f['week_i']=f.date.map(wid)
        chunks.append(f)
    p=pd.concat(chunks,ignore_index=True)
    p['eligible']=p.rate60.notna()&p.coverage.ge(.8)&p.members.ge(5)
    p['slowdown']=p.eligible&p.rate20.lt(0)&p.rate_change.gt(0)
    p['pressure_easing']=p.slowdown&p.low_count_change.lt(0)
    p['improvement_acceleration']=p.eligible&p.rate20.ge(0)&p.rate_change.gt(0)
    p['broad_confirmation']=p.eligible&p.rate20.gt(0)&p.breadth21.ge(.5)
    p['long_confirmation']=p.broad_confirmation&p.rate60.gt(0)
    p['positive_but_slowing']=p.eligible&p.rate20.gt(0)&p.rate_change.lt(0)
    old=pd.read_csv(EP/'outputs/r03/selected.csv.gz',usecols=['era','industry_code','date','pool','strategy'],parse_dates=['date'])
    old=old[old.pool.eq('accelerating_improvement')&old.strategy.eq('joint_velocity')][['era','industry_code','date']].drop_duplicates()
    old['old_top10']=True
    p=p.merge(old,on=['era','industry_code','date'],how='left',validate='one_to_one');p['old_top10']=p.old_top10.fillna(False).astype(bool)
    frac=p[p.eligible].groupby('date').breadth_change5.apply(lambda s:s.dropna().gt(0).mean())
    p['market_breadth_up_fraction']=p.date.map(frac)
    cases=pd.read_csv(EP/'outputs/r06/cases.csv')
    p['sample_case']=False
    for _,c in cases.iterrows():
        p.loc[p.era.eq(c.era)&p.industry_code.eq(c.industry_code)&p.date.between(c.entry,c.end),'sample_case']=True
    return p,m,weeks


def valid_window(g,i,a,b):
    l,r=i+a,i+b
    return l>=0 and r<len(g) and np.array_equal(g.week_i.iloc[l:r+1].to_numpy(),np.arange(g.week_i.iloc[i]+a,g.week_i.iloc[i]+b+1))


def slope(a):
    a=np.asarray(a);t=np.arange(len(a),dtype=float);t-=t.mean()
    return float(t@(a-a.mean())/(t@t))


def process(g):
    g=g.sort_values('date').reset_index(drop=True)
    episodes=[];refs=[];suppressed=[]
    for method in METHODS:
        prev=False;last=-1000
        for i,r in g.iterrows():
            flag=bool(r[method]);rising=flag and not prev;prev=flag
            if not (pd.Timestamp('2021-01-01')<=r.date<=pd.Timestamp('2025-12-31')):continue
            if not rising:continue
            if r.week_i-last<8:
                suppressed.append(dict(method=method,date=r.date));continue
            last=r.week_i
            base={k:r[k] for k in ['era','industry_code','industry_name','block','date','week_i','sample_case','rate20','rate60','rate_change','breadth21','market_breadth_up_fraction']}
            base.update(method=method,position=i,followup_known=valid_window(g,i,1,8))
            if base['followup_known']:
                future=g.iloc[i+1:i+9]
                if future.rate20.isna().any():base['followup_known']=False
            if base['followup_known']:
                positive=int(future.rate20.gt(0).sum())
                base.update(positive_weeks=positive,development='SUSTAINED_6_OF_8' if positive>=6 else 'NO_POSITIVE_WEEK' if positive==0 else 'TRANSIENT_OR_NOT_YET_SUSTAINED')
            else:base.update(positive_weeks=np.nan,development='UNKNOWN')
            # All first confirmations include current week, which may already satisfy condition.
            for name,mask in [('short_positive',g.rate5.gt(0)),('medium_positive',g.rate20.gt(0)),('breadth_majority',g.breadth21.ge(.5)),('broad_confirmation',g.broad_confirmation),('long_confirmation',g.long_confirmation),('old_top10',g.old_top10)]:
                at=None
                for j in range(i,min(len(g),i+9)):
                    if not valid_window(g,i,0,j-i):break
                    if bool(mask.iloc[j]):at=j;break
                base[name+'_delay']=np.nan if at is None else int(g.week_i.iloc[at]-r.week_i)
                base[name+'_relative_move']=np.nan if at is None else float(np.expm1(g.x.iloc[at]-r.x))
            episodes.append(base)
    for kind in ['trough_w2','trough_w4','acceleration_break']:
        last=-1000
        for i,r in g.iterrows():
            if not (pd.Timestamp('2021-01-01')<=r.date<=pd.Timestamp('2025-12-31')):continue
            if not r.eligible or not valid_window(g,i,-4,8):continue
            x=g.x.to_numpy();after=x[i+1:i+9]
            sustained=int((after>x[i]).sum())>=6 and slope(x[i:i+9])>0
            before=slope(x[i-4:i+1]);flag=False
            if kind.startswith('trough'):
                w=int(kind[-1]);flag=x[i]==np.min(x[i-w:i+w+1]) and before<0 and sustained
            else:flag=before>0 and slope(x[i:i+5])>before and sustained
            if not flag or r.week_i-last<8:continue
            last=r.week_i
            refs.append({k:r[k] for k in ['era','industry_code','industry_name','block','date','week_i','sample_case']}|{'reference':kind,'position':i})
    return episodes,refs,suppressed


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    p,m,weeks=make_panel();p.to_parquet('/tmp/ep33_onset_panel.parquet',index=False)
    ep=[];ref=[];supp=[]
    for _,g in p.groupby(KEY):
        e,r,s=process(g);ep+=e;ref+=r;supp+=s
    e=pd.DataFrame(ep);r=pd.DataFrame(ref);e.to_csv(OUT/'episodes.csv.gz',index=False);r.to_csv(OUT/'references.csv.gz',index=False)
    pd.DataFrame(supp).to_csv(OUT/'suppressed_repeat_edges.csv.gz',index=False)
    summary=[];yearly=[]
    for scope,z in [('all',e),('outside_sample',e[~e.sample_case])]:
        for method,g in z.groupby('method'):
            known=g[g.followup_known]
            summary.append(dict(scope=scope,method=method,episodes=len(g),known=len(known),unknown=int((~g.followup_known).sum()),
                sustained=int(known.development.eq('SUSTAINED_6_OF_8').sum()),sustained_fraction=known.development.eq('SUSTAINED_6_OF_8').mean(),
                no_improvement=int(known.development.eq('NO_POSITIVE_WEEK').sum()),transient=int(known.development.eq('TRANSIENT_OR_NOT_YET_SUSTAINED').sum())))
            for y,a in g.groupby(g.date.dt.year):
                k=a[a.followup_known];yearly.append(dict(scope=scope,method=method,year=y,episodes=len(a),known=len(k),sustained_fraction=k.development.eq('SUSTAINED_6_OF_8').mean()))
    pd.DataFrame(summary).to_csv(OUT/'development_summary.csv',index=False);pd.DataFrame(yearly).to_csv(OUT/'development_annual.csv',index=False)
    # Matching is entirely evaluation-side. Same-industry events can overlap; not independent precision.
    matches=[]
    lookup={k:g for k,g in e.groupby(KEY)}
    for _,rr in r.iterrows():
        candidates=lookup.get(tuple(rr[k] for k in KEY),e.iloc[:0])
        for method in METHODS:
            for band in [2,4,8]:
                a=candidates[candidates.method.eq(method)&candidates.week_i.between(rr.week_i-band,rr.week_i+band)].sort_values('date')
                first=a.iloc[0] if len(a) else None
                matches.append(dict(reference=rr.reference,era=rr.era,industry_code=rr.industry_code,date=rr.date,sample_case=rr.sample_case,
                    method=method,band=band,matched=first is not None,delay=np.nan if first is None else first.week_i-rr.week_i,
                    prompt_date=None if first is None else first.date))
    mat=pd.DataFrame(matches);mat.to_csv(OUT/'reference_matches.csv.gz',index=False)
    sums=[]
    for (reference,method,band),g in mat.groupby(['reference','method','band']):
        a=g[g.matched];sums.append(dict(reference=reference,method=method,band=band,references=len(g),matched=len(a),recall=len(a)/len(g),
                                      median_delay=a.delay.median(),early_or_same=int(a.delay.le(0).sum()),late=int(a.delay.gt(0).sum())))
    pd.DataFrame(sums).to_csv(OUT/'reference_summary.csv',index=False)
    pe=e[e.method.eq('pressure_easing')];delays=[]
    for name in ['short_positive','medium_positive','breadth_majority','broad_confirmation','long_confirmation','old_top10']:
        a=pe[name+'_delay'];delays.append(dict(condition=name,episodes=len(pe),observed=int(a.notna().sum()),not_observed=int(a.isna().sum()),
            already_at_prompt=int(a.eq(0).sum()),median_delay=a.median(),median_relative_move=pe[name+'_relative_move'].median()))
    pd.DataFrame(delays).to_csv(OUT/'pressure_confirmation_delays.csv',index=False)
    coverage=p[p.date.between('2021-01-01','2025-12-31')].groupby('date').agg(observed_rows=('date','size'),eligible=('eligible','sum'))
    coverage.to_csv(OUT/'coverage.csv')
    inputs=[SOURCE/'daily_industries.parquet',SOURCE/'CSI_ALL.parquet',EP/'rounds/r07_process_test_plan.md',EP/'src/onset_replay.py',Path(__file__),EP/'outputs/r06/cases.csv',EP/'outputs/r03/selected.csv.gz']
    (OUT/'receipt.json').write_text(json.dumps({'stage':'case_driven_process_exploration','no_future_payoff_columns_used':True,'inputs':{str(q):sha(q) for q in inputs}},indent=2)+'\n')
    print(pd.DataFrame(summary).query('scope=="all"').to_string(index=False))
    print(pd.DataFrame(delays).to_string(index=False))
    print(pd.DataFrame(sums).query('band==4 and reference=="trough_w4"').to_string(index=False))

if __name__=='__main__':main()
