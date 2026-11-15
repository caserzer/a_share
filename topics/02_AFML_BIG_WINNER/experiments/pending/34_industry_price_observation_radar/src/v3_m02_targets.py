"""Build bounded-prefix coverage/early targets without reading final labels."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha
from v2_s11_duration_identity_guarded import excursions
from v2_s13_duration_enhancements import enhancements

TARGETS=['parent_coverage_target','parent_early_target','child_coverage_target','child_early_target']


def weekly_runs(raw,calendar):
    cal=calendar.copy();cal['week']=cal.date.dt.to_period('W-SUN');expected=cal.groupby('week').size()
    for key,g in raw[raw.nav.gt(0)&raw.block.notna()].groupby(['era','industry_code','block'],sort=True):
        g=g.sort_values('day_i').copy();assert len(g)<2 or np.all(np.diff(g.day_i)==1)
        g['week']=g.date.dt.to_period('W-SUN');g['y']=np.log(g.nav)
        w=g.groupby('week').agg(y=('y','median'),date=('date','max'),days=('date','size')).reset_index()
        complete=w.days.eq(w.week.map(expected))
        if cal.date.max().weekday()<4:complete &= w.week.ne(cal.date.max().to_period('W-SUN'))
        w['run']=(~complete).cumsum()
        for run,z in w[complete].groupby('run'):
            z=z.reset_index(drop=True)
            assert len(z)<2 or np.all(np.diff(expected.index.get_indexer(z.week))==1)
            yield (*key,int(run)),z


def prefix_targets(y,t,cache=None,horizon=8):
    if t<8 or t+horizon>=len(y):return dict.fromkeys(TARGETS), 'INSUFFICIENT_CONTEXT_OR_FUTURE',None,None
    y=np.asarray(y[:t+horizon+1],float)
    matches=[p for p in excursions(y) if p['start_i']<=t<=p['end_i']]
    assert len(matches)<=1
    result={k:0 for k in TARGETS}
    if not matches:return result,'NO_IDENTIFIED_PARENT_WITHIN8',None,None
    p=matches[0];start=p['start_i'];end=p['end_i']
    if p['left_context_unknown']:return dict.fromkeys(TARGETS),'LEFT_CONTEXT_UNKNOWN',start,None
    if p['status']!='CONFIRMED':return result,'PARENT_NOT_CONFIRMED_WITHIN8',start,None
    result['parent_coverage_target']=int(y[t]>y[start])
    result['parent_early_target']=int(start<t<=p['visible_i']+1 and y[t]>y[start])
    if cache is None:cache={}
    key=(start,end)
    if key not in cache:
        _,rows=enhancements(y[start:end+1]);cache[key]=rows
    rows=cache[key];offset=t-start;child=[r for r in rows if r['start_i']<=offset<=r['end_i']]
    assert len(child)<=1
    childref=None
    if child:
        c=child[0];childref=start+c['start_i']
        known=c['status']=='PATH_SUPPORTED' and y[t]>y[childref]
        result['child_coverage_target']=int(known)
        result['child_early_target']=int(known and t<=childref+1)
    assert result['parent_early_target']<=result['parent_coverage_target']
    assert result['child_early_target']<=result['child_coverage_target']
    return result,'PREFIX_PARENT_CONFIRMED',start,childref


def sources_and_raw():
    rawpath=PRIOR/'daily_industries.parquet'
    receipt=json.loads((PRIOR/'receipt.json').read_text());calpath=Path(next(k for k in receipt['inputs'] if k.endswith('/calendar.parquet')))
    raw=pd.read_parquet(rawpath,columns=['date','day_i','era','industry_code','block','nav'])
    return rawpath,calpath,raw,pd.read_parquet(calpath)


def main():
    out=EP/'outputs/v3_m02_targets'
    if out.exists():raise FileExistsError(out)
    out.mkdir();rawpath,calpath,raw,cal=sources_and_raw()
    panelpath=EP/'outputs/v3_m01_preparation/training_panel.parquet';panel=pd.read_parquet(panelpath)
    selected=set(map(tuple,panel.loc[panel.eligible,['era','industry_code','block','date']].values))
    sources=[rawpath,calpath,panelpath,EP/'protocols/v3_r00/m02_maturity_plan.md',EP/'src/v2_s11_duration_identity_guarded.py',EP/'src/v2_s13_duration_enhancements.py',Path(__file__)]
    (out/'started.json').write_text(json.dumps({str(p):sha(p) for p in sources},indent=2)+'\n')
    rows=[];checks=0;fits=0
    for number,(key,w) in enumerate(weekly_runs(raw,cal)):
        y=w.y.to_numpy();cache={}
        for t,date in enumerate(w.date):
            if (*key[:3],date) not in selected:continue
            labels,reason,pref,cref=prefix_targets(y,t,cache)
            available=w.date.iloc[t+8] if t+8<len(w) else pd.NaT
            if t>=8 and t+9<len(y) and t%29==0:
                altered=y.copy();altered[t+9:]+=np.linspace(10,20,len(y)-t-9)
                check=prefix_targets(altered,t,{})
                assert check==(labels,reason,pref,cref);checks+=1
            rows.append(dict(era=key[0],industry_code=key[1],block=key[2],date=date,**labels,target_reason=reason,
                target_available_date=available,parent_reference=None if pref is None else f'{key}/{w.date.iloc[pref].date()}',
                child_reference=None if cref is None else f'{key}/{w.date.iloc[pref].date()}/{w.date.iloc[cref].date()}'))
        fits+=len(cache)
        if number%100==0:print('target groups',number,'candidate rows',len(rows),'prefix child fits',fits,flush=True)
    targets=pd.DataFrame(rows)
    d=panel.merge(targets,on=['era','industry_code','block','date'],how='left',validate='one_to_one')
    a=d.loc[d.eligible,'label'];b=d.loc[d.eligible,'parent_early_target']
    assert ((a==b)|(a.isna()&b.isna())).all(),'M01 parity failure'
    assert d.loc[d.eligible,'label_available_date'].fillna(pd.Timestamp('1900-01-01')).equals(d.loc[d.eligible,'target_available_date'].fillna(pd.Timestamp('1900-01-01')))
    support=[]
    for year in range(2020,2027):
        cutoff=pd.Timestamp(year=year,month=1,day=1)
        for target in TARGETS:
            tr=d[d.eligible&d[target].notna()&d.target_available_date.lt(cutoff)]
            identity='child_reference' if target.startswith('child') else 'parent_reference'
            support.append(dict(year=year,target=target,rows=len(tr),positive=int(tr[target].sum()),negative=int(tr[target].eq(0).sum()),positive_references=tr.loc[tr[target].eq(1),identity].nunique(),
                latest_available=str(tr.target_available_date.max()),meets_m01_row_support=len(tr)>=1000 and tr[target].sum()>=50 and tr[target].eq(0).sum()>=50))
    d.to_parquet(out/'training_panel.parquet',index=False);pd.DataFrame(support).to_csv(out/'training_support.csv',index=False)
    d.assign(year=d.date.dt.year).groupby(['year','era','eligible','target_reason'],dropna=False).size().rename('rows').to_csv(out/'inventory.csv')
    summary=dict(rows=len(d),candidates=int(d.eligible.sum()),future_tail_checks=checks,prefix_child_fits=fits,m01_parent_early_parity=True,final_labels_read=False,
        positive={k:int(d.loc[d.eligible,k].sum()) for k in TARGETS},known={k:int(d.loc[d.eligible,k].notna().sum()) for k in TARGETS})
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'receipt.json').write_text(json.dumps(dict(inputs={str(p):sha(p) for p in sources},artifacts={p.name:sha(p) for p in out.iterdir() if p.is_file()}),indent=2)+'\n')
    print(json.dumps(summary,indent=2));print(pd.DataFrame(support).to_string(index=False))


if __name__=='__main__':main()
