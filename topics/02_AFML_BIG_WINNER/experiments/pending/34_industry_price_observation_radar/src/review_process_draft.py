"""Deterministic case selection and direct raw-path arithmetic checks."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from audit_local_inputs import EP, PRIOR, CACHE, sha


def main():
    out=EP/'outputs/r00_process_draft_v01'
    a=pd.read_parquet(out/'anchors.parquet')
    p=pd.read_parquet(out/'processes.parquet')
    d=pd.read_parquet(PRIOR/'daily_industries.parquet')
    groups={k:g.set_index('day_i').sort_index() for k,g in d.groupby(['era','industry_code'])}
    chosen=[]
    for kind,status in [('WARMING','VALID_CANDIDATE'),('HEATING','VALID_CANDIDATE'),
                        ('WARMING','REBOUND_OR_INTERRUPTED'),('HEATING','REBOUND_OR_INTERRUPTED'),
                        ('ORDINARY_CONTINUATION','ORDINARY_CONTINUATION')]:
        candidates=a[a.kind.eq(kind)&a.status.eq(status)]
        chosen.append(candidates.sample(1,random_state=3401).iloc[0])
    longest=p.sort_values(['duration','process_id'],ascending=[False,True]).iloc[0]
    chosen.append(a[a.process_id.eq(longest.process_id)].sort_values('day_i').iloc[0])
    selected=pd.DataFrame(chosen)
    selected.to_json(out/'case_selection.json',orient='records',force_ascii=False,date_format='iso',indent=2)
    checks=0
    for _,s in a.groupby(['kind','status']):
        for r in s.sample(min(40,len(s)),random_state=3401).itertuples():
            g=groups[(r.era,r.industry_code)].reindex(range(r.day_i-60,r.day_i+61))
            vals=g.nav.to_numpy(); base=vals[60]
            assert np.isfinite(vals).all() and g.block.nunique()==1
            assert vals[60]==min(vals[55:66]) and list(vals[55:66]).index(min(vals[55:66]))==5
            above=sum(v>=base*1.02 for v in vals[61:])
            peak=vals[60]; worst=0.
            for v in vals[60:]:
                peak=max(peak,v); worst=min(worst,v/peak-1)
            assert above==r.retained_days and np.isclose(worst,r.max_drawdown)
            assert np.isclose(max(vals[61:81])/base-1,r.gain20_max)
            assert np.isclose(vals[-1]/base-1,r.gain60)
            conditions=[max(vals[61:81])/base-1>=.08,vals[-1]/base-1>=.05,above>=40,
                        min(vals[61:])/base-1>=-.05,worst>=-.12]
            assert (all(conditions) and r.kind!='ORDINARY_CONTINUATION')==(r.status=='VALID_CANDIDATE')
            checks+=1
    for _,g in p.groupby(['era','industry_code','block']):
        g=g.sort_values('start_day_i')
        assert (g.start_day_i.iloc[1:].to_numpy()>g.end_day_i.iloc[:-1].to_numpy()+1).all()
    marketfile=CACHE/'forecast_v5/CSI_ALL.parquet'
    market=pd.read_parquet(marketfile).close.sort_index()
    fig,axs=plt.subplots(3,2,figsize=(15,12))
    for panel,(ax,(_,r)) in enumerate(zip(axs.flat,selected.iterrows())):
        stop=int(longest.end_day_i) if panel==5 else int(r.day_i+60)
        g=groups[(r.era,r.industry_code)].reindex(range(int(r.day_i-60),stop+1))
        x=np.arange(-60,stop-int(r.day_i)+1); base=g.loc[r.day_i,'nav']
        ax.plot(x,(g.nav/base-1)*100,label='Industry NAV')
        m=market.reindex(pd.DatetimeIndex(g.date))
        if np.isfinite(m.iloc[60]): ax.plot(x,(m/m.iloc[60]-1)*100,label='CSI All',alpha=.7)
        ax.axvline(0,color='black',lw=.7); ax.axhline(0,color='gray',lw=.7)
        if panel==5:
            for z in a[a.process_id.eq(longest.process_id)].day_i: ax.axvline(z-r.day_i,color='orange',alpha=.3)
        ax.set_title(f'{r.industry_code} {r.date.date()}\n'+('LONG MERGED PROCESS' if panel==5 else r.kind+' / '+r.status),fontsize=9)
        ax.set_xlabel('Trading days from reference origin'); ax.set_ylabel('Return from origin (%)'); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(out/'case_paths.png',dpi=130); plt.close(fig)
    result=dict(status='ARITHMETIC_CHECKS_PASS_SEMANTICS_NOT_APPROVED',sampled_anchors=checks,
                selection='seed3401 one per listed stratum plus longest merged process',
                market_sha256=sha(marketfile),script_sha256=sha(__import__('pathlib').Path(__file__)),
                anchors_sha256=sha(out/'anchors.parquet'),processes_sha256=sha(out/'processes.parquet'))
    (out/'review_checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__': main()
