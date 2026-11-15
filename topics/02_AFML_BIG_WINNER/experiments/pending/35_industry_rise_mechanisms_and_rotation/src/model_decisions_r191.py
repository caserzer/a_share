"""Join distinct evidence axes without promoting descriptive results to adoption."""
from common import *
import pandas as pd
K=['era','level','cohort','horizon']
def run():
 out=ROOT/'outputs/r191';files=['outputs/r131/evaluation/outputs/r02/paired_increments.csv','outputs/r187/paired_folds.csv','outputs/r188/summary.csv','outputs/r189/paired_summary.csv','outputs/r190/paired_metrics.csv']
 ic=pd.read_csv(ROOT/files[0]);ic=ic[ic.task.eq('return')].set_index(K)
 mse=pd.read_csv(ROOT/files[1]);top=pd.read_csv(ROOT/files[2]);top=top[top.year.eq('all')].set_index(K)
 port=pd.read_csv(ROOT/files[3]);annual=pd.read_csv(ROOT/files[4]);rows=[]
 for x in port.to_dict('records'):
  key=tuple(x[k] for k in K);a=ic.loc[key];b=top.loc[key];m=mse;y=annual
  for k,v in zip(K,key):m=m[m[k].eq(v)];y=y[y[k].eq(v)]
  yy=y[y.cost.eq('net20')&y.year.ne('all')];allrow=y[y.cost.eq('net20')&y.year.eq('all')]
  rows.append(dict(x,formal_ic_status=a.result,formal_ic_dates=int(a.months),formal_ic_increment=a.increment,median_centered_mse_improvement=m.centered_improvement.median(),fixed_horizon_top_delta=b.delta,fixed_horizon_paired_dates=int(b.paired_complete),complete_calendar_fragments=len(yy),positive_calendar_fragments=int(yy.delta_return.gt(0).sum()),fullpath_total_return_delta=allrow.delta_return.iloc[0] if len(allrow) else None,fullpath_drawdown_delta=allrow.delta_drawdown.iloc[0] if len(allrow) else None,decision='historical_diagnostic_only' if x['both_whole'] else 'incomplete_path_conditional_only',adoption=False))
 result=pd.DataFrame(rows);assert len(result)==len(ic)==len(top)==24;assert not result.duplicated(K).any()
 result.to_csv(out/'model_decisions.csv',index=False)
 js(out/'decision_receipt.json',dict(status='PASS',scope='24 exact keyed joins; primary/secondary formal decisions preserved; no adoption',inputs={x:sha(ROOT/x) for x in files},code_sha256=sha(__file__),output_sha256=sha(out/'model_decisions.csv')))
 print(result[['era','level','cohort','horizon','formal_ic_status','decision']].to_string(index=False))
if __name__=='__main__':run()
