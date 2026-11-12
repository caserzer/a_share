"""Revisit pre-existing semantic counterexamples, with no outcome-based replacement."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from audit_local_inputs import EP, PRIOR, CACHE, sha


def main():
    root=EP/'outputs/r00_price_process_v03';out=root/'regression_review';out.mkdir(exist_ok=True)
    p=pd.read_parquet(root/'processes.parquet');a=pd.read_parquet(root/'candidate_assignments.parquet')
    old=pd.read_json(EP/'outputs/r00_process_draft_v02/case_review/selection.json')
    picks=['YEAR_2018','YEAR_2023','YEAR_2024','NEW_HEATING_PHASE','CLASSIFICATION_BOUNDARY','RIGHT_CENSORED']
    cases=[]
    for label in picks:
        r=old[old.stratum.eq(label)].iloc[0]
        match=a[a.era.eq(r.era)&a.industry_code.eq(r.industry_code)&a.block.eq(r.block)&a.position.eq(r.start)]
        assert len(match)==1
        c=p[p.process_id.eq(match.process_id.iloc[0])].iloc[0].to_dict()
        c.update(case=label,old_start=int(r.start),old_end=int(r.end),assignment=match.disposition.iloc[0]);cases.append(c)
    longest=p.sort_values(['duration','process_id'],ascending=[False,True]).iloc[0].to_dict()
    longest.update(case='LONGEST_V03',old_start=None,old_end=None,assignment=None);cases.append(longest)
    d=pd.read_parquet(PRIOR/'daily_industries.parquet')
    groups={k:g.sort_values('date').reset_index(drop=True) for k,g in d[d.nav.notna()].groupby(['era','industry_code','block'])}
    marketfile=CACHE/'forecast_v5/CSI_ALL.parquet';market=pd.read_parquet(marketfile).close.sort_index()
    for page in range(2):
        fig,axs=plt.subplots(2,2,figsize=(15,10))
        for ax,r in zip(axs.flat,cases[page*4:page*4+4]):
            g=groups[(r['era'],r['industry_code'],r['block'])];start=int(r['start']);end=int(r['end']);lo=max(0,start-60)
            v=g.iloc[lo:end+1];x=np.arange(lo,end+1)-start;base=g.nav.iloc[start]
            ax.plot(x,(v.nav/base-1)*100,label='Industry')
            mb=market.reindex([g.date.iloc[start]]).iloc[0];mp=market.reindex(pd.DatetimeIndex(v.date))
            ax.plot(x,(mp/mb-1)*100,label='CSI All',alpha=.65)
            ax.axvline(0,color='black',lw=.8);ax.axvline(60,color='green',linestyle=':',label='Evidence end')
            ax.axvline(end-start,color='red',linestyle='--',label='V03 last valid/observed')
            if r['old_end'] is not None:ax.axvline(r['old_end']-start,color='purple',linestyle='--',label='V02 stage end')
            ax.set_title(f"{r['case']} {r['industry_code']} {pd.Timestamp(r['start_date']).date()}\n{r['kind']} {r['end_reason']}",fontsize=9)
            ax.set_xlabel('Trading days from v03 origin');ax.set_ylabel('Return (%)');ax.legend(fontsize=7)
        for ax in axs.flat[len(cases[page*4:page*4+4]):]:ax.set_visible(False)
        fig.tight_layout();fig.savefig(out/f'page{page+1}.png',dpi=120);plt.close(fig)
    pd.DataFrame(cases).to_json(out/'cases.json',orient='records',force_ascii=False,date_format='iso',indent=2)
    (out/'receipt.json').write_text(json.dumps(dict(cases=len(cases),sources={str(f):sha(f) for f in [root/'processes.parquet',root/'candidate_assignments.parquet',marketfile]}),indent=2)+'\n')
    print(pd.DataFrame(cases)[['case','industry_code','start_date','end_date','duration','assignment']].to_string(index=False))


if __name__=='__main__':main()
