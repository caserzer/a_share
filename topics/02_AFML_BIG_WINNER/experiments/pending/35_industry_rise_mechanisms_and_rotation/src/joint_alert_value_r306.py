from common import *
import pandas as pd
K=KEY+['date'];G=['era','level','variant','strategy'];M=['terminal_return','terminal_excess','worst_absolute_shortfall','mean_absolute_shortfall','worst_relative_shortfall','onset_hit','reversal_hit']
def run():
 out=ROOT/'outputs/r306';out.mkdir(exist_ok=True);p=json.loads((ROOT/'protocols/r306.json').read_text());a=pd.read_parquet(ROOT/p['inputs'][0]);a=a[a.coverage.eq('both')&a.eligibility.eq('onset__reversal')&a.alert_presence.isin(['left_only','both'])].copy();a['joint_alert']=a.alert_presence.eq('both');assert not a.duplicated(K+['variant','strategy']).any()
 keys=pd.read_parquet(ROOT/p['inputs'][2]);paths=np.load(ROOT/p['inputs'][3]);s=paths['stock'];b=paths['market'];risk=keys.copy();risk['terminal_return']=s[:,-1]-1;risk['terminal_excess']=s[:,-1]-b[:,-1];loss=np.maximum(1-s[:,1:],0);risk['worst_absolute_shortfall']=loss.max(axis=1);risk['mean_absolute_shortfall']=loss.mean(axis=1);relative=s/b-1;risk['worst_relative_shortfall']=np.maximum(-relative[:,1:].min(axis=1),0);risk['onset_hit']=(risk.terminal_return.ge(.05)&risk.terminal_excess.ge(.03)).astype(float);risk['reversal_hit']=(relative[:,1:].min(axis=1)<=-.08).astype(float)
 a=a.merge(risk,on=K,how='left',validate='many_to_one');origin=pd.read_parquet(ROOT/p['inputs'][1],columns=K+['complete_path']);a=a.merge(origin,on=K,validate='many_to_one');assert a.path_id.notna().eq(a.complete_path).all();assert a.loc[a.complete_path,'onset_hit'].astype(int).astype(str).eq(a.loc[a.complete_path,'onset_label']).all();assert a.loc[a.complete_path,'reversal_hit'].astype(int).astype(str).eq(a.loc[a.complete_path,'reversal_label']).all();a.to_parquet(out/'alert_observations.parquet',index=False)
 rows=[]
 for key,g in a.groupby(G+['date']):
  t=g[g.joint_alert];c=g[~g.joint_alert];paired=bool(len(t) and len(c));complete=bool(g.complete_path.all());row=dict(zip(G+['date'],key),joint=len(t),onset_only=len(c),joint_unknown=int((~t.complete_path).sum()),onset_only_unknown=int((~c.complete_path).sum()),both_groups=paired,complete_date=complete,primary=paired and complete)
  for m in M:
   row[m+'_joint']=t[m].mean() if paired and complete else np.nan;row[m+'_onset_only']=c[m].mean() if paired and complete else np.nan;row[m+'_difference']=row[m+'_joint']-row[m+'_onset_only']
  rows.append(row)
 d=pd.DataFrame(rows);d.to_parquet(out/'date_contrasts.parquet',index=False);summaries=[]
 for key,g in d.groupby(G):
  for period,z in [('all',g)]+[(str(y),x) for y,x in g.groupby(g.date.dt.year)]:
   q=z[z.primary];months=q.date.dt.to_period('M').nunique();years=q.date.dt.year.nunique();row=dict(zip(G,key),period=period,dates=len(z),both_group_dates=int(z.both_groups.sum()),complete_paired_dates=len(q),missing_group_dates=int((~z.both_groups).sum()),unknown_dates=int((~z.complete_date).sum()),months=months,years=years,stability_eligible=bool(months>=24 and years>=3))
   for m in M:row[m+'_difference']=q[m+'_difference'].mean()
   summaries.append(row)
 summary=pd.DataFrame(summaries);summary.to_csv(out/'summary.csv',index=False);full=summary[summary.period.eq('all')];result=dict(status='PASS',alert_rows=len(a),unique_origins=len(a[K].drop_duplicates()),joint_alerts=int(a.joint_alert.sum()),unknown_alert_rows=int((~a.complete_path).sum()),date_comparisons=len(d),complete_paired_comparisons=int(d.primary.sum()),groups=len(full),groups_with_pairs=int(full.complete_paired_dates.gt(0).sum()),stability_eligible_groups=int(full.stability_eligible.sum()),higher_worst_absolute=int(full.worst_absolute_shortfall_difference.gt(0).sum()),higher_worst_relative=int(full.worst_relative_shortfall_difference.gt(0).sum()),higher_reversal_hit=int(full.reversal_hit_difference.gt(0).sum()),lower_terminal_return=int(full.terminal_return_difference.lt(0).sum()),adoption=False,new_models=0)
 js(out/'result.json',result);reads=p['inputs']+['protocols/r306.json',str(Path(__file__).relative_to(ROOT))];js(out/'receipt.json',dict(inputs={x:sha(ROOT/x) for x in reads},outputs={x.name:sha(x) for x in out.iterdir() if x.name!='receipt.json'}));print(json.dumps(result,indent=2));print(full[['era','level','variant','strategy','complete_paired_dates','worst_absolute_shortfall_difference','terminal_return_difference']].to_string(index=False))
if __name__=='__main__':run()
