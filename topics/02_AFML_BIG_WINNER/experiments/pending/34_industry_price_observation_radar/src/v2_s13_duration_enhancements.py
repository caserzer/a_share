"""Continuous retrospective trend changes within immutable price-path parents."""
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/ep34-mpl-cache')
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP, PRIOR, sha


def continuous_fit(y):
    y=np.asarray(y,float);n=len(y);t=np.arange(n,dtype=float)
    if n<2:return dict(knots=[],changes=[],slopes=[],fitted=y.tolist(),penalty=None)
    dd=np.diff(y,n=2)
    noise=max(.002,float(np.median(np.abs(dd-np.median(dd)))/(.67448975*np.sqrt(6)))) if len(dd) else .002
    penalty=3*np.log(n)*noise**2
    def solve(knots):
        x=np.column_stack([np.ones(n),t]+[np.maximum(0,t-k) for k in knots])
        beta=np.linalg.lstsq(x,y,rcond=None)[0];fit=x@beta
        return float(np.sum((y-fit)**2)),beta,fit
    knots=[];rss,beta,fit=solve(knots)
    while True:
        best=None
        for k in range(4,n-4):
            if any(abs(k-v)<4 for v in [0,n-1]+knots):continue
            kk=sorted(knots+[k]);rr,bb,ff=solve(kk)
            if best is None or rr<best[0]-1e-12:best=(rr,kk,bb,ff)
        if best is None or rss-best[0]<=penalty+1e-12:break
        rss,knots,beta,fit=best
    slopes=np.r_[beta[1],beta[1]+np.cumsum(beta[2:])]
    return dict(knots=knots,changes=beta[2:].tolist(),slopes=slopes.tolist(),
                fitted=fit.tolist(),penalty=float(penalty),noise=float(noise),rss=float(rss))


def first_support(y,start,end):
    y=np.asarray(y,float)
    return next((c for c in range(start+4,end+1) if (y[c-3:c+1]>y[start]).all()),None)


def enhancements(y):
    y=np.asarray(y,float);f=continuous_fit(y);rows=[];start=None
    for j,k in enumerate(f['knots']):
        delta=f['changes'][j]
        if delta<=1e-10:
            if start is not None:
                start['end_i']=k;rows.append(start);start=None
            continue
        prior=f['slopes'][j];after=f['slopes'][j+1]
        eligible=prior>=-1e-10 and after>=.002-1e-10 and delta>=.002-1e-10 and y[k]>=y[k-4]-1e-12
        if start is None and eligible:
            supported=bool((y[k+1:k+5]>y[k]).all())
            start=dict(start_i=k,end_i=len(y)-1,confirm_i=k+4 if supported else None,
                       prior_slope=float(prior),after_slope=float(after),delta=float(delta),
                       status='PATH_SUPPORTED' if supported else 'NOT_RETAINED',positive_knots=1)
        elif start is not None:start['positive_knots']+=1
    if start is not None:rows.append(start)
    for row in rows:
        row['confirm_i']=first_support(y,row['start_i'],row['end_i'])
        row['status']='PATH_SUPPORTED' if row['confirm_i'] is not None else 'NOT_RETAINED'
    return f,rows


def synthetic():
    t=np.arange(81.)
    paths={'flat':np.zeros(81),'steady':.003*t,
           'single_heating':.003*t+.009*np.maximum(0,t-40),
           'smooth_heating':.003*t+.0002*t*t,
           'two_heatings':.003*t+.009*np.maximum(0,t-20)-.009*np.maximum(0,t-40)+.012*np.maximum(0,t-60),
           'pulse':np.where(t==40,.15,0.),
           'slowing_decline':-.009*t+.007*np.maximum(0,t-40),
           'warming':-.003*t+.009*np.maximum(0,t-40)}
    expected={'flat':0,'steady':0,'single_heating':1,'smooth_heating':1,'two_heatings':2,'pulse':0,'slowing_decline':0,'warming':0}
    result=[]
    for name,y in paths.items():
        f,rr=enhancements(y);_,shift=enhancements(y+2)
        count=sum(r['status']=='PATH_SUPPORTED' for r in rr)
        key=lambda r:(r['start_i'],r['end_i'],r['confirm_i'],r['status'])
        result.append(dict(path=name,expected=expected[name],supported=count,
                           pass_semantic=count==expected[name],scale_invariant=list(map(key,rr))==list(map(key,shift)),
                           fit=f,children=rr,log_prices=y.tolist()))
    return result


