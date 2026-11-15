"""Separate complete-control selection from the incremental feature comparison."""
import pandas as pd
from common import *
from battery_pilot_r62 import panel as old_panel
from battery_pilot_r64 import panel

def run():
 a,b=old_panel(),panel();keys=KEY+['date'];m=a[keys].merge(b[keys],on=keys,how='outer',indicator=True,validate='one_to_one');assert not m['_merge'].eq('right_only').any()
 lost=m[m['_merge'].eq('left_only')][keys];raw=pd.read_parquet(ROOT/'data/r54_market_controls.parquet');q=lost.merge(raw[keys+['market_beta126','residual_vol126']],on=keys,how='left',validate='one_to_one');assert q[['market_beta126','residual_vol126']].isna().any(axis=1).all()
 p=pd.DataFrame(json.loads((ROOT/'outputs/r64/predictions.json').read_text()))
 for key,g in p.groupby(KEY+['horizon','date']):
  assert set(g.method)=={'FS','FSB','FSM','FSMB'} and g.target.nunique(dropna=False)==1
 js(ROOT/'outputs/r64/cohort_audit.json',dict(status='PASS',old_panel_rows=len(a),complete_control_rows=len(b),removed_rows=q.to_dict('records'),same_prediction_cohort=True,source_sha256=sha(ROOT/'data/r54_market_controls.parquet')))
 print('R64 cohort audit',len(a),len(b),len(q))
if __name__=='__main__':run()
