import pandas as pd
from common import *


def run():
 out=ROOT/'outputs/r26';out.mkdir(exist_ok=True)
 old=pd.read_parquet(ROOT/'data/r14_industry_events.parquet');events=pd.read_parquet(ROOT/'data/r26_industry_events.parquet');context=pd.read_parquet(ROOT/'data/r26_non_event_context.parquet')
 keys=KEY+['signal_date'];lost=old[keys].drop_duplicates().merge(events[keys].drop_duplicates(),on=keys,how='left',indicator=True);lost=lost[lost._merge.eq('left_only')][keys]
 quarantine=set(map(tuple,lost.rename(columns={'signal_date':'date'})[KEY+['date']].to_numpy()))
 context['source_unknown']=context[KEY+['date']].apply(tuple,axis=1).isin(quarantine)
 available=context[~context.is_event&~context.source_unknown&context.quintile.notna()]
 metrics=['pre20','pre60','reaction','post20','post60'];controls=[]
 for key,g in available.groupby(['era','level','date','quintile']):
  rec=dict(zip(['era','level','signal_date','quintile'],key),control_count=len(g))
  for m in metrics:rec['control_'+m]=g[m].mean() if len(g)>=3 and g[m].notna().all() else np.nan
  controls.append(rec)
 result=events.drop(columns=['control_count']+['control_'+m for m in metrics]+['matched_'+m for m in metrics]).merge(pd.DataFrame(controls),on=['era','level','signal_date','quintile'],how='left',validate='many_to_one')
 for m in metrics:result['matched_'+m]=result[m]-result['control_'+m]
 assert len(result)==len(events)
 result.to_parquet(ROOT/'data/r26_unknown_control_sensitivity.parquet',index=False)
 rows=[]
 for key,g in result.groupby(['era','level','direction']):
  for m in metrics+['matched_'+m for m in metrics]:rows.append(dict(zip(['era','level','direction'],key),metric=m,event_rows=len(g),known=int(g[m].notna().sum()),event_mean=g[m].mean(),date_mean=g.groupby('signal_date')[m].mean().mean()))
 summary=pd.DataFrame(rows);summary.to_csv(out/'unknown_control_summary.csv',index=False)
 pair=events.merge(result,on=keys+['fiscal_year'],suffixes=('_fixed','_conservative'),validate='one_to_one')
 changed=~np.isclose(pair.control_count_fixed,pair.control_count_conservative,equal_nan=True)
 pair[changed].to_csv(out/'unknown_control_changes.csv',index=False)
 baseline=old.merge(result,on=keys+['fiscal_year'],suffixes=('_old','_new'),validate='one_to_one')
 differences={m:int((~np.isclose(baseline['matched_'+m+'_old'],baseline['matched_'+m+'_new'],equal_nan=True)).sum()) for m in metrics}
 js(out/'unknown_control_receipt.json',dict(status='PASS_AUXILIARY_SENSITIVITY',quarantined_contexts=len(quarantine),changed_remaining_events=int(changed.sum()),remaining_matched_differences_vs_r14=differences,protocol_sha256=sha(ROOT/'protocols/r26_control_sensitivity.json'),code_sha256=sha(__file__),result_sha256=sha(ROOT/'data/r26_unknown_control_sensitivity.parquet'),limitation='selected cached reports still cannot establish genuine no-news controls; known source-invalid rows excluded only'))
 print(json.dumps(json.loads((out/'unknown_control_receipt.json').read_text()),ensure_ascii=False))

if __name__=='__main__':run()
