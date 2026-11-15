from common import *
import pandas as pd
from regime_monitor_r231 import snapshot
SOURCES={'core_three_tasks':196,'l1_three_tasks':196,'rank_target':196,'market_style':199,'battery':198,'eps_expectations':197,'size_diffusion':199,'financing':199,'profit_events':205,'leader_catchup':200,'financial_dual_clock':201,'macro_interaction':202,'profit_expectations':197,'fixed_factor_rank':204}
def select(p,family,rnd):
 if family=='core_three_tasks':return p[p.family.eq('core')&p.objective.ne('rank')]
 if family=='l1_three_tasks':return p[p.family.eq('l1')&p.objective.ne('rank')]
 if family=='rank_target':return p[p.objective.eq('rank')]
 if rnd==199:return p[p.family.eq(family)]
 if family=='eps_expectations':return p[p.family.str.startswith('eps_')]
 if family=='profit_expectations':return p[p.family.eq('profit_expectations')]
 return p
IDENT=['era','level','family','cohort','method','task','horizon','objective','variant','fy_offset','population','target_type','lag']
def build(as_of,out):
 out=Path(out);asof=pd.Timestamp(as_of);snapshot(str(asof.date()),'signal_close');snapshot(str(asof.date()),'prior_close');out.mkdir(exist_ok=True);catalog=json.loads((ROOT/'outputs/r230/family_catalog.json').read_text());qual=json.loads((ROOT/'outputs/r232/family_qualification.json').read_text());qm={x['family']:x for x in qual['families']};cache={};reads=[];parts=[];entries=[];expected=json.loads((ROOT/'outputs/r224/actual_prediction_coverage.json').read_text());hashes={x['source']:x['source_sha256'] for x in expected if 'source' in x}
 for f in catalog['families']:
  name=f['family'];entry=dict(family=name,name=f['name'],as_of=str(asof.date()),historical_qualification=qm[name],retrospective_conclusion=f['conclusion'],adoption=False,exact_date_rows=0)
  if name not in SOURCES:entry.update(status='no_fitted_model_history_insufficient',reason='original training gates failed; no score fabricated');entries.append(entry);continue
  rnd=SOURCES[name];path=ROOT/f"outputs/r{rnd}/{'scores' if rnd==202 else 'predictions'}.parquet"
  if rnd not in cache:
   assert sha(path)==hashes[str(path.relative_to(ROOT))];cache[rnd]=pd.read_parquet(path,filters=[('date','==',asof)]);reads.append(path)
  p=select(cache[rnd],name,rnd).copy();entry.update(source=str(path.relative_to(ROOT)),source_sha256=sha(path),exact_date_rows=len(p),status='historical_exact_date_records' if len(p) else 'no_exact_date_output',reason=None if len(p) else 'no archived row on requested date; do not infer data failure or fill last score')
  if len(p):
   keys=[k for k in IDENT if k in p];p['model_slice']=p[keys].apply(lambda row:json.dumps(row.to_dict(),sort_keys=True,default=lambda x:x.item() if hasattr(x,'item') else str(x)),axis=1);value='score' if rnd==202 else 'prediction';p['research_score']=p[value];p['ranking_value']=np.sign(p.slope)*p.score if rnd==204 else p[value]
   if rnd==204:p.loc[p.variant.eq('fixed'),'ranking_value']=p.loc[p.variant.eq('fixed'),'score']
   p['display_rank']=p.groupby('model_slice').ranking_value.rank(ascending=False,method='average');p['slice_count']=p.groupby('model_slice').industry_code.transform('size');p['family_registry']=name;p['source_round']=rnd;p['score_interpretation']=['pooled_classifier_output_not_state_certified_probability' if x in ['onset','reversal'] else 'historical_model_or_rule_score_not_expected_executable_return' for x in p.task] if 'task' in p else 'historical_model_or_rule_score_not_expected_executable_return';p['rank_interpretation']=['higher_reversal_risk' if x=='reversal' else 'higher_model_score' for x in p.task] if 'task' in p else 'higher_model_score'
   keep=['family_registry','source_round','model_slice','era','level','industry_code','date','research_score','ranking_value','display_rank','slice_count','score_interpretation','rank_interpretation']+[x for x in ['regime','state_date','event_id','regime_seen_in_fit'] if x in p];parts.append(p[keep]);entry['model_slices']=p.model_slice.nunique()
  entries.append(entry)
 scores=pd.concat(parts,ignore_index=True) if parts else pd.DataFrame(columns=['family_registry','source_round','model_slice','era','level','industry_code','date','research_score','ranking_value','display_rank','slice_count','score_interpretation','rank_interpretation']);assert scores.date.eq(asof).all();scores.to_parquet(out/'historical_score_view.parquet',index=False);js(out/'snapshot.json',dict(schema='ep35.research_archive_view.v1',as_of=str(asof.date()),scope='Retrospective inspection of exact-date archived records; not proof this whole report was available then',market_state=snapshot(str(asof.date()),'signal_close'),event_prior_state=snapshot(str(asof.date()),'prior_close'),families=entries,score_view='historical_score_view.parquet',ranking='display within original model slice only; no new selection or cross-model aggregate',future_outcomes_exposed=False,production_enabled=False,adoption=False))
 reads += [ROOT/'outputs/r230/family_catalog.json',ROOT/'outputs/r232/family_qualification.json',ROOT/'outputs/r224/actual_prediction_coverage.json',ROOT/'protocols/r239.json',Path(__file__),ROOT/'src/regime_monitor_r231.py']
 js(out/'verification.json',dict(status='PASS',families=len(entries),score_rows=len(scores),exact_date_families=sum(x['exact_date_rows']>0 for x in entries),inputs={str(p):sha(p) for p in reads},outputs={x:sha(out/x) for x in ['snapshot.json','historical_score_view.parquet']},adoption=False))
