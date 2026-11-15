from common import *
import pandas as pd

def run():
 out=ROOT/'outputs/r305';out.mkdir(exist_ok=True);k=KEY+['date'];j=pd.read_parquet(ROOT/'outputs/r304/paired_dates.parquet');j=j[j.eligibility.eq('onset__reversal')&j.onset_label.eq('1')&j.reversal_label.eq('1')];assert len(j)==51
 origin=pd.read_parquet(ROOT/'outputs/r287/origins.parquet');v=j[k].merge(origin,on=k,validate='one_to_one');assert len(v)==51 and v.complete_path.all()
 raw=pd.read_parquet(ROOT/'outputs/r129/daily_2026-10-21.parquet').set_index(k);market=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close;cal=pd.DatetimeIndex(market.index);rows=[];paths=[]
 for case,x in enumerate(v.sort_values(k).to_dict('records')):
  start=cal.get_loc(x['date']);assert start==x['day_i'];dates=cal[start+1:start+22];idx=pd.MultiIndex.from_tuples([tuple(x[c] for c in KEY)+(d,) for d in dates],names=k);q=raw.reindex(idx);assert len(q)==21 and q.nav.notna().all() and q.block.eq(x['block']).all();assert dates[0]==x['entry_date'] and dates[-1]==x['maturity20']
  stock=q.nav.to_numpy()/q.nav.iloc[0];bench=market.reindex(dates).to_numpy()/market.loc[dates[0]];relative=stock/bench-1;terminal=stock[-1]-1;excess=stock[-1]-bench[-1];trough=relative[1:].min();assert abs(terminal-x['return20'])<1e-10 and abs(excess-x['excess20'])<1e-10 and abs(trough-x['rel_trough20'])<1e-10;assert terminal>=.05 and excess>=.03 and trough<=-.08
  first=int(np.flatnonzero(relative<=-.08)[0]);low=int(np.argmin(relative));assert 0<first<=low<20
  rows.append(dict(case_id=case,**{c:x[c] for c in k},block=x['block'],entry_date=dates[0],terminal_date=dates[-1],first_breach_step=first,trough_step=low,trough_date=dates[low],relative_trough=trough,terminal_return=terminal,terminal_excess=excess,terminal_relative_wealth=relative[-1],entry_to_trough_absolute=stock[low]-1,terminal_from_trough_relative=(1+relative[-1])/(1+trough)-1))
  for step,d in enumerate(dates):paths.append(dict(case_id=case,step=step,date=d,industry_nav=float(q.nav.iloc[step]),market_close=float(market.loc[d]),industry_wealth=float(stock[step]),market_wealth=float(bench[step]),relative_wealth_return=float(relative[step])))
 cases=pd.DataFrame(rows);points=pd.DataFrame(paths);cases.to_parquet(out/'cases.parquet',index=False);points.to_parquet(out/'path_points.parquet',index=False)
 # Overlapping entry-to-terminal intervals per exact industry, descriptive clusters only.
 clusters=[]
 for key,g in cases.groupby(KEY):
  end=None;n=0
  for x in g.sort_values('entry_date').itertuples():
   if end is None or x.entry_date>end:n+=1
   end=max(end,x.terminal_date) if end is not None else x.terminal_date;clusters.append(dict(case_id=x.case_id,industry_cluster=n))
 pd.DataFrame(clusters).to_csv(out/'overlap_clusters.csv',index=False)
 summary=dict(status='PASS',cases=len(cases),points=len(points),industries=len(cases[KEY].drop_duplicates()),overlap_clusters=sum(g.industry_cluster.nunique() for _,g in cases.merge(pd.DataFrame(clusters),on='case_id').groupby(KEY)),first_breach_step_min=int(cases.first_breach_step.min()),first_breach_step_max=int(cases.first_breach_step.max()),trough_step_min=int(cases.trough_step.min()),trough_step_max=int(cases.trough_step.max()),all_labels_reproduced=True,new_models=0,adoption=False)
 js(out/'summary.json',summary);protocol=json.loads((ROOT/'protocols/r305.json').read_text());inputs=protocol['inputs']+['protocols/r305.json',str(Path(__file__).relative_to(ROOT))];js(out/'receipt.json',dict(inputs={p:sha(ROOT/p) for p in inputs},benchmark_path=str(CACHE/'forecast_v5/CSI_ALL.parquet'),benchmark_sha256=sha(CACHE/'forecast_v5/CSI_ALL.parquet'),outputs={p.name:sha(p) for p in out.iterdir() if p.name!='receipt.json'}));print(summary)
if __name__=='__main__':run()
