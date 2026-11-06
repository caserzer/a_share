"""Prespecified six-test family; market-month moving blocks, never stock iid."""
import numpy as np
import pandas as pd
from context6 import OUT,js,finite_json


def block_summary(values,seed=32,replications=1000,length=3):
    v=np.asarray(values,dtype=float);v=v[np.isfinite(v)];n=len(v)
    if n<6:return dict(months=n,effect=np.nan,ci_low=np.nan,ci_high=np.nan,p_one_sided=np.nan)
    rng=np.random.default_rng(seed);starts=rng.integers(0,n,size=(replications,int(np.ceil(n/length))))
    ix=((starts[:,:,None]+np.arange(length))%n).reshape(replications,-1)[:,:n]
    bootstrap=v[ix].mean(axis=1);observed=v.mean();null=bootstrap-observed
    return dict(months=n,effect=float(observed),ci_low=float(np.quantile(bootstrap,.025)),ci_high=float(np.quantile(bootstrap,.975)),
        p_one_sided=float((1+(null>=observed).sum())/(replications+1)))


def bh(p):
    p=np.asarray(p,float);order=np.argsort(p);ordered=p[order]
    q=np.minimum.accumulate((ordered*len(p)/np.arange(1,len(p)+1))[::-1])[::-1]
    result=np.empty(len(p));result[order]=np.minimum(q,1);return result


def run():
    rows=[]
    loss=pd.read_csv(OUT/'monthly_brier_improvement.csv');common=loss[loss.cohort.eq('common')]
    for name in ['H1','H2','H3']:
        r=block_summary(common[name]);r.update(test=name+'_brier_increment',hypothesis=name,unit='Brier reduction',primary=True);rows.append(r)
    mech=pd.read_csv(OUT/'monthly_mechanism_effects.csv')
    for name in ['H1_positive_lead','H1_forward_minus_reverse','H1_forward_minus_other']:
        r=block_summary(mech[name]);r.update(test=name,hypothesis='H1',unit='risk-scaled slope',primary=True);rows.append(r)
    d=pd.DataFrame(rows);assert len(d)==6 and d.p_one_sided.notna().all();d['q_bh']=bh(d.p_one_sided)
    d['positive_supported']=d.effect.gt(0)&d.q_bh.lt(.05)&d.ci_low.gt(0)
    d.to_csv(OUT/'primary_tests.csv',index=False)
    extras=[]
    for cohort,g in loss.groupby('cohort'):
        for name in ['H1','H2','H3','joint','other_leader','reverse']:
            if name not in g or g[name].notna().sum()<6:continue
            r=block_summary(g[name]);r.update(cohort=cohort,model=name,primary=False);extras.append(r)
    pd.DataFrame(extras).to_csv(OUT/'diagnostic_intervals.csv',index=False)
    h1=d[d.hypothesis.eq('H1')]
    js(OUT/'hypothesis_verdicts.json',dict(
        H1=dict(status='OBSERVABLE_IMPLICATIONS_SUPPORTED' if h1.positive_supported.all() else 'NOT_SUPPORTED',
            caveat='directional leading effect and same-sample predictive increment must both hold; association is not causality'),
        H2=dict(status='INCREMENTAL_FEATURE_CANDIDATE' if bool(d.set_index('test').loc['H2_brier_increment','positive_supported']) else 'NO_ROBUST_INCREMENT',
            caveat='an unconstrained tree can exploit an opposite sign; improved prediction alone does not verify diffusion'),
        H3=dict(status='INCREMENTAL_FEATURE_CANDIDATE' if bool(d.set_index('test').loc['H3_brier_increment','positive_supported']) else 'NO_ROBUST_INCREMENT',
            caveat='one market beta does not remove every systematic risk factor'),
        H4=dict(status='BLOCKED_DATA',caveat='insufficient audited announcement-vintage industry fundamentals'),
        strict_PIT='BLOCKED_DATA',independent_confirmation=False))
    print(d[['test','effect','ci_low','ci_high','q_bh','positive_supported']].to_string(index=False),flush=True)


if __name__=='__main__':run()
