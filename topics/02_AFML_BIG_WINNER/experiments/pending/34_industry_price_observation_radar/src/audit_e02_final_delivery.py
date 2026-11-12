"""Verify current final research delivery against its concrete artifact requirements."""
import json,hashlib,re
from pathlib import Path
import pandas as pd
from audit_local_inputs import EP,sha

def main():
 out=EP/'handoff/20261112_e02_final'
 assert sha(EP/'GOAL_v2.md')=='ef8b44beef25c7c33f74d6ff1f34def95849ef897f21999bb93957c46629099b'
 assert sha(EP/'GOAL.md')=='651fb80f71354aa3600196bb2fea778008ea1a5f9fcba4603d419b1ece539969'
 roots=['outputs/v2_s12_full_directory_duration','outputs/v2_s12_full_directory_duration/boundary_audit','outputs/v2_s13_duration_enhancements','outputs/v2_revaluation02','outputs/v2_revaluation02/comparison_complete','outputs/evaluation_versions/e02_20261021','outputs/v2_e02_context/strata','outputs/v2_e02_context/stage','outputs/v2_e02_context/uncertainty','outputs/v2_e02_context/misses_complete','outputs/followup_versions/s04_20261021','outputs/v2_s07_explained_primary','handoff/20261112_e02_final/observations']
 seen=set();verified=0;receipt_paths=[]
 for root in roots:
  rpath=EP/root/'receipt.json';r=json.loads(rpath.read_text());receipt_paths.append(rpath)
  for name,digest in r.get('inputs',{}).items():
   path=Path(name)
   if (str(path),digest) not in seen:assert sha(path)==digest,path;seen.add((str(path),digest));verified+=1
  for name,digest in r.get('artifacts',{}).items():
   path=rpath.parent/name
   if (str(path),digest) not in seen:assert sha(path)==digest,path;seen.add((str(path),digest));verified+=1
 events=json.loads((EP/'protocols/v2_revaluation02/frozen_event_manifest.json').read_text());assert len(events)==167
 for name,digest in events.items():assert sha(Path(name))==digest
 main=EP/'outputs/evaluation_versions/e02_20261021/runs/A';s=json.loads((main/'summary.json').read_text())
 assert [s[k] for k in ['new_total','new_effective','new_evaluable','new_unknown','parent_total','parent_covered','parent_timely','parent_late','parent_missed','child_total','child_covered']]==[1459,1262,1434,25,5795,1362,575,787,4433,544,222]
 pc=pd.read_parquet(main/'parent_coverage.parquet');ev=pd.read_parquet(main/'event_quality.parquet');assert pc.process_id.is_unique and ev.event_id.is_unique
 assert pc.covered.sum()==1362 and pc.timing.eq('TIMELY').sum()+pc.timing.eq('LATE').sum()==1362
 assert ev[ev.status.eq('COVERED')].primary_id.is_unique
 d=pd.read_parquet(out/'observations/all_observations.parquet');original=pd.read_parquet(EP/'outputs/v2_s07_explained_primary/all_observations.parquet')
 pd.testing.assert_frame_equal(d.drop(columns='research_question'),original.drop(columns='research_question'))
 assert len(d)==141872 and d.date.nunique()==496 and not d.duplicated(['date','era','industry_code']).any()
 assert set(d.state)=={'NEW','TRACKING','EXIT','NOT_TRIGGERED','DATA_INSUFFICIENT'}
 required=['research_question','unknowns','invalidation_rule','rule_version','source_data_version','trigger_or_update_reason']
 for col in required:assert d[col].notna().all() and d[col].astype(str).str.len().gt(0).all(),col
 active=d[d.state.isin(['NEW','TRACKING'])];assert active.observation_id.notna().all() and active.first_alert.notna().all()
 assert d[d.state.eq('NEW')].groupby('date').size().max()<=5 and active.groupby('date').size().max()<=20
 calendar=pd.read_csv(EP/'outputs/refresh/s02_chain_safe_v2_20261112/calendar_coverage.csv');assert len(calendar)==501 and calendar.state.eq('CLASSIFICATION_TRANSITION_UNKNOWN').sum()==5
 new=ev[ev.kind.eq('NEW')];follow=pd.read_parquet(EP/'outputs/followup_versions/s04_20261021/all_new_paths.parquet');a=follow[follow.arm.eq('A')];assert set(a.event_id)==set(new.event_id);assert a.groupby('horizon').size().eq(1459).all()
 audit=json.loads((EP/'outputs/v2_revaluation02/verification.json').read_text());assert audit['runs']==167 and audit['event_rows_checked']==1031431
 context=json.loads((EP/'outputs/v2_e02_context/cross_checks.json').read_text());assert context['all_strata_reconciled'] and context['all_parent_omission_identities_reconciled']
 links=[]
 for doc in out.glob('*.md'):
  for target in re.findall(r'\]\(([^)]+)\)',doc.read_text()):
   if '://' in target or target.startswith('#'):continue
   path=(doc.parent/target).resolve();assert path.exists(),(doc,target);links.append(str(path))
 evidence=[EP/'GOAL_v2.md',EP/'protocols/v2_revaluation02/plan.md',EP/'protocols/v2_revaluation02/frozen_event_manifest.json',EP/'protocols/confirmation_v1/user_decision_20261112.md',EP/'outputs/v2_revaluation02/verification.json',EP/'outputs/v2_e02_context/cross_checks.json',EP/'outputs/evaluation_versions/e02_20261021/e02_equivalence_checks.json',EP/'outputs/v2_s13_duration_enhancements/verification.json',EP/'outputs/v2_s12_full_directory_duration/boundary_audit/independent_boundary_checks.json',Path(__file__)]+receipt_paths
 result={'result':'PASS_CURRENT_LOCAL_HISTORICAL_RESEARCH_DELIVERY','verified_hash_references':verified,'frozen_event_ledgers':167,'all_goal_hashes_preserved':True,'all_5_states_and_141872_rows_present':True,'all_weekly_new_and_pool_caps_pass':True,'all_required_row_explanations_present':True,'all_original_observation_fields_except_research_question_unchanged':True,'all_followup_event_keys_match':True,'full_population_and_counts_reconciled':True,'context_and_versioned_evaluation_verified':True,'local_document_links_checked':len(links),'limits':['historical simulation, not independent out-of-sample','no future-return or earlier-than-random claim','data through 2026-10-21; complete observation through 2026-10-16','no deployment, transactions or external collection']}
 (out/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 docs=[x for x in out.rglob('*') if x.is_file() and x.name!='manifest.json']
 (out/'manifest.json').write_text(json.dumps({'evidence':{str(x.relative_to(EP)):sha(x) for x in evidence},'delivery':{str(x.relative_to(out)):sha(x) for x in docs}},ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
