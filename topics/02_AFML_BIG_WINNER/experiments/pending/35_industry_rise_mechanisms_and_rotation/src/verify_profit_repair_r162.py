"""Independently solve every repaired weighted Ridge model and verify reused coverage."""
import pandas as pd
from common import *
from train_r02 import F

def run():
 out=ROOT/'outputs/r162';root=out/'evaluation';receipt=json.loads((out/'receipt.json').read_text())
 for p,h in receipt['reads'].items():assert sha(p)==h,p
 for rel in ['data/r25_revision_coverage.parquet','data/r25_company_pair_audit.parquet','data/r15_revision_coverage.parquet','protocols/r25.json']:assert sha(ROOT/rel)==sha(root/rel)
 original=pd.read_parquet(ROOT/'data/monthly_panel.parquet');panel=pd.read_parquet(root/'data/monthly_panel.parquet');assert set(original.date)==set(panel.date);panel['log_members']=np.log(panel.members);cov=pd.read_parquet(root/'data/r25_revision_coverage.parquet');merged=cov.merge(panel,on=KEY+['date'],suffixes=('_coverage',''),validate='many_to_one');base=merged[merged.price_ready].dropna(subset=F+['covered_member_median']);models=json.loads((root/'outputs/r25/model_parameters.json').read_text());maxerror=0.
 for m in models:
  g=base[base.era.eq(m['era'])&base.level.eq(m['level'])&base.fy_offset.eq(m['fy_offset'])];g=g[g.eligible] if m['population']=='strict' else g[g.known.ge(5)&~g.eligible];g=g[g.groupby('date').date.transform('size')>=2].copy();g['expectation']=g.covered_member_median;ranks=g.groupby('date')[F+['expectation']].rank(method='average');counts=g.groupby('date')[F+['expectation']].transform('count');ranks=(ranks-.5)/counts-.5;cut=pd.Timestamp(m['year'],1,1);h=m['horizon'];tr=g[g.date.lt(cut)&g[f'maturity{h}'].lt(cut)&g[f'excess{h}'].notna()];rr=ranks.loc[tr.index,m['columns']].to_numpy();mu=rr.mean(axis=0);sd=rr.std(axis=0);sd[sd==0]=1;assert np.allclose(mu,m['scaler_mean']) and np.allclose(sd,m['scaler_scale']);x=(rr-mu)/sd;y=tr[f'excess{h}'].to_numpy();w=len(tr)/(tr.date.nunique()*tr.groupby('date').date.transform('size').to_numpy());xm=np.average(x,axis=0,weights=w);ym=np.average(y,weights=w);xx=x-xm;coef=np.linalg.solve(xx.T@(xx*w[:,None])+10*np.eye(x.shape[1]),xx.T@((y-ym)*w));intercept=ym-xm@coef;err=max(float(np.max(np.abs(coef-m['coef']))),abs(intercept-m['intercept']));maxerror=max(maxerror,err);assert err<1e-10
 p=pd.read_parquet(out/'prediction_pairs.parquet');a=pd.read_parquet(ROOT/'outputs/r25/predictions.parquet');b=pd.read_parquet(root/'outputs/r25/predictions.parquet');keys=KEY+['date','population','fy_offset','horizon','method','year'];expected=a.merge(b,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');pd.testing.assert_frame_equal(expected,p)
 assert json.loads((root/'outputs/r25/verification.json').read_text())['status']=='PASS';folds=pd.read_csv(root/'outputs/r25/fold_ledger.csv');assert not (folds.population.eq('strict')&folds.status.eq('fit')).any()
 js(out/'verification.json',dict(status='PASS',normal_equation_models=len(models),max_parameter_error=maxerror,prediction_rows=len(b),strict_fits=0,scope='unchanged source coverage and dates; independently reconstructed weighted Ridge coefficients/scalers/intercepts; exact prediction comparisons and original full row verifier',verifier_sha256=sha(Path(__file__))))
 print('R162 VERIFIED',len(models),len(b),maxerror)
if __name__=='__main__':run()
