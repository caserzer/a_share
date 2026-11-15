"""Summarize repaired portfolio differences without changing acceptance rules."""
import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r137';p=pd.read_csv(out/'interval_comparison.csv');s=pd.read_csv(out/'summary_comparison.csv');both=p[p._merge.eq('both')];fields=['gross_return','net20','net50','turnover'];counts={c:dict(changed=int((both[c+'_new']-both[c+'_old']).abs().gt(1e-12).sum()),maximum_absolute_change=float((both[c+'_new']-both[c+'_old']).abs().max())) for c in fields};complete=s[s.whole_path_valid_new&s.whole_path_valid_old];maxima={c:float((complete[c+'_new']-complete[c+'_old']).abs().max()) for c in ['cagr','drawdown','vol','beta','benchmark_cagr','total_return']};changed=both[np.logical_or.reduce([(both[c+'_new']-both[c+'_old']).abs().gt(1e-12) for c in fields])];changed.to_csv(out/'changed_valid_intervals.csv',index=False)
 js(out/'impact.json',dict(interval_metrics=counts,complete_summary_maximum_changes=maxima,complete_strategy_groups=complete[['era','level','method']].drop_duplicates().to_dict('records'),complete_net20=complete[complete.cost.eq('net20')][['era','level','method','cagr_new','drawdown_new','beta_new']].to_dict('records'),source_hashes={str(x):sha(x) for x in [out/'interval_comparison.csv',out/'summary_comparison.csv',Path(__file__)]}))
 print('IMPACT',counts,flush=True)
if __name__=='__main__':run()
