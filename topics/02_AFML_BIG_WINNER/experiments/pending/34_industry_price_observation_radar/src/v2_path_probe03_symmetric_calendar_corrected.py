"""Event-independent path identity prototype; never used as a signal input."""
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/ep34-mpl-cache')
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP, PRIOR, sha


def excursions(y):
    y=np.asarray(y,dtype=float)
    assert np.isfinite(y).all()
    n=len(y); rows=[]
    if n<9:return rows
    def scale(t):return float(max(.002,2*np.median(np.abs(np.diff(y[t-8:t+1])))))
    low=8; eps=scale(low); active=False; seen=None; confirmed=None; peak=low
    def record(end,breach):
        return dict(start_i=low,visible_i=seen,confirm_i=confirmed,end_i=end,
                    breach_i=breach,peak_i=peak,epsilon=eps,
                    left_context_unknown=bool(low==8 and y[8]>y[0]),
                    status='CONFIRMED' if confirmed is not None else
                           'UNCONFIRMED_INTERRUPTED' if breach is not None else 'RIGHT_UNKNOWN',
                    right_open=breach is None,peak_log_gain=float(y[peak]-y[low]),
                    final_log_gain=float(y[end]-y[low]))
    for i in range(9,n):
        if not active:
            if y[i]<=y[low]:
                low=i;eps=scale(low)
            elif y[i]-y[low]>=eps:
                active=True;seen=i;peak=i;confirmed=None
        if active:
            if y[i]>y[peak]:peak=i
            if y[peak]-y[i]>=eps:
                rows.append(record(i-1,i))
                active=False;low=i;eps=scale(low);seen=None;confirmed=None;peak=low
            elif confirmed is None and i-low>=4 and (y[i-3:i+1]>y[low]).all() and y[i]-y[low]>=eps:
                confirmed=i
    if active:rows.append(record(n-1,None))
    return rows


def checks():
    decline=-.003*np.arange(16)
    base=decline[-1]
    paths={
      'long_gain_then_decline':np.r_[-.003*np.arange(16),-.045+.03*np.arange(1,51),1.455-.04*np.arange(1,13)],
      'flat':np.zeros(60),
      'decline':-.003*np.arange(60),
      'warming':np.r_[decline,base+.003*np.arange(1,31)],
      'warming_then_heating':np.r_[decline,base+.003*np.arange(1,16),base+.045+.009*np.arange(1,26)],
      'pulse':np.r_[decline,base+.05,base,np.repeat(base,15)],
      'interrupt_restart':np.r_[decline,base+.003*np.arange(1,16),base-.03,base-.03+.004*np.arange(1,21)],
      'right_unknown':np.r_[decline,base+.02,base+.025],
      'confirmed_open':np.r_[decline,base+.003*np.arange(1,8)],
      'steady_left_unknown':.003*np.arange(60),
      'smooth_acceleration':np.r_[decline,base+.0005*np.arange(1,31)**2],
    }
    expected={'long_gain_then_decline':1,'flat':0,'decline':0,'warming':1,'warming_then_heating':1,'pulse':0,
              'interrupt_restart':2,'right_unknown':0,'confirmed_open':1,
              'steady_left_unknown':1,'smooth_acceleration':1}
    result=[]
    for name,y in paths.items():
        rr=excursions(y); actual=sum(r['status']=='CONFIRMED' for r in rr)
        ok=actual==expected[name]
        if name=='long_gain_then_decline':ok=ok and len(rr)==1 and rr[0]['breach_i'] is not None
        if name=='right_unknown':ok=ok and len(rr)==1 and rr[0]['status']=='RIGHT_UNKNOWN'
        if name=='steady_left_unknown':ok=ok and rr[0]['left_context_unknown']
        if name=='pulse':ok=ok and len(rr)==1 and rr[0]['status']=='UNCONFIRMED_INTERRUPTED'
        # Scaling NAV is translation in log space. Compare discrete identities,
        # allowing only floating-point noise in amplitudes.
        shifted=excursions(y+2)
        fields=['start_i','visible_i','confirm_i','end_i','breach_i','status','left_context_unknown']
        scale_ok=[{k:r[k] for k in fields} for r in rr]==[{k:r[k] for k in fields} for r in shifted]
        result.append(dict(path=name,expected_confirmed=expected[name],actual_confirmed=actual,
                           semantic_pass=bool(ok),scale_invariant=scale_ok,processes=rr,log_prices=y.tolist()))
    return result


