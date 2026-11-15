"""Rebuild battery coverage and replay fixed original return/gate experiments."""
import shutil
import pandas as pd
from common import *
from train_r02 import F
import battery_pilot_r64,battery_classification_gates_r65

def run():
 out=ROOT/'outputs/r140';sandbox=out/'evaluation';paths={'data/monthly_panel.parquet':ROOT/'outputs/r130/monthly_panel.parquet','data/r54_market_controls.parquet':ROOT/'outputs/r133/market_controls.parquet','data/r30_size_control.parquet':ROOT/'data/r30_size_control.parquet','outputs/r60/frozen_monthly_series.json':ROOT/'outputs/r60/frozen_monthly_series.json'}
 for n in ['r64','r65']:paths[f'protocols/{n}.json']=ROOT/f'protocols/{n}.json'
 for n in ['train_r02','battery_pilot_r64']:paths[f'src/{n}.py']=ROOT/f'src/{n}.py'
 for dest,source in paths.items():
  p=sandbox/dest;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,p)
 (sandbox/'outputs/r61').mkdir(exist_ok=True);features=json.loads((sandbox/'outputs/r60/frozen_monthly_series.json').read_text());panel=pd.read_parquet(sandbox/'data/monthly_panel.parquet');p=panel[panel.era.eq('SW2021')&panel.industry_code.isin(['801737.SI','857371.SI'])].copy();p['log_members']=np.log(p.members);p=p.merge(pd.read_parquet(sandbox/'data/r30_size_control.parquet',columns=KEY+['date','size_control']),on=KEY+['date'],how='left',validate='one_to_one');observations=[]
 for _,r in p.iterrows():
  date=r['date'];eligible=[x for x in features if x['growth_available_at'] and pd.Timestamp(x['growth_available_at'])<=date and 0<=date.to_period('M').ordinal-pd.Period(x['month'],'M').ordinal<=2];selected=max(eligible,key=lambda x:x['month']) if eligible else None
  observations.append(dict(**{k:r[k].isoformat() if k=='date' else r[k] for k in KEY+['date']},economic_month=selected['month'] if selected else None,log_yoy=selected['log_yoy'] if selected else None,growth_available_at=selected['growth_available_at'] if selected else None,price_complete=bool(r.price_ready and r[F].notna().all()),size_complete=bool(pd.notna(r.size_control))))
 js(sandbox/'outputs/r61/signal_coverage.json',observations)
 oldpanel=battery_pilot_r64.panel();oldpanel.to_parquet(out/'cohort_old.parquet',index=False);battery_pilot_r64.ROOT=sandbox;battery_pilot_r64.panel().to_parquet(out/'cohort_new.parquet',index=False);battery_pilot_r64.run();battery_classification_gates_r65.ROOT=sandbox;battery_classification_gates_r65.run()
 differences=[]
 for family,names in [('r64',['fold_ledger','model_parameters','predictions','metrics']),('r65',['fold_ledger','eligible_labels'])]:
  for name in names:
   old=json.loads((ROOT/f'outputs/{family}/{name}.json').read_text());new=json.loads((sandbox/f'outputs/{family}/{name}.json').read_text());differences.append(dict(family=family,artifact=name,old_rows=len(old),new_rows=len(new),exactly_equal=old==new))
 js(out/'comparison.json',dict(artifacts=differences,old_coverage_rows=len(json.loads((ROOT/'outputs/r61/signal_coverage.json').read_text())),new_coverage_rows=len(observations),old_cohort_rows=len(oldpanel),new_cohort_rows=len(battery_pilot_r64.panel()),reads={str(p):sha(p) for p in list(paths.values())+[Path(__file__),ROOT/'src/battery_classification_gates_r65.py',ROOT/'protocols/r140.json']},boundary='Fixed original rules, old results retained'))
 print(differences,flush=True)
if __name__=='__main__':run()
