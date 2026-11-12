import json,sys
from pathlib import Path
import numpy as np,pandas as pd
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha
OUT=EP/'restart/p25';OUT.mkdir(exist_ok=True);assert not (OUT/'receipt.json').exists()
newfile=EP/'restart/p24/daily_industries.parquet';wf=EP/'restart/p24/weekly_path_support.parquet';oldfile=EP/'restart/p21/evaluated.parquet';mf=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5/CSI_ALL.parquet')
seal=json.loads((EP/'restart/p24/receipt.json').read_text());assert sha(newfile)==seal['artifacts'][newfile.name];assert sha(wf)==seal['artifacts'][wf.name]
d=pd.read_parquet(newfile);w=pd.read_parquet(wf);m=pd.read_parquet(mf).close.sort_index();cal=pd.DatetimeIndex(m.index);parts=[]
for _,g in d[d.nav.notna()].groupby(['era','industry_code','block']):
 g=g.sort_values('date').copy();assert np.all(np.diff(g.day_i)==1);bm=g.date.map(m)
 for h in [63,126,252]:
  ret=g.nav.shift(-h-1)/g.nav.shift(-1)-1;mr=bm.shift(-h-1)/bm.shift(-1)-1;end=g.date.shift(-h-1)
  g[f'new_return{h}']=ret;g[f'new_end{h}']=end;g[f'new_win{h}']=(ret.gt(0)&ret.gt(mr)).astype(float).where(end.notna())
 parts.append(g[['era','industry_code','date']+[c for h in [63,126,252] for c in [f'new_return{h}',f'new_end{h}',f'new_win{h}']]])
labels=pd.concat(parts,ignore_index=True);ids=['era','industry_code','date'];w=w.merge(labels,on=ids,how='left',validate='one_to_one')
for h in [63,126,252]:
 assert np.array_equal(w[f'new_win{h}'].notna().to_numpy(),w[f'path{h}'].to_numpy(dtype=bool))
 w[f'new_status{h}']=np.where(~w[f'calendar_mature{h}'],'IMMATURE',np.where(w[f'new_win{h}'].notna(),'KNOWN','MISSING_PATH'))
w.to_parquet(OUT/'weekly_labels.parquet',index=False)
o=pd.read_parquet(oldfile);q=o.merge(w[ids+['history60']+[c for h in [63,126,252] for c in [f'new_win{h}',f'new_end{h}',f'new_status{h}']]],on=ids,how='left',validate='one_to_one',indicator=True);assert q._merge.eq('both').all();q.to_parquet(OUT/'fixed_signal_comparison.parquet',index=False)
rows=[]
for scope,mask in [('all',pd.Series(True,index=q.index)),('top20_edge',q.top20_edge),('raw_gate_edge',q.raw_gate_edge),('nonup_edge',q.nonup_edge)]:
 z=q[mask]
 for year,a in [('ALL',z)]+list(z.groupby(z.date.dt.year)):
  for h in [63,126,252]:
   old=a[f'win{h}'];new=a[f'new_win{h}'];common=old.notna()&new.notna();lost=old.notna()&new.isna();gained=old.isna()&new.notna();wins=new.sum();n=new.notna().sum()
   rows.append(dict(scope=scope,year=str(year),horizon=h,total=len(a),old_known=int(old.notna().sum()),new_known=int(n),common=int(common.sum()),lost=int(lost.sum()),gained=int(gained.sum()),old_all_win=old.mean(),old_common_win=old[common].mean(),new_common_win=new[common].mean(),common_delta=(new[common]-old[common]).mean(),flips_0_to_1=int((old[common].eq(0)&new[common].eq(1)).sum()),flips_1_to_0=int((old[common].eq(1)&new[common].eq(0)).sum()),lost_old_win=old[lost].mean(),new_all_win=new.mean(),full_signal_lower=wins/len(a) if len(a) else np.nan,full_signal_upper=(wins+len(a)-n)/len(a) if len(a) else np.nan,new_history_unavailable=int((~a.history60).sum()),new_immature=int(a[f'new_status{h}'].eq('IMMATURE').sum()),new_missing_path=int(a[f'new_status{h}'].eq('MISSING_PATH').sum())))
s=pd.DataFrame(rows);s.to_csv(OUT/'decomposition.csv',index=False)
prior=pd.read_csv(EP/'restart/p21/summary.csv')
for _,r in prior[prior.unit.eq('edge')].iterrows():
 a=s[s.scope.eq(r.method+'_edge')&s.year.eq('ALL')&s.horizon.eq(r.horizon)].iloc[0];assert a.total==r.total and a.old_known==r.known and np.isclose(a.old_all_win,r.win_rate)
# Independent whole-calendar extraction checks missing rows as well as endpoints.
groups={k:g.set_index('day_i') for k,g in d.groupby(['era','industry_code'])};checks=0
for _,r in w.sample(120,random_state=3325).iterrows():
 g=groups[(r.era,r.industry_code)];i=int(r.day_i)
 for h in [63,126,252]:
  b=g.reindex(range(i,i+h+2));valid=b.nav.notna().all() and b.block.nunique(dropna=False)==1
  assert valid==pd.notna(r[f'new_win{h}'])
  if valid:
   ret=b.nav.iloc[-1]/b.nav.iloc[1]-1;mr=m.iloc[i+h+1]/m.iloc[i+1]-1;assert r[f'new_win{h}']==float(ret>0 and ret>mr);assert r[f'new_end{h}']==cal[i+h+1]
  checks+=1
inputs=[newfile,wf,oldfile,mf,Path(__file__),EP/'restart/P25_label_impact_plan.md']
(OUT/'receipt.json').write_text(json.dumps(dict(status='PASS',inputs={str(f):sha(f) for f in inputs},artifacts={f.name:sha(f) for f in OUT.glob('*') if f.is_file()},path_checks=checks,p21_summary_rows_checked=9,fixed_signal_rows=len(q),no_retraining=True),indent=2)+'\n')
print(s[s.year.eq('ALL')&s.horizon.eq(126)].to_string(index=False));print(s[s.scope.eq('top20_edge')&s.horizon.eq(126)].to_string(index=False))