def main():
    out=EP/'outputs/v2_s13_duration_enhancements'
    if out.exists():raise FileExistsError('Preserve first run')
    out.mkdir();test=synthetic()
    support_checks=[first_support([0,-.01,.01,.02,.03,.04],0,5)==5,
        first_support([0,.15,0,0,0,0],0,5) is None,
        first_support([0,.01,.02,.03],0,3) is None,
        first_support([0,-.01,.01,.02,.03,.04],0,4) is None]
    (out/'support_checks.json').write_text(json.dumps(support_checks)+'\n')
    assert all(support_checks)
    (out/'checks.json').write_text(json.dumps(test,indent=2)+'\n')
    if not all(x['pass_semantic'] and x['scale_invariant'] for x in test):
        print(json.dumps([{k:v for k,v in x.items() if k not in ['fit','children','log_prices']} for x in test],indent=2))
        raise AssertionError('Semantic failure, full-directory run not started')
    parent_path=EP/'outputs/v2_s12_full_directory_duration/processes.parquet'
    paths=[parent_path,PRIOR/'daily_industries.parquet',EP/'protocols/r00_v2/path_probe03/enhancement_plan.md',EP/'protocols/r00_v2/path_probe03/enhancement_recovery_plan.md',EP/'protocols/v2_s13/plan.md',Path(__file__)]
    inputs={str(p):sha(p) for p in paths}
    parents=pd.read_parquet(parent_path)
    raw=pd.read_parquet(paths[1],columns=['era','industry_code','industry_name','block','date','day_i','nav'])
    raw=raw[raw.nav.gt(0)&raw.block.notna()].copy();raw['week']=raw.date.dt.to_period('W-SUN');raw['y']=np.log(raw.nav)
    groups={key:g.sort_values('date') for key,g in raw.groupby(['era','industry_code','block'])}
    allfits=[];children=[];adjacent=[];cache={}
    for p in parents.itertuples():
        key=(p.era,p.industry_code,p.block);g=groups[key]
        part=g[g.date.between(p.reference_week_start,p.end_date)]
        w=part.groupby('week').agg(y=('y','median'),end=('date','max')).reset_index()
        assert len(w)==p.weeks
        f,rr=enhancements(w.y.to_numpy());cache[p.process_id]=(w,f)
        allfits.append(dict(parent_id=p.process_id,era=p.era,industry_code=p.industry_code,knots=len(f['knots']),
                            weeks=len(w),parent_status=p.status,left_unknown=p.left_context_unknown,
                            right_open=p.right_open,fit_json=json.dumps(f)))
        for r in rr:
            cid=f'H04D-{len(children)+1:06d}'
            end=r['end_i'];c=r['confirm_i']
            if c is None and p.right_open and end==len(w)-1:r['status']='RIGHT_UNKNOWN'
            children.append(dict(**r,child_id=cid,parent_id=p.process_id,era=p.era,industry_code=p.industry_code,
                industry_name=p.industry_name,block=p.block,parent_status=p.status,parent_left_unknown=p.left_context_unknown,
                parent_right_open=p.right_open,end_unknown=bool(p.right_open and end==len(w)-1),
                start_date=str(w.end.iloc[r['start_i']].date()),end_date=str(w.end.iloc[end].date()),
                confirm_date=None if c is None else str(w.end.iloc[c].date())))
    for key,gg in parents.groupby(['era','industry_code','block','complete_week_run']):
        gg=gg.sort_values('start_date');rawg=groups[key[:3]];bydate=rawg.set_index('date')
        prev=None
        for p in gg.itertuples():
            if prev is not None:
                lo=pd.Timestamp(prev.end_date);hi=pd.Timestamp(p.start_date)
                gap=int(bydate.loc[hi,'day_i']-bydate.loc[lo,'day_i'])
                old=cache[prev.process_id][0];peak=float(old.y.max())
                ww=cache[p.process_id][0];recovered=ww[ww.y>=peak]
                adjacent.append(dict(previous_parent=prev.process_id,next_parent=p.process_id,era=p.era,industry_code=p.industry_code,
                    previous_status=prev.status,next_status=p.status,previous_end=prev.end_date,next_start=p.start_date,
                    trading_day_gap=gap,week_gap=int(ww.week.iloc[0].ordinal-old.week.iloc[-1].ordinal),
                    previous_peak_recovered_within_next=bool(len(recovered)),
                    recovery_date=None if recovered.empty else str(recovered.end.iloc[0].date())))
            prev=p
    fits=pd.DataFrame(allfits);ch=pd.DataFrame(children);ad=pd.DataFrame(adjacent)
    fits.to_parquet(out/'parent_fits.parquet',index=False);ch.to_parquet(out/'children.parquet',index=False);ad.to_parquet(out/'adjacent_parents.parquet',index=False)
    ch.assign(year=ch.start_date.str[:4]).groupby(['era','year','status']).size().rename('count').to_csv(out/'annual.csv')
    selected=ch.sort_values(['start_date','child_id']).groupby(['era','status'],sort=True).head(1)
    selected.to_csv(out/'selected_cases.csv',index=False)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    font='/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc';font_manager.fontManager.addfont(font)
    plt.rcParams['font.family']=font_manager.FontProperties(fname=font).get_name();plt.rcParams['axes.unicode_minus']=False
    fig,axes=plt.subplots(len(selected),1,figsize=(12,3.5*len(selected)),squeeze=False)
    for ax,p in zip(axes.flat,selected.itertuples()):
        w,f=cache[p.parent_id];base=w.y.iloc[0]
        ax.plot(w.end,np.exp(w.y-base)*100,label='周中位数价格',color='#333')
        ax.plot(w.end,np.exp(np.array(f['fitted'])-base)*100,label='连续折线',color='#777',linestyle='--')
        ax.axvline(pd.Timestamp(p.start_date),color='orange',label='新增强参考点')
        if p.confirm_date is not None:ax.axvline(pd.Timestamp(p.confirm_date),color='green',label='4周路径支持')
        ax.axvspan(pd.Timestamp(p.start_date),pd.Timestamp(p.end_date),color='green',alpha=.12)
        ax.set_title(f'{p.child_id} {p.industry_name} {p.era} {p.status}');ax.legend();ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(out/'cases.png',dpi=110);plt.close(fig)
    summary=dict(scope='Retrospective within-parent enhancement prototype; not alert accuracy or final labels',
                 parents=len(parents),parents_with_fit_knots=int(fits.knots.gt(0).sum()),total_fit_knots=int(fits.knots.sum()),
                 children=len(ch),status=ch.status.value_counts().to_dict(),parents_with_children=int(ch.parent_id.nunique()),
                 parent_status=ch.parent_status.value_counts().to_dict(),end_unknown=int(ch.end_unknown.sum()),
                 adjacent_pairs=len(ad),adjacent_confirmed_pairs=int((ad.previous_status.eq('CONFIRMED')&ad.next_status.eq('CONFIRMED')).sum()),
                 adjacent_peak_recovered=int(ad.previous_peak_recovered_within_next.sum()),
                 trading_day_gap_quantiles=ad.trading_day_gap.quantile([.1,.5,.9]).to_dict(),
                 semantic_checks=len(test),semantic_checks_passed=sum(x['pass_semantic'] and x['scale_invariant'] for x in test))
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'receipt.json').write_text(json.dumps(dict(inputs=inputs,artifacts={p.name:sha(p) for p in out.iterdir() if p.is_file()}),indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
