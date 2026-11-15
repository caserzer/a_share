"""Describe numerical drift and conclusions without choosing a model."""
import pandas as pd
from common import *
G=['era','level','cohort','task','horizon']

def run():
    out=ROOT/'outputs/r106';p=pd.read_parquet(out/'paired_predictions.parquet');rows=[]
    for key,g in p.groupby(G+['year']):
        for variant,a,b in [('duplicate','default_prediction','prediction'),('unique','default_unique_prediction','unique_prediction')]:
            diff=g[b]-g[a]
            rows.append(dict(zip(G+['year'],key),variant=variant,rows=len(g),maximum_absolute_drift=float(diff.abs().max()),mean_absolute_drift=float(diff.abs().mean())))
    pd.DataFrame(rows).to_csv(out/'prediction_drift.csv',index=False)
    old=pd.read_csv(ROOT/'outputs/r105/summary.csv');new=pd.read_csv(out/'summary.csv')
    paired=old.merge(new,on=G,validate='one_to_one',suffixes=('_default','_tight'))
    paired['mean_sign_changed']=np.sign(paired.mean_delta_default)!=np.sign(paired.mean_delta_tight)
    paired['mean_delta_change']=paired.mean_delta_tight-paired.mean_delta_default
    paired.to_csv(out/'precision_comparison.csv',index=False)
    summary=dict(groups=len(paired),mean_sign_changes=int(paired.mean_sign_changed.sum()),default_positive_family=int(paired.family60_low_default.gt(0).sum()),tight_positive_family=int(paired.family60_low_tight.gt(0).sum()),default_negative_family=int(paired.family60_high_default.lt(0).sum()),tight_negative_family=int(paired.family60_high_tight.lt(0).sum()),classification_max_abs_drift=pd.DataFrame(rows).query('task!="return"').groupby('variant').maximum_absolute_drift.max().to_dict(),regression_max_abs_drift=float(pd.DataFrame(rows).query('task=="return"').maximum_absolute_drift.max()),adopted=False)
    js(out/'drift_summary.json',summary)
    reads=[ROOT/'outputs/r105/summary.csv',out/'summary.csv',out/'paired_predictions.parquet',Path(__file__)]
    js(out/'drift_receipt.json',dict(reads={str(p):sha(p) for p in reads},outputs={n:sha(out/n) for n in ['prediction_drift.csv','precision_comparison.csv','drift_summary.json']}));print(summary)

if __name__=='__main__':run()
