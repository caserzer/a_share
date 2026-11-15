"""Independently verify every corrected followup path from raw basket endpoints."""
import pandas as pd
from common import *

def run():
 out=ROOT/'outputs/r156';root=out/'evaluation';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h,p
 assert sha(ROOT/'protocols/r10.json')==sha(root/'protocols/r10.json')
 raw=pd.read_parquet(root/'cache/forecast_v5/daily_industries.parquet');market=pd.read_parquet(root/'cache/forecast_v5/CSI_ALL.parquet').close
 lookup={}
 for key,g in raw.groupby(KEY+['block'],sort=False):
  g=g.sort_values('date');nav=g.nav.to_numpy();bm=g.date.map(market).to_numpy();dates=g.date.to_numpy();breadth=g.breadth21.to_numpy()
  for i,date in enumerate(g.date):lookup[tuple(key[:3])+(date,)]=(i,nav,bm,dates,breadth)
 a=pd.read_parquet(root/'data/r10_alert_followup.parquet');risk=pd.read_parquet(root/'data/r10_risk_followup.parquet');checks=0
 for frame,horizons in [(a,[5,20,60]),(risk,[20,60])]:
  for row in frame.itertuples(index=False):
   i,nav,bm,dates,breadth=lookup[(row.era,row.level,row.industry_code,row.date)]
   for h in horizons:
    end=i+h+1;actual=getattr(row,f'return{h}')
    if end>=len(nav):assert pd.isna(actual);continue
    start=i+1;path=nav[start:end+1];ret=nav[end]/nav[start]-1;benchmark=bm[end]/bm[start]-1
    assert np.isclose(actual,ret,atol=1e-12) and np.isclose(getattr(row,f'excess{h}'),ret-benchmark,atol=1e-12)
    assert pd.Timestamp(getattr(row,f'maturity{h}'))==pd.Timestamp(dates[end])
    assert np.isclose(getattr(row,f'drawdown{h}'),min(path[j]/max(path[:j+1])-1 for j in range(len(path))),atol=1e-12)
    checks+=1
 for name,keys in [('followup_summary',['era','level','strategy','horizon']),('followup_annual',['era','level','strategy','year','horizon']),('continuation',['era','level','strategy','cohort']),('exit_summary_dates',['era','level','horizon','cohort','cost']),('exit_summary_rows',['era','level','horizon','cohort','cost'])]:
  old=pd.read_csv(ROOT/f'outputs/r10/{name}.csv');new=pd.read_csv(root/f'outputs/r10/{name}.csv');expected=old.merge(new,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');saved=pd.read_csv(out/f'{name}_comparison.csv');pd.testing.assert_frame_equal(expected.assign(_merge=expected._merge.astype(str)),saved,check_dtype=False,rtol=1e-12,atol=1e-14)
 assert json.loads((root/'outputs/r10/verification.json').read_text())['status']=='PASS'
 js(out/'verification.json',dict(status='PASS',alert_rows=len(a),risk_rows=len(risk),independent_complete_path_checks=checks,scope='All return, excess, maturity and within-window running-high drawdown values independently recalculated from corrected NAV; every summary comparison reconstructed',verifier_sha256=sha(Path(__file__))))
 print('R156 VERIFIED',checks)
if __name__=='__main__':run()
