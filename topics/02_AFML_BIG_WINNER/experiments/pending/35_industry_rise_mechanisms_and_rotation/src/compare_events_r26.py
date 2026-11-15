import pandas as pd
from common import *


def run():
 out=ROOT/'outputs/r26'
 expected=(ROOT/'src/events_r14.py').read_text().replace('outputs/r14','outputs/r26').replace('data/r14_','data/r26_').replace('protocols/r14.json','protocols/r26.json').replace('data/r11_analyst_forecasts.parquet','data/r24_source_exclusion_overlay.parquet').replace("print('R14'","print('R26'")
 assert expected==(ROOT/'src/events_r26.py').read_text()
 old=pd.read_csv(ROOT/'outputs/r14/event_ledger.csv');new=pd.read_csv(out/'event_ledger.csv')
 keys=['stock_code','broker','fiscal_year','publication_date']
 ledger=old.merge(new,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one')
 assert ledger._merge.eq('both').all()
 changed=ledger.status_old.ne(ledger.status_new)|~np.isclose(ledger.revision_old,ledger.revision_new,equal_nan=True)
 ledger[changed].to_csv(out/'changed_report_events.csv',index=False)
 a=pd.read_parquet(ROOT/'data/r14_industry_events.parquet');b=pd.read_parquet(ROOT/'data/r26_industry_events.parquet')
 q=a.merge(b,on=KEY+['signal_date','fiscal_year'],how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one')
 common=q._merge.eq('both');columns=['revision','event_companies','event_member_fraction','pre20','pre60','reaction','post20','post60','control_count']+['control_'+x for x in ['pre20','pre60','reaction','post20','post60']]
 counts={};affected=~common
 for c in columns:
  change=common&~np.isclose(q[c+'_old'],q[c+'_new'],equal_nan=True)
  counts[c]=int(change.sum());affected|=change
 q[affected].to_csv(out/'changed_industry_events.csv',index=False)
 sk=['era','level','direction','metric'];summary=pd.read_csv(ROOT/'outputs/r14/summary.csv').merge(pd.read_csv(out/'summary.csv'),on=sk,how='outer',suffixes=('_old','_new'),validate='one_to_one')
 summary['event_mean_delta']=summary.event_mean_new-summary.event_mean_old;summary['date_mean_delta']=summary.date_mean_new-summary.date_mean_old
 summary.to_csv(out/'summary_vs_r14.csv',index=False)
 js(out/'impact_receipt.json',dict(status='PASS_FIXED_SOURCE_SENSITIVITY',report_ledger_rows=len(ledger),changed_report_rows=int(changed.sum()),old_industry_events=len(a),new_industry_events=len(b),industry_membership=q._merge.value_counts().to_dict(),common_changes=counts,affected_industry_rows=int(affected.sum()),max_event_mean_delta=float(summary.event_mean_delta.abs().max()),max_date_mean_delta=float(summary.date_mean_delta.abs().max()),baseline_event_sha256=sha(ROOT/'data/r14_industry_events.parquet'),new_event_sha256=sha(ROOT/'data/r26_industry_events.parquet'),code_sha256=sha(__file__),scope='original rule and sample process unchanged; event pool can change control membership, no causal or forward inference'))
 print(json.dumps(json.loads((out/'impact_receipt.json').read_text()),ensure_ascii=False))

if __name__=='__main__':run()
