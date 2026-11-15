import pandas as pd
from common import *
JOIN=KEY+['asof']
def build(tasks,evidence):
 t=tasks.copy();e=evidence.copy();t['asof']=pd.to_datetime(t['asof']);e['asof']=pd.to_datetime(e['asof'])
 assert not t.duplicated(JOIN+['task','horizon','method','cohort']).any()
 assert not e.duplicated(JOIN+['clock']).any()
 pub=e[e.clock.eq('publication_proxy')].copy();pref=pub.rename(columns={c:'evidence_'+c for c in pub if c not in JOIN})
 result=t.merge(pref,on=JOIN,how='left',validate='many_to_one',indicator='evidence_join')
 matched=result.evidence_join.eq('both');assert result.loc[matched,'industry_name'].eq(result.loc[matched,'evidence_industry_name']).all()
 result['integration_scope']='historical_publication_proxy_display_no_model_change';result['model_source_round']=np.where(result.level.eq('L1'),'R16','R02');result['model_clock_scope']='frozen_historical_proxy_not_archive_or_acquisition_replay'
 extra=pub.merge(t[JOIN].drop_duplicates(),on=JOIN,how='left',indicator=True);extra=extra[extra._merge.eq('left_only')].drop(columns='_merge')
 return result,e,extra

def run():
 out=ROOT/'outputs/r93';out.mkdir(exist_ok=True);tp=ROOT/'outputs/r22/task_monitor.csv';ep=ROOT/'outputs/r74/evidence_matrix.parquet';tasks=pd.read_csv(tp);evidence=pd.read_parquet(ep);d,e,extra=build(tasks,evidence);d.to_parquet(out/'task_evidence.parquet',index=False);e.to_parquet(out/'all_clock_evidence.parquet',index=False);extra.to_parquet(out/'evidence_without_task_key.parquet',index=False)
 rows=[]
 for (date,level),g in d.groupby(['asof','level']):
  ev=g.drop_duplicates(JOIN);rows.append(dict(asof=date,level=level,industries=g.industry_code.nunique(),task_rows=len(g),matched_rows=int(g.evidence_join.eq('both').sum()),formal_predictions=int(g.prediction.notna().sum()),industries_with_any_formal=g.loc[g.prediction.notna(),'industry_code'].nunique(),operating_current_industries=int(ev.evidence_operating_status.eq('historical_proxy_available').sum()),operating_states=ev.evidence_operating_status.value_counts(dropna=False).to_dict(),task_statuses=g.status.value_counts().to_dict()))
 js(out/'coverage.json',rows);paths=[tp,ep,ROOT/'outputs/r22/verification.json',ROOT/'outputs/r74/verification.json',ROOT/'protocols/r93.json',Path(__file__)];outputs=[out/x for x in ['task_evidence.parquet','all_clock_evidence.parquet','evidence_without_task_key.parquet','coverage.json']];js(out/'receipt.json',dict(reads={str(p):sha(p) for p in paths},outputs={p.name:sha(p) for p in outputs},task_rows=len(d),evidence_rows=len(e),unmatched_evidence_keys=len(extra),prospective_records=0,ranking_changed=False))
 current=json.loads((ROOT/'outputs/current_sources.json').read_text());current['selected']['integrated_historical_task_evidence']=dict(path='outputs/r93/task_evidence.parquet',sha256=sha(out/'task_evidence.parquet'));current['selected']['integrated_historical_clock_evidence']=dict(path='outputs/r93/all_clock_evidence.parquet',sha256=sha(out/'all_clock_evidence.parquet'));js(ROOT/'outputs/current_sources.json',current);print(json.dumps(rows,ensure_ascii=False,default=str))
if __name__=='__main__':run()
