"""Opening suspension state from complete date partitions, with vendor conflicts unknown."""
import re
import numpy as np,pandas as pd
from common import *

def opening_suspension(timing):
 if pd.isna(timing) or not str(timing).strip():return True
 ranges=str(timing).split(',')
 states=[]
 for item in ranges:
  match=re.fullmatch(r'(\d{2}:\d{2})-(\d{2}:\d{2})',item.strip())
  if not match:return None
  start,end=match.groups();states.append(start<='09:30'<end)
 return any(states)

def main():
 rec=json.loads((OUT/'data_audit/suspension_acquisition.json').read_text());assert rec['complete_partition_query'];assert sha(PRIVATE/'suspensions/daily.parquet')==rec['sha256']
 old=pd.read_parquet(PRIVATE/'vendor_trade_status.parquet');state=pd.DataFrame(1.,index=old.index,columns=old.columns);events=pd.read_parquet(PRIVATE/'suspensions/daily.parquet');events=events.loc[events.suspend_type.eq('S')].copy();events['date']=pd.to_datetime(events.trade_date);events['instrument']=events.ts_code.str[-2:]+events.ts_code.str[:6];events['opening_suspended']=events.suspend_timing.map(opening_suspension)
 for row in events.itertuples():
  if row.date not in state.index or row.instrument not in state.columns:continue
  value=np.nan if row.opening_suspended is None else 0. if row.opening_suspended else 1.
  if value!=1:state.loc[row.date,row.instrument]=value
 # Daily vendor flag 0 versus opening trade permission is a genuine conflict; do not choose on performance.
 conflict=old.notna()&state.notna()&(old!=state);state=state.mask(conflict)
 conflict_rows=conflict.stack();conflict_rows=conflict_rows.loc[conflict_rows].reset_index();conflict_rows.columns=['date','instrument','conflict'];conflict_rows.to_csv(OUT/'data_audit/trade_status_conflicts_v2.csv',index=False)
 state.to_parquet(PRIVATE/'opening_trade_status_v2.parquet');save_json(OUT/'manifests/execution_status_v2.json',dict(sha256=sha(PRIVATE/'opening_trade_status_v2.parquet'),suspension_source_sha256=rec['sha256'],conflicts=int(conflict.to_numpy().sum()),rows=state.size,unknown=int(state.isna().to_numpy().sum()),quality='historical vendor-complete-event-list inference; not first-vintage or orderbook certification'))
 print('opening status rows',state.size,'conflicts',conflict.to_numpy().sum(),'unknown',state.isna().to_numpy().sum())
if __name__=='__main__':main()
