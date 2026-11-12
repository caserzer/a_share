"""R09+ research-pool evaluation: fixed rules, joint outcome, paired date controls."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from onset_replay import EP,SOURCE,KEY,sha

HORIZONS=(63,126,252)
ID=['era','industry_code','block','date']
METHODS=['slowdown','pressure_easing','improvement_acceleration','broad_confirmation','long_confirmation','old_top10']

def joint_label(ret,excess):
    return ((ret>0)&(excess>0)).astype(float).where(ret.notna()&excess.notna())

def load_panel():
    p=pd.read_parquet('/tmp/ep33_onset_panel.parquet').sort_values(KEY+['date'])
    prev=p.groupby(KEY).week_i.shift()
    p['contiguous_previous']=p.week_i.sub(prev).eq(1)
    for method in METHODS:
        previous=p.groupby(KEY)[method].shift()
        p[method+'_entry']=p[method]&previous.eq(False)&p.contiguous_previous
        p[method+'_boundary']=p[method]&~p.contiguous_previous
    p=p[p.date.ge('2021-01-01')].copy()
    lab=pd.read_parquet('/tmp/ep33_r01_panel.parquet')
    cols=ID+['velocity','prior63']+[f'{v}{h}' for h in HORIZONS for v in ['return','excess','adverse','end']]
    p=p.merge(lab[cols],on=ID,how='left',validate='one_to_one')
    m=pd.read_parquet(SOURCE/'CSI_ALL.parquet').close.sort_index()
    for h in HORIZONS:
        p[f'win{h}']=joint_label(p[f'return{h}'],p[f'excess{h}'])
        p[f'status{h}']=np.where(p[f'win{h}'].notna(),'KNOWN',np.where(p.day_i+1+h>=len(m),'IMMATURE','MISSING_PATH'))
    p['market126']=p.date.map(m/m.shift(126)-1)
    p=p.reset_index(drop=True);p.index.name='row_id'
    return p,m

def calendar_dates():
    m=pd.read_parquet(SOURCE/'CSI_ALL.parquet').close.sort_index()
    s=pd.Series(m.index,index=m.index);w=s.groupby(s.index.to_period('W-FRI')).max()
    return pd.DatetimeIndex(w[[x.end_time.normalize()<=m.index.max() for x in w.index]]).intersection(pd.date_range('2021-01-01',m.index.max()))

def controls(p,ids):
    # IDs selected without reading outcomes; ties deterministically ordered by identity.
    z=p.loc[ids];counts=z.groupby('date').size();base=p[p.eligible & p.date.isin(counts.index)]
    ranked=base.sort_values(['date','rate20','era','industry_code'],ascending=[True,False,True,True])
    rank=ranked.groupby('date').cumcount();mom=ranked[rank.lt(ranked.date.map(counts))]
    assert len(mom)==len(z)
    return base.index,mom.index

def selections(p):
    out={}
    old=pd.read_csv(EP/'outputs/r07/episodes.csv.gz',parse_dates=['date'])
    for name in METHODS:
        out[name,'state']=p.index[p[name]&p.eligible]
        out[name,'entry']=p.index[p[name+'_entry']&p.eligible]
        keys=old[old.method.eq(name)][ID]
        z=p.reset_index().merge(keys,on=ID,how='inner',validate='one_to_one')
        out[name,'cooldown8']=pd.Index(z.loc[z.eligible,'row_id'])
    return out

def block_ci(series,block,seed=3309):
    a=np.asarray(series,float);n=len(a)
    if np.isfinite(a).sum()<8:return np.nan,np.nan
    rng=np.random.default_rng(seed);est=[]
    # Circular blocks preserve whole cross sections; no industry IID bootstrap.
    for _ in range(500):
        starts=rng.integers(0,n,size=int(np.ceil(n/block)))
        ix=((starts[:,None]+np.arange(block))%n).ravel()[:n]
        b=a[ix]
        if np.isfinite(b).any():est.append(np.nanmean(b))
    return tuple(np.quantile(est,[.025,.975]))

def evaluate(p,selection,out):
    out.mkdir(parents=True,exist_ok=True)
    dates=calendar_dates();rows=[];annual=[];weekly=[];members=[]
    allknown={h:p[p.eligible][f'win{h}'].sum() for h in HORIZONS}
    for (method,unit),ids in selection.items():
        ids=pd.Index(ids);baseids,momids=controls(p,ids)
        z=p.loc[ids];base=p.loc[baseids];mom=p.loc[momids]
        count=z.groupby('date').size().reindex(dates,fill_value=0)
        top_share=z.groupby(['era','industry_code']).size().max()/len(z) if len(z) else np.nan
        for role,idx in [('selected',ids),('momentum',momids)]:
            members.append(pd.DataFrame({'row_id':idx,'method':method,'unit':unit,'role':role}))
        for h in HORIZONS:
            col=f'win{h}';n=z[col].count();wins=z[col].sum();status=z[f'status{h}']
            rates=pd.DataFrame({'selected':z.groupby('date')[col].mean(),'all':base.groupby('date')[col].mean(),'momentum':mom.groupby('date')[col].mean()}).reindex(dates)
            diff=rates.selected-rates.momentum;diffbase=rates.selected-rates['all']
            lo,hi=block_ci(diff,max(1,round(h/5)));blo,bhi=block_ci(diffbase,max(1,round(h/5)))
            rows.append(dict(method=method,unit=unit,horizon=h,total=len(z),known=n,wins=wins,failures=n-wins,
                immature=int(status.eq('IMMATURE').sum()),missing=int(status.eq('MISSING_PATH').sum()),
                pooled_win_rate=wins/n if n else np.nan,unknown_lower=wins/len(z) if len(z) else np.nan,
                unknown_upper=(wins+len(z)-n)/len(z) if len(z) else np.nan,date_equal_win_rate=rates.selected.mean(),
                paired_dates=int(diff.notna().sum()),paired_all_delta=diffbase.mean(),all_delta_lo=blo,all_delta_hi=bhi,
                paired_momentum_delta=diff.mean(),momentum_delta_lo=lo,momentum_delta_hi=hi,
                mean_pool=count.mean(),median_pool=count.median(),empty_fraction=count.eq(0).mean(),max_industry_share=top_share,
                success_week_recall=wins/allknown[h] if unit=='state' and allknown[h] else np.nan,
                median_rate20=z.rate20.median(),median_rate60=z.rate60.median(),
                boundary_unknown=int((p[method+'_boundary']&p.eligible).sum()) if method+'_boundary' in p else np.nan))
            for year in sorted(p.date.dt.year.unique()):
                a=z[z.date.dt.year.eq(year)];r=rates[rates.index.year==year]
                annual.append(dict(method=method,unit=unit,horizon=h,year=int(year),total=len(a),known=a[col].count(),wins=a[col].sum(),pooled_win_rate=a[col].mean(),
                    date_equal_win_rate=r.selected.mean(),paired_all_delta=(r.selected-r['all']).mean(),paired_momentum_delta=(r.selected-r.momentum).mean()))
            w=rates.reset_index(names='date');w['method']=method;w['unit']=unit;w['horizon']=h;w['pool_n']=count.to_numpy();weekly.append(w)
    pd.DataFrame(rows).to_csv(out/'summary.csv',index=False)
    pd.DataFrame(annual).to_csv(out/'annual.csv',index=False)
    pd.concat(weekly,ignore_index=True).to_csv(out/'weekly_comparison.csv.gz',index=False)
    pd.concat(members,ignore_index=True).to_csv(out/'memberships.csv.gz',index=False)
    p.to_parquet(out/'evaluation_panel.parquet',index=True)
    return pd.DataFrame(rows)

def coverage(p,out):
    path=EP.parent/'32_industry_rotation_cycle_observation/extensions/v4_all_industry_review/outputs/industry_coverage.csv'
    cat=pd.read_csv(path);cat=cat[cat.level.eq('L3')]
    # Separate classification regimes, including the unobservable transition period.
    dates=pd.DataFrame({'date':calendar_dates()});dates['era']=np.where(dates.date.le('2021-11-30'),'SW2014','SW2021')
    registry=dates.merge(cat[['era','industry_code','industry_name']],on='era')
    observed=p[['date','era','industry_code','eligible','coverage','members']]
    registry=registry.merge(observed,on=['date','era','industry_code'],how='left',validate='one_to_one')
    registry['status']=np.where(registry.eligible.eq(True),'ELIGIBLE',np.where(registry.eligible.isna(),'NO_PRICE_PATH','INSUFFICIENT_HISTORY_OR_COVERAGE'))
    registry.to_csv(out/'universe_registry.csv.gz',index=False)
    registry.groupby(['date','era','status']).size().unstack(fill_value=0).to_csv(out/'coverage.csv')

def validate(p,m):
    d=pd.read_parquet(SOURCE/'daily_industries.parquet');d=d[d.level.eq('L3')]
    lookup={k:g.sort_values('date').set_index('date') for k,g in d.groupby(KEY)}
    sample=p.sample(min(180,len(p)),random_state=3309);checks=0
    for _,r in sample.iterrows():
        g=lookup[tuple(r[k] for k in KEY)];pos=g.index.get_loc(r.date)
        for h in HORIZONS:
            if pos+1+h<len(g):
                start,end=g.iloc[pos+1],g.iloc[pos+1+h];t0,t1=g.index[pos+1],g.index[pos+1+h]
                ret=end.nav/start.nav-1;excess=ret-(m.loc[t1]/m.loc[t0]-1)
                assert np.isclose(ret,r[f'return{h}']) and np.isclose(excess,r[f'excess{h}'])
                assert float(ret>0 and excess>0)==r[f'win{h}']
            else:assert pd.isna(r[f'win{h}'])
            checks+=1
    for h in HORIZONS:
        assert p.loc[p[f'status{h}'].eq('KNOWN'),f'end{h}'].le(m.index.max()).all()
    return {'sampled_raw_outcome_checks':checks,'joint_label_verified':True,'maturity_checked':True}

def main():
    out=EP/'outputs/r09';out.mkdir(parents=True,exist_ok=True)
    p,m=load_panel();checks=validate(p,m);s=evaluate(p,selections(p),out);coverage(p,out)
    inputs=[Path('/tmp/ep33_onset_panel.parquet'),Path('/tmp/ep33_r01_panel.parquet'),SOURCE/'daily_industries.parquet',SOURCE/'CSI_ALL.parquet',EP/'rounds/r09_research_pool_plan.md',Path(__file__)]
    (out/'receipt.json').write_text(json.dumps({'status':'EXECUTED_EXPLORATORY','checks':checks,'inputs':{str(f):sha(f) for f in inputs},'horizons':HORIZONS,'bootstrap':'500 circular date-block draws, lengths13/25/50 weeks; descriptive intervals not multiplicity-adjusted','limits':'historical proxy; all dates previously seen; no independent validation; cooldown8 limited to 2021-2025 per R07'},indent=2)+'\n')
    print(s[s.unit.eq('state')][['method','horizon','total','known','pooled_win_rate','paired_all_delta','paired_momentum_delta','momentum_delta_lo','momentum_delta_hi','success_week_recall','mean_pool']].to_string(index=False))
if __name__=='__main__':main()
