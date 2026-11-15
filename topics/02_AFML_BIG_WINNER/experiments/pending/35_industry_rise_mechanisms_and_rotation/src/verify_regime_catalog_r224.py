from common import *
import pandas as pd
out=ROOT/'outputs/r224';catalog=json.loads((out/'family_catalog.json').read_text());original=json.loads((ROOT/'outputs/r195/experiment_registry.json').read_text());assert {x['family'] for x in catalog['families']}=={x['family'] for x in original['families']} and len(catalog['families'])==16
for row in catalog['families']:
 assert row['adoption'] is False and row['full_evaluation_complete'] is False
 for evidence in row['evidence']:
  path=ROOT/evidence['path'];assert sha(path)==evidence['sha256'];payload=json.loads(path.read_text());assert not str(payload.get('status','')).startswith(('FAIL','ERROR'))
source_round={'core_three_tasks':196,'l1_three_tasks':196,'rank_target':196,'market_style':199,'battery':198,'eps_expectations':197,'size_diffusion':199,'financing':199,'profit_events':205,'leader_catchup':200,'financial_dual_clock':201,'macro_interaction':202,'profit_expectations':197,'fixed_factor_rank':204};cache={};rows=[]
for family,rnd in source_round.items():
 path=ROOT/f'outputs/r{rnd}/predictions.parquet'
 if rnd==202:path=ROOT/'outputs/r202/scores.parquet'
 if rnd not in cache:cache[rnd]=pd.read_parquet(path)
 p=cache[rnd]
 if family=='core_three_tasks':p=p[p.family.eq('core')&p.objective.ne('rank')]
 elif family=='l1_three_tasks':p=p[p.family.eq('l1')&p.objective.ne('rank')]
 elif family=='rank_target':p=p[p.objective.eq('rank')]
 elif rnd==199:p=p[p.family.eq(family)]
 elif family=='eps_expectations':p=p[p.family.str.startswith('eps_')]
 elif family=='profit_expectations':p=p[p.family.eq('profit_expectations')]
 assert len(p)>0
 rows.append(dict(family=family,source=str(path.relative_to(ROOT)),source_sha256=sha(path),rows=len(p),task_horizon_counts=p.groupby(['task','horizon']).size().reset_index(name='rows').to_dict('records') if 'task' in p else None,tasks=sorted(p.task.unique().tolist()) if 'task' in p else ['rolling_score' if rnd==202 else 'return'],horizons=sorted(p.horizon.unique().tolist()) if 'horizon' in p else ['shared_score_for20_and60'],variants=sorted(p.variant.unique().tolist()),date_min=p.date.min(),date_max=p.date.max(),levels=sorted(p.level.unique().tolist()),eras=sorted(p.era.unique().tolist()),known_targets=int(p['y' if 'y' in p else 'target'].notna().sum()) if 'y' in p or 'target' in p else None))
for family in ['capital_accounting','early_financial']:rows.append(dict(family=family,rows=0,tasks=[],horizons=[],reason='Original six-period data fail prior training history; state diagnostics retained'))
js(out/'actual_prediction_coverage.json',rows);assert sum(x['rows'] for x in rows if x['family'] in ['core_three_tasks','l1_three_tasks','rank_target'])==len(cache[196]);js(out/'independent_verification.json',dict(status='PASS',families=len(rows),scope='Exact original family set, live receipt hashes and nonfailure status; actual frozen prediction subpopulations, task/horizon/level/date coverage; R196 partitions disjoint and exhaustive',catalog_sha256=sha(out/'family_catalog.json'),actual_prediction_coverage_sha256=sha(out/'actual_prediction_coverage.json'),script_sha256=sha(__file__)));print([(x['family'],x['rows'],x.get('tasks'),x.get('horizons')) for x in rows])
