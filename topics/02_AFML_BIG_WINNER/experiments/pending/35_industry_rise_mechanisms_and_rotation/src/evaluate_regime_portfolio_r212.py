from common import *
import pandas as pd
out=ROOT/'outputs/r212';s=pd.read_csv(out/'summary.csv');rows=[];keys=['era','level','cohort','horizon','cost']
for key,g in s.groupby(keys):
 for method in ['state','interaction']:
  for control in ['base','momentum','equal']:
   a=g[g.method.eq(method)].iloc[0];b=g[g.method.eq(control)].iloc[0];whole=bool(a.whole_path_valid and b.whole_path_valid);ident=dict(zip(keys,key));r=dict(ident,method=method,control=control,both_whole=whole,scheduled=int(a.scheduled))
   for metric in ['total_return','cagr','drawdown','vol','beta','mean_turnover']:
    r['delta_'+metric]=a[metric]-b[metric] if whole else np.nan
   rows.append(r)
pd.DataFrame(rows).to_csv(out/'paired_risk.csv',index=False)
q=pd.DataFrame(rows);v=q.query("horizon==20 and cost=='net50' and control=='base' and both_whole");print(v.groupby('method')[['delta_cagr','delta_drawdown','delta_mean_turnover']].agg(['count','median',lambda x:sum(x>0)]).to_string());print('strategies',s[keys[:-1]+['method']].drop_duplicates().shape[0],'whole',s.drop_duplicates(keys[:-1]+['method']).whole_path_valid.sum())
js(out/'evaluation_receipt.json',dict(status='PASS',paired_risk_rows=len(q),whole_pairs=int(q.both_whole.sum()),adoption=False,inputs={'summary.csv':sha(out/'summary.csv')},output_sha256=sha(out/'paired_risk.csv'),code_sha256=sha(__file__)))
