"""Deterministic descriptive casebook; no changes to labels or predictions."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from audit_local_inputs import EP,PRIOR,sha
from post_alert_evaluation import post_alert_result


def main():
    out=EP/'outputs/r01_cases';out.mkdir(exist_ok=True)
    if (out/'casebook.json').exists():raise FileExistsError('casebook exists')
    afile=EP/'outputs/r01/evaluated_new_observations.parquet'
    pfile=EP/'outputs/r00_metric_denominators/full_process_registry.parquet'
    rawfile=PRIOR/'daily_industries.parquet'
    a=pd.read_parquet(afile).sort_values(['date','alert_id']);p=pd.read_parquet(pfile).set_index('process_id')
    raw=pd.read_parquet(rawfile);groups={k:g.sort_values('day_i') for k,g in raw.groupby(['era','industry_code'])};asof=int(raw.day_i.max())
    allrows=[]
    for r in a.itertuples():
        g=groups[(r.era,r.industry_code)];kwargs={}
        if pd.notna(r.process_id):
            proc=p.loc[r.process_id];kwargs=dict(process_end=int(proc.end_day_i),process_end_observed=not proc.right_censored)
        result=post_alert_result(g.day_i.to_numpy(),g.nav.to_numpy(),g.block.to_numpy(float,na_value=np.nan),r.day,asof,**kwargs)
        assert result['status']==r.post_evaluation
        allrows.append(dict(alert_id=r.alert_id,**result))
    metrics=pd.DataFrame(allrows)
    metrics.to_parquet(out/'all_alert_path_metrics.parquet',index=False)
    a=a.merge(metrics,on='alert_id',validate='one_to_one')
    late=pd.read_parquet(EP/'outputs/r01/failure_audit_rows.parquet')
    lateids=set(late.loc[late.late_reference_exists & late.post_evaluation.eq('POST_VALID'),'alert_id'])
    selected=[];paths=[]
    for era,sub in a.groupby('era'):
        masks={
            'TIMELY_SUCCESS':sub.outcome.eq('SUCCESS'),
            'MATCHED_POST_FAILURE':sub.outcome.eq('FIRST_FAILURE') & sub.post_evaluation.eq('POST_FAILED'),
            'SHORT_REBOUND':sub.post_evaluation.eq('POST_FAILED') & sub.peak_return.ge(.08) & (sub.terminal_return.lt(.05)|sub.retained_days.lt(40)),
            'PROCESS_INTERRUPTED':sub.post_evaluation.eq('PROCESS_ENDED'),
            'LATE_REFERENCE_POST_VALID':sub.alert_id.isin(lateids),
            'UNKNOWN_BOUNDARY':sub.outcome.eq('UNKNOWN')}
        fig,axes=plt.subplots(3,2,figsize=(13,11),constrained_layout=True)
        for ax,(category,mask) in zip(axes.flat,masks.items()):
            choices=sub[mask].sort_values(['date','alert_id'])
            if choices.empty:
                ax.set_title(category+' : no case');continue
            r=choices.iloc[0];g=groups[(era,r.industry_code)]
            origin=None if pd.isna(r.process_id) else int(p.loc[r.process_id].start_day_i)
            if category=='LATE_REFERENCE_POST_VALID':origin=int(p.loc[late.set_index('alert_id').loc[r.alert_id].late_process_id].start_day_i)
            window=g[g.day_i.between(r.day-60,r.day+65)].copy();base=float(g.loc[g.day_i.eq(r.day),'nav'].iloc[0])
            # Keep absent dates and invalid/changed blocks visibly broken.
            plot=window.set_index('day_i').reindex(range(int(r.day)-60,int(r.day)+66))
            originalblock=g.loc[g.day_i.eq(r.day),'block'].iloc[0]
            y=plot.nav/base-1;y=y.where(plot.block.eq(originalblock))
            ax.plot(np.arange(-60,66),100*y,color='#2563eb',lw=1.4)
            ax.axvline(0,color='black',label='alert');ax.axhline(0,color='gray',lw=.6)
            ax.axhline(5,color='green',ls=':',lw=.8);ax.axhline(-5,color='red',ls=':',lw=.8)
            if origin is not None:ax.axvline(origin-r.day,color='#d97706',ls='--',label='process origin')
            ax.axvspan(0,60,color='#dbeafe',alpha=.25);ax.grid(alpha=.2)
            ax.set_title(f'{category}\n{r.industry_code} {r.date.date()}',fontsize=10)
            ax.set_xlabel('Trading sessions from alert');ax.set_ylabel('NAV return from alert (%)')
            record=dict(category=category,era=era,industry_code=r.industry_code,industry_name=str(g.industry_name.iloc[-1]),
                        alert_id=r.alert_id,date=str(r.date.date()),day=int(r.day),outcome=r.outcome,
                        post_evaluation=r.post_evaluation,label_coverage_known=bool(r.label_coverage_known),
                        origin_day=origin,delta=None if origin is None else int(r.day-origin),
                        metrics={k:(None if pd.isna(r[k]) else float(r[k])) for k in ['peak_return','terminal_return','retained_days','floor_return','max_drawdown']},
                        failed_conditions=r.failed_conditions if isinstance(r.failed_conditions,list) else [],
                        same_block_price_rows=int(y.notna().sum()))
            selected.append(record)
            paths.extend(dict(alert_id=r.alert_id,relative_day=int(i-r.day),nav_return=None if pd.isna(v) else float(v)) for i,v in y.items())
        fig.suptitle(f'{era}: earliest alert in each category; descriptive examples only',fontsize=13)
        fig.savefig(out/f'{era}_cases.png',dpi=140);plt.close(fig)
    pd.DataFrame(paths).to_parquet(out/'case_paths.parquet',index=False)
    result=dict(selection='Earliest date then alert ID per era/category; categories may overlap; not effectiveness evidence',
                short_rebound_definition='Descriptive only: failed post path, peak20 >=8%, and terminal60 <5% or retained days <40',
                late_scope='Reference only, not one-to-one validated late success',cases=selected,
                inputs={str(x):sha(x) for x in [afile,pfile,rawfile,EP/'src/r01_path_cases.py']})
    (out/'casebook.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps([dict(category=r['category'],era=r['era'],name=r['industry_name'],date=r['date'],delta=r['delta'],metrics=r['metrics'],failed=r['failed_conditions']) for r in selected],ensure_ascii=False))


if __name__=='__main__':main()
