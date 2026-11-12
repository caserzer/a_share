import json
import math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from audit_local_inputs import EP, PRIOR, CACHE, sha


def main():
    root=EP/'outputs/r00_process_draft_v02'; out=root/'case_review';out.mkdir(exist_ok=True)
    p=pd.read_parquet(root/'processes.parquet');m=pd.read_parquet(root/'candidate_metrics.parquet')
    d=pd.read_parquet(PRIOR/'daily_industries.parquet')
    groups={k:g.sort_values('date').reset_index(drop=True) for k,g in d[d.nav.notna()].groupby(['era','industry_code','block'])}
    marketfile=CACHE/'forecast_v5/CSI_ALL.parquet';market=pd.read_parquet(marketfile).close.sort_index()
    cases=[]
    def add(g,stratum):
        if len(g):
            r=g.sample(1,random_state=3402).iloc[0].to_dict();r['stratum']=stratum;cases.append(r)
    for year,g in p.groupby(p.start_date.dt.year):add(g,'YEAR_'+str(year))
    second=p.sort_values('start').groupby('parent_id').cumcount().gt(0)
    # Use sorted frame with matching index to select a genuinely subsequent phase.
    add(p.loc[second[second].index],'NEW_HEATING_PHASE')
    add(p[p.start_at_first_evaluable_day],'LEFT_BOUNDARY')
    for reason in ['CLASSIFICATION_BOUNDARY','INTERNAL_PRICE_BREAK','RIGHT_CENSORED']:add(p[p.end_reason.eq(reason)],reason)
    for kind in ['WARMING','HEATING']:
        g=m[m.kind.eq(kind)&m.amplitude&~m.persistence].copy()
        g['start']=g.position;g['end']=g.position+60;g['start_date']=g.date
        g['end_reason']='FAILED_PERSISTENCE';g['process_id']=None
        add(g,'FAILED_'+kind)
    selected=pd.DataFrame(cases)
    selected.to_json(out/'selection.json',orient='records',force_ascii=False,date_format='iso',indent=2)
    for page in range(math.ceil(len(cases)/6)):
        fig,axs=plt.subplots(3,2,figsize=(15,12))
        for ax,r in zip(axs.flat,cases[page*6:page*6+6]):
            g=groups[(r['era'],r['industry_code'],r['block'])];a=int(r['start']);b=min(len(g)-1,max(a+60,int(r['end'])))
            lo=max(0,a-60);v=g.iloc[lo:b+1];x=np.arange(lo,b+1)-a;base=g.nav.iloc[a]
            ax.plot(x,(v.nav/base-1)*100,label='Industry')
            marketpath=market.reindex(pd.DatetimeIndex(v.date));mb=market.reindex([g.date.iloc[a]]).iloc[0]
            if np.isfinite(mb):ax.plot(x,(marketpath/mb-1)*100,label='CSI All',alpha=.7)
            ax.axvline(0,color='black',lw=.7);ax.axhline(0,color='gray',lw=.7)
            ax.axvline(int(r['end'])-a,color='red',linestyle='--',label='Phase end')
            ax.axvline(60,color='green',linestyle=':',label='Evaluation day60')
            ax.set_title(f"{r['stratum']} {r['industry_code']} {pd.Timestamp(r['start_date']).date()}\n{r['kind']} {r['end_reason']}",fontsize=9)
            ax.legend(fontsize=7);ax.set_xlabel('Trading days from reference');ax.set_ylabel('Return (%)')
        for ax in axs.flat[len(cases[page*6:page*6+6]):]:ax.set_visible(False)
        fig.tight_layout();fig.savefig(out/f'page{page+1}.png',dpi=120);plt.close(fig)
    rows=[]
    for r in p.itertuples():
        g=groups[(r.era,r.industry_code,r.block)];a=int(r.start);dates=g.date.iloc[[a,a+20,a+60]]
        v=g.nav.iloc[[a,a+20,a+60]].to_numpy();marketvals=market.reindex(pd.DatetimeIndex(dates)).to_numpy()
        row=dict(process_id=r.process_id,year=r.start_date.year)
        for h,j in [(20,1),(60,2)]:
            row[f'absolute{h}']=v[j]/v[0]-1
            row[f'market{h}']=marketvals[j]/marketvals[0]-1 if np.isfinite(marketvals[[0,j]]).all() else np.nan
            row[f'excess{h}']=row[f'absolute{h}']-row[f'market{h}']
        rows.append(row)
    context=pd.DataFrame(rows);context.to_parquet(out/'market_context.parquet',index=False)
    stats={}
    for h in [20,60]:
        known=context[f'market{h}'].notna()
        stats[str(h)]=dict(known=int(known.sum()),unknown=int((~known).sum()),market_positive=int(context[f'market{h}'].gt(0).sum()),
                          industry_outperforms=int(context[f'excess{h}'].gt(0).sum()))
    result=dict(cases=len(cases),unique_phase_cases=int(selected.process_id.nunique()),market=stats,
                phases_under20=int(p.duration.lt(20).sum()),
                inputs={str(f):sha(f) for f in [root/'processes.parquet',root/'candidate_metrics.parquet',marketfile,EP/'rounds/R00_v02_case_review_plan.md']})
    (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