def main():
    out=EP/'outputs/r00_v2_path_probe03_symmetric_calendar_corrected'
    if out.exists():raise FileExistsError('Preserve prototype run')
    out.mkdir()
    tests=checks();(out/'checks.json').write_text(json.dumps(tests,indent=2)+'\n')
    if not all(x['semantic_pass'] and x['scale_invariant'] for x in tests):
        raise AssertionError('Preserve failed checks; no full-data run')
    receipt=json.loads((PRIOR/'receipt.json').read_text())
    calendar=Path(next(k for k in receipt['inputs'] if k.endswith('/calendar.parquet')))
    inputs=[PRIOR/'daily_industries.parquet',calendar,EP/'outputs/r01/weekly_catalog.parquet',
            EP/'outputs/r00_v2_label_probe02/segments.parquet',
            EP/'protocols/r00_v2/path_probe03/plan.md',EP/'protocols/r00_v2/path_probe03/symmetric_interruption_plan.md',Path(__file__)]
    hashes={str(p):sha(p) for p in inputs}
    raw=pd.read_parquet(inputs[0],columns=['date','day_i','era','industry_code','industry_name','block','nav'])
    cal=pd.read_parquet(calendar); cal['week']=cal.date.dt.to_period('W-SUN')
    expected=cal.groupby('week').size()
    cat=pd.read_parquet(inputs[2],columns=['era','industry_code','industry_name']).drop_duplicates(['era','industry_code'])
    valid=raw.nav.gt(0)&raw.block.notna()
    groups=raw[valid].groupby(['era','industry_code','block'],sort=True)
    records=[];weeks=[];prices={}
    for key,g in groups:
        g=g.sort_values('day_i').copy(); assert np.all(np.diff(g.day_i)==1)
        g['week']=g.date.dt.to_period('W-SUN');g['y']=np.log(g.nav)
        w=g.groupby('week').agg(y=('y','median'),start=('date','min'),end=('date','max'),days=('date','size')).reset_index()
        w['complete']=w.days.eq(w.week.map(expected))
        if cal.date.max().weekday()<4:
            w.loc[w.week.eq(cal.date.max().to_period('W-SUN')),'complete']=False
        w['run']=(~w.complete).cumsum()
        for r in w[~w.complete].itertuples():
            weeks.append(dict(era=key[0],industry_code=key[1],block=int(key[2]),week=str(r.week),
                              state='PARTIAL_WEEK_UNKNOWN',process_id=None))
        for run,ww in w[w.complete].groupby('run'):
            ww=ww.reset_index(drop=True); y=ww.y.to_numpy()
            assert len(ww)<2 or np.all(np.diff(expected.index.get_indexer(ww.week))==1)
            state=np.array(['CONTEXT_INSUFFICIENT' if i<8 else 'NO_IDENTIFIED_EXCURSION' for i in range(len(ww))],dtype=object)
            ids=np.full(len(ww),None,dtype=object)
            for r in excursions(y):
                pid=f'L03S-{len(records)+1:06d}'
                rec=dict(**r,process_id=pid,era=key[0],industry_code=key[1],industry_name=g.industry_name.iloc[0],
                         block=int(key[2]),complete_week_run=int(run),weeks=r['end_i']-r['start_i']+1)
                for field in ['start','visible','confirm','end','breach','peak']:
                    i=r[field+'_i']
                    rec[field+'_date']=None if i is None else ww.end.iloc[i].strftime('%Y-%m-%d')
                rec['reference_week_start']=ww.start.iloc[r['start_i']].strftime('%Y-%m-%d')
                a,b=r['start_i'],r['end_i']
                state[a:b+1]=r['status'];ids[a:b+1]=pid
                rec['max_weekly_drawdown']=float(np.expm1((y[a:b+1]-np.maximum.accumulate(y[a:b+1])).min()))
                records.append(rec)
            for i,r in enumerate(ww.itertuples()):
                weeks.append(dict(era=key[0],industry_code=key[1],block=int(key[2]),week=str(r.week),
                                  state=state[i],process_id=ids[i]))
        prices[key]=g
    r=pd.DataFrame(records);w=pd.DataFrame(weeks)
    r.to_parquet(out/'processes.parquet',index=False);w.to_parquet(out/'weekly_evaluation_states.parquet',index=False)
    counts=raw.groupby(['era','industry_code']).agg(raw_rows=('date','size'),valid_rows=('nav',lambda x:int(x.gt(0).sum()))).reset_index()
    cat.merge(counts,how='left').to_csv(out/'directory.csv',index=False)
    r.assign(year=r.start_date.str[:4]).groupby(['era','year','status','left_context_unknown']).size().rename('count').to_csv(out/'annual.csv')
    old=pd.read_parquet(inputs[3]);bridges=[]
    for key,gg in r.groupby(['era','industry_code','block']):
        ss=old[(old.era==key[0])&(old.industry_code==key[1])&(old.block==key[2])]
        for p in gg.itertuples():
            match=ss[(ss.end_date>=p.reference_week_start)&(ss.start_date<=p.end_date)]
            for z in match.itertuples():bridges.append(dict(process_id=p.process_id,old_segment_id=z.segment_id,old_kind=z.kind))
    pd.DataFrame(bridges).to_parquet(out/'old_segment_interval_bridge.parquet',index=False)
    selected=r.sort_values(['start_date','process_id']).groupby(['era','status'],sort=True).head(1)
    selected.to_csv(out/'selected_cases.csv',index=False)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    font='/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc';font_manager.fontManager.addfont(font)
    plt.rcParams['font.family']=font_manager.FontProperties(fname=font).get_name()
    plt.rcParams['axes.unicode_minus']=False
    fig,axes=plt.subplots(len(selected),1,figsize=(12,3.1*len(selected)),squeeze=False)
    for ax,p in zip(axes.flat,selected.itertuples()):
        g=prices[(p.era,p.industry_code,p.block)]
        q=g[g.date.between(pd.Timestamp(p.reference_week_start)-pd.Timedelta(days=70),pd.Timestamp(p.end_date)+pd.Timedelta(days=35))]
        ax.plot(q.date,q.nav/q.nav.iloc[0]*100,color='#333')
        ax.axvspan(pd.Timestamp(p.start_date),pd.Timestamp(p.end_date),alpha=.12,color='green')
        ax.axvline(pd.Timestamp(p.visible_date),color='orange',label='可辨上升')
        if p.confirm_date is not None:ax.axvline(pd.Timestamp(p.confirm_date),color='green',label='持续性确认')
        if p.breach_date is not None:ax.axvline(pd.Timestamp(p.breach_date),color='red',label='回吐终止')
        ax.set_title(f'{p.process_id} {p.industry_name} {p.era} {p.status} 左边界未知={p.left_context_unknown}')
        ax.legend();ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(out/'cases.png',dpi=110);plt.close(fig)
    summary=dict(scope='Parent identity prototype, enhancement children and alert matching not defined',
        directory=len(cat),valid_daily_rows=int(valid.sum()),invalid_daily_rows=int((~valid).sum()),
        candidate_parents=len(r),status=r.status.value_counts().to_dict(),
        known_context_status=r[~r.left_context_unknown].status.value_counts().to_dict(),
        left_context_unknown=int(r.left_context_unknown.sum()),right_open=int(r.right_open.sum()),
        weekly_states=w.state.value_counts().to_dict(),
        epsilon_quantiles=r.epsilon.quantile([.1,.5,.9]).to_dict(),
        peak_gain_quantiles=np.expm1(r.peak_log_gain).quantile([.1,.5,.9]).to_dict(),
        weeks_quantiles=r.weeks.quantile([.1,.5,.9]).to_dict(),
        semantic_checks=len(tests),semantic_checks_passed=sum(x['semantic_pass'] and x['scale_invariant'] for x in tests))
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    (out/'receipt.json').write_text(json.dumps(dict(inputs=hashes,artifacts={p.name:sha(p) for p in out.iterdir() if p.is_file()}),indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
