from common import *
import pandas as pd

def run():
 out=ROOT/'outputs/r206';out.mkdir(exist_ok=True);root=ROOT/'outputs/r147/evaluation/outputs';state=pd.read_parquet(ROOT/'outputs/r195/market_regimes.parquet').regime;paths=[root/'r73/industry_evidence.json',root/'r74/monthly_observations.json'];counts=[];gates=[]
 for name,path in zip(['period_evidence','current_observations'],paths):
  d=pd.DataFrame(json.loads(path.read_text()));d['snapshot']=pd.to_datetime(d.snapshot);d['regime']=d.snapshot.map(state).fillna('unknown');d.to_parquet(out/f'{name}.parquet',index=False)
  if name=='period_evidence':d['status']=np.where(d.coverage_gate,'coverage_pass','coverage_fail')
  for (level,status),g in d.groupby(['level','status']):
   for st in ['down_low','down_high','up_low','up_high','unknown']:
    z=g[g.regime.eq(st)];counts.append(dict(source=name,level=level,status=status,regime=st,rows=len(z),snapshots=z.snapshot.nunique(),industries=z.industry_code.nunique()))
  assert sum(x['rows'] for x in counts if x['source']==name)==len(d)
  for level,g in d.groupby('level'):
   for year in sorted(g.snapshot.dt.year.unique()):
    n=g[g.snapshot.lt(pd.Timestamp(int(year),1,1))].snapshot.dt.to_period('M').nunique();assert n<18;gates.append(dict(source=name,level=level,year=int(year),all_signal_months=g.snapshot.dt.to_period('M').nunique(),prior_months_upper_bound=n,required=18,status='insufficient_history'))
 pd.DataFrame(counts).to_csv(out/'state_coverage.csv',index=False);js(out/'training_gates.json',gates)
 # Original payload roundtrip must preserve every value; regime is metadata only.
 for name,path in zip(['period_evidence','current_observations'],paths):
  original=pd.DataFrame(json.loads(path.read_text()));original['snapshot']=pd.to_datetime(original.snapshot);saved=pd.read_parquet(out/f'{name}.parquet').drop(columns='regime');pd.testing.assert_frame_equal(original,saved)
 js(out/'verification.json',dict(status='PASS',original_rows_preserved=True,new_models=0,adoption=False,gate_records=len(gates),inputs={str(x):sha(x) for x in paths+[ROOT/'outputs/r195/market_regimes.parquet',ROOT/'protocols/r206.json',Path(__file__)]},outputs={x:sha(out/x) for x in ['period_evidence.parquet','current_observations.parquet','state_coverage.csv','training_gates.json']}))
 print('rows',sum(x['rows'] for x in counts),'gates',len(gates))
if __name__=='__main__':run()
