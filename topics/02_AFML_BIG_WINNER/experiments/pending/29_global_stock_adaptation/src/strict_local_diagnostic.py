"""Exact unpooled empirical-rate diagnostic, kept separate from the registered weak prior."""
from common import *


def empirical_rate(frame):
    n=frame.individual_months.to_numpy(float);e=frame.individual_events.to_numpy(float)
    assert ((e>=0)&(e<=n)).all() and np.isfinite(n).all()
    p=np.divide(e,n,out=frame.G.to_numpy(float).copy(),where=n>0)
    return np.clip(p,C['probability_clip'],1-C['probability_clip'])


def main():
    registration=json.loads((MANIFEST/'strict_local_diagnostic_registration.json').read_text())
    assert digest(Path(__file__))==registration['code_sha256']
    rows=[];contrasts=[]
    cohort=json.loads((EP/'configs/target_cohort.yaml').read_text());stocks=[x['instrument'] for x in cohort['companies']]
    for world,prefix in [('D0','real_M_R'),('synthetic_positive','synthetic_positive'),('synthetic_zero','synthetic_zero'),('identity','identity')]:
        full=pd.read_parquet(CACHE/f'{prefix}_all.parquet')
        if world.startswith('synthetic'):
            start=sorted(full.date.unique())[C['controls']['warmup_months']]
            f=full[full.date>=start].copy()
        else:f=full[full.date>=C['prediction_start']].copy()
        f['L_MLE']=empirical_rate(f);f[['date','instrument','L_MLE','individual_months','individual_events']].to_parquet(CACHE/f'{prefix}_strict_local.parquet',index=False)
        populations=[(world,f)]+([('cohort40',f[f.instrument.isin(stocks)])] if world=='D0' else [])
        for population,g in populations:
            monthly=[]
            for date,z in g[g.actual.notna()].groupby('date'):
                y=labels(z.actual)
                for name in ['G','GP','GI','GPI','L','GPI_strong','L_unshrunk','L_MLE']:
                    r=dict(population=population,date=date,model=name,rows=len(z),brier=float(np.mean((z[name]-y)**2)),
                        extreme_probability_fraction=float(((z[name]<.01)|(z[name]>.99)).mean()))
                    if 'true_probability' in z:r['oracle_MSE']=float(np.mean((z[name]-z.true_probability)**2))
                    monthly.append(r);rows.append(r)
            m=pd.DataFrame(monthly).pivot(index='date',columns='model',values='brier')
            for a,b in [('GPI','L_MLE'),('L','L_MLE'),('L_unshrunk','L_MLE'),('L_MLE','G')]:
                for block in [6,12]:contrasts.append(dict(population=population,candidate=a,baseline=b,**ci(m[a]-m[b],block)))
    pd.DataFrame(rows).to_csv(OUT/'strict_local_monthly.csv',index=False)
    pd.DataFrame(contrasts).to_csv(OUT/'strict_local_intervals.csv',index=False)


if __name__=='__main__':main()
