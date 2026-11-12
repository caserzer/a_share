"""One preregistered persistence diagnostic; does not rewrite L02."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha
from v2_label_probe02 import fit_segments,classify


def retained(z):
    z=np.asarray(z)
    mid=(z[0]+z[-1])/2
    return bool(z[-1]>z[0] and (z>=mid).sum()*2>=len(z) and (z[-2:]>=mid).all())


def main():
    out=EP/'outputs/r00_v2_label_probe02/persistence'
    if out.exists():raise FileExistsError('Immutable diagnostic')
    out.mkdir()
    source=PRIOR/'daily_industries.parquet'
    original=out.parent/'candidates.parquet'
    plan=EP/'protocols/r00_v2/label_probe02/persistence_check_plan.md'
    inputs={str(f):sha(f) for f in [source,original,plan,Path(__file__)]}
    raw=pd.read_parquet(source,columns=['date','era','industry_code','block','nav'])
    raw=raw[raw.nav.notna()&raw.nav.gt(0)&raw.block.notna()].copy()
    raw['week']=raw.date.dt.to_period('W-SUN').astype(str);raw['y']=np.log(raw.nav)
    groups={k:g.groupby('week').y.median().to_numpy() for k,g in raw.groupby(['era','industry_code','block'])}
    r=pd.read_parquet(original)
    r['minimum_persistence']=[retained(groups[(v.era,v.industry_code,v.block)][v.start:v.stop]) for v in r.itertuples()]
    r['diagnostic_status']=np.where(r.partial_weeks.gt(0),'PARTIAL_WEEK_UNKNOWN',np.where(r.minimum_persistence,'RETAINED','NOT_RETAINED'))
    r.to_parquet(out/'candidate_diagnostic.parquet',index=False)
    t=np.arange(80);rng=np.random.default_rng(0);checks=[]
    paths={'flat':np.zeros(80),'warming':np.r_[-.005*np.arange(40),-.195+.003*np.arange(40)],
           'heating':np.r_[.003*np.arange(40),.117+.009*np.arange(40)],
           'pulse':np.where(t==40,.15,0.),'steady_up':.003*t,
           'slowing_decline':np.r_[-.009*np.arange(40),-.351-.002*np.arange(40)]}
    for name,y in paths.items():
        for perturb in (False,True):
            z=y+(rng.normal(0,.001,len(y)) if perturb else 0)
            ss=classify(z,fit_segments(z))
            kept=[s['kind'] for s in ss if s['kind'] in ('WARMING','HEATING') and retained(z[s['start']:s['stop']])]
            ok=('WARMING' in kept if name=='warming' else 'HEATING' in kept if name=='heating' else not kept)
            checks.append(dict(path=name,perturbed=perturb,kept=kept,expectation_met=bool(ok)))
    summary=dict(scope='Persistence diagnostic only; not frozen labels',
                 original_candidates=len(r),status=r.diagnostic_status.value_counts().to_dict(),
                 checks_met=sum(c['expectation_met'] for c in checks),checks_total=len(checks),checks=checks)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'receipt.json').write_text(json.dumps(dict(inputs=inputs,artifacts={f.name:sha(f) for f in out.iterdir() if f.is_file()}),indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
