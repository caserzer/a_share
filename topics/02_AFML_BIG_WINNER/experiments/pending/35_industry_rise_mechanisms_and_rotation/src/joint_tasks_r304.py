from common import *
import pandas as pd
K=KEY+['date'];G=['era','level','year'];F=['past_excess20','past_excess60','mom60','return20','excess20','rel_trough20']
def run():
 out=ROOT/'outputs/r304';out.mkdir(exist_ok=True);inputs=['outputs/r253/scores.parquet','outputs/r286/scores.parquet','outputs/r253/alerts.parquet','outputs/r287/alerts.parquet','src/train_r02.py','protocols/r304.json',str(Path(__file__).relative_to(ROOT))];parts=[]
 for task,path in zip(['onset','reversal'],inputs[:2]):
  d=pd.read_parquet(ROOT/path,columns=K+['year','variant','eligible','y']+F);assert not d.duplicated(K+['variant']).any()
  base=d[d.variant.eq('base')].drop(columns='variant');assert len(d)==3*len(base)
  for variant,g in d.groupby('variant'):
   c=g.drop(columns='variant').sort_values(K).reset_index(drop=True);pd.testing.assert_frame_equal(c,base.sort_values(K).reset_index(drop=True))
  if task=='onset':e=base.past_excess20.le(0);y=(base.return20.ge(.05)&base.excess20.ge(.03)).astype(float).where(base.excess20.notna())
  else:e=base.past_excess60.gt(0)&base.mom60.gt(0);y=base.rel_trough20.le(-.08).astype(float).where(base.excess20.notna()&base.rel_trough20.notna())
  assert base.eligible.eq(e).all();assert ((base.y==y)|(base.y.isna()&y.isna())).all();parts.append(base)
 joined=parts[0].merge(parts[1],on=K,how='outer',suffixes=('_onset','_reversal'),indicator='coverage',validate='one_to_one');joined['year']=joined.date.dt.year;common=joined.coverage.eq('both')
 for c in F:
  a=joined.loc[common,c+'_onset'];b=joined.loc[common,c+'_reversal'];assert ((a==b)|(a.isna()&b.isna())).all()
 joined['eligibility']='missing_model';joined.loc[common,'eligibility']=joined.loc[common,'eligible_onset'].map({True:'onset',False:'no_onset'})+'__'+joined.loc[common,'eligible_reversal'].map({True:'reversal',False:'no_reversal'})
 joined['onset_label']=joined.y_onset.map({0.:'0',1.:'1'}).fillna('unknown');joined['reversal_label']=joined.y_reversal.map({0.:'0',1.:'1'}).fillna('unknown')
 joined.to_parquet(out/'paired_dates.parquet',index=False);joined.groupby(G+['coverage','eligibility'],observed=True).size().rename('rows').reset_index().to_csv(out/'coverage.csv',index=False)
 dual=joined[joined.eligibility.eq('onset__reversal')];dual.groupby(G+['onset_label','reversal_label']).size().rename('rows').reset_index().to_csv(out/'dual_labels.csv',index=False)
 alerts=[]
 for task,path in zip(['onset','reversal'],inputs[2:4]):
  a=pd.read_parquet(ROOT/path,columns=K+['variant','strategy']);assert not a.duplicated().any();alerts.append(a)
 ak=K+['variant','strategy'];paired=alerts[0].merge(alerts[1],on=ak,how='outer',indicator='alert_presence',validate='one_to_one');paired=paired.merge(joined[K+['coverage','eligibility','onset_label','reversal_label']],on=K,how='left',validate='many_to_one');assert paired.coverage.notna().all();paired['year']=paired.date.dt.year
 paired.to_parquet(out/'paired_alerts.parquet',index=False);paired.groupby(G+['variant','strategy','coverage','alert_presence'],observed=True).size().rename('alerts').reset_index().to_csv(out/'alert_counts.csv',index=False)
 simultaneous=paired[paired.alert_presence.eq('both')];assert simultaneous.eligibility.eq('onset__reversal').all();simultaneous.groupby(G+['variant','strategy','onset_label','reversal_label']).size().rename('alerts').reset_index().to_csv(out/'simultaneous_labels.csv',index=False)
 bothpositive=dual[dual.onset_label.eq('1')&dual.reversal_label.eq('1')];bothpositive.sort_values(K).head(20).to_json(out/'both_positive_examples.json',orient='records',date_format='iso',force_ascii=False,indent=2)
 summary=dict(status='PASS',unique_onset_dates=len(parts[0]),unique_reversal_dates=len(parts[1]),common_dates=int(common.sum()),coverage=joined.coverage.value_counts().to_dict(),dual_eligible_dates=len(dual),dual_both_labels_known=int((dual.onset_label.ne('unknown')&dual.reversal_label.ne('unknown')).sum()),dual_both_positive=len(bothpositive),onset_alerts=len(alerts[0]),reversal_alerts=len(alerts[1]),simultaneous_alert_rows=len(simultaneous),simultaneous_unique_dates=len(simultaneous.drop_duplicates(K)),no_refit=True,new_joint_probability=False,adoption=False)
 js(out/'summary.json',summary);js(out/'receipt.json',dict(inputs={p:sha(ROOT/p) for p in inputs},outputs={p.name:sha(p) for p in out.iterdir() if p.name!='receipt.json'}));print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':run()
