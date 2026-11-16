import numpy as np,pandas as pd
from common import *
from backtest import Inputs

def main():
 x=Inputs();coverage=pd.read_csv(OUT/'data_audit/weekly_coverage.csv');rows=[];missing=[]
 for signal in pd.to_datetime(coverage.signal_date):
  si=x.days.get_indexer([signal])[0];ei=si+1
  if ei>=len(x.days):continue
  member,b,reason,snapshot,industry,buy,sell,known=x.context(si,ei)
  rows.append(dict(signal_date=signal,execution_date=x.days[ei],members=int(member.sum()),buy_eligible=int((member&buy).sum()),sell_eligible=int((member&sell).sum()),unknown_state_members=int((member&~known).sum()),benchmark_status=reason,weight_snapshot=snapshot,known_benchmark_sum=float(b.sum()) if b is not None else None,unknown_industry_weight=float(b[industry=='UNKNOWN'].sum()) if b is not None else None,unknown_execution_benchmark_weight=float(b[~known].sum()) if b is not None else None))
  for j in np.where(member&~known)[0]:missing.append(dict(signal_date=signal,execution_date=x.days[ei],instrument=x.symbols[j],raw_open=x.raw[ei,j],qfq_open=x.o[ei,j],trade_status=x.status[ei,j],up_limit=x.up[ei,j],down_limit=x.down[ei,j],benchmark_weight=b[j] if b is not None else None))
 pd.DataFrame(rows).to_csv(OUT/'data_audit/execution_and_weights_weekly.csv',index=False)
 pd.DataFrame(missing).to_csv(OUT/'data_audit/unknown_execution_rows.csv',index=False)
 raw=pd.read_parquet(PRIVATE/'close.parquet');v=pd.read_parquet(PRIVATE/'volume.parquet');m=pd.read_parquet(PRIVATE/'money.parquet');ratio=m/v/raw
 valid=np.isfinite(ratio)&(v>0)&(raw>0);a=ratio.where(valid).stack()
 unit=dict(vwap_over_raw_close_quantiles=a.quantile([.001,.01,.5,.99,.999]).to_dict(),rows=len(a),far_outside_05_2=int(((a<.5)|(a>2)).sum()),volume_basis='shares inferred by money/volume relative to raw close; turnover used only dimensionless ratios',no_raw_qfq_vwap_mixing=True)
 save_json(OUT/'data_audit/units.json',unit)
 if not (OUT/'manifests/code_before_training.json').exists():save_json(OUT/'manifests/code_before_training.json',dict(files=[dict(path=str(p.relative_to(EP)),sha256=sha(p)) for folder in ['src','configs','tests'] for p in sorted((EP/folder).glob('*')) if p.is_file()],outcomes_read=False))
 print(pd.DataFrame(rows).benchmark_status.value_counts().to_dict());print(unit)
if __name__=='__main__':main()
