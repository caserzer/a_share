"""Adopt only sealed, verified repair outputs into an explicit overlay."""
from common import *
from research_entry_r139 import ENTRY,load
ROUTES={
 'corrected_daily_baskets':('outputs/r129/daily_2026-10-21.parquet','outputs/r129/verification.json'),
 'corrected_monthly_panel':('outputs/r130/monthly_panel.parquet','outputs/r130/verification.json'),
 'three_task_price_models':('outputs/r131/model_parameters.json','outputs/r131/verification.json'),
 'three_task_prediction_evaluation':('outputs/r131/evaluation_summary.json','outputs/r131/evaluation_verification.json'),
 'fixed_rank_evaluation':('outputs/r132/evaluation/outputs/r01/date_metrics.csv','outputs/r132/verification.json'),
 'market_exposure_controls':('outputs/r133/market_controls.parquet','outputs/r133/verification.json'),
 'market_control_return_metrics':('outputs/r135/evaluation/outputs/r55/increments.csv','outputs/r135/evaluation_verification.json'),
 'market_control_classifier_metrics':('outputs/r135/evaluation/outputs/r56/increments.csv','outputs/r135/evaluation_verification.json'),
 'market_control_exit_metrics':('outputs/r136/evaluation/outputs/r57/summary.csv','outputs/r136/verification.json'),
 'synthetic_portfolio_summary':('outputs/r137/evaluation/outputs/r04/summary.csv','outputs/r137/verification.json'),
 'versioned_historical_inference':('outputs/r138/bundles.json','outputs/r138/verification.json'),
 'three_task_model_explanations':('outputs/r138/model_explanations.parquet','outputs/r138/verification.json'),
 'three_task_model_terms':('outputs/r138/model_terms.parquet','outputs/r138/verification.json'),
 'integrated_historical_task_evidence':('outputs/r138/task_evidence.parquet','outputs/r138/verification.json')}
def run():
 out=ROOT/'outputs/r139';before=json.loads((out/'prior_current_sources.json').read_text());sealed=json.loads((out/'prior_progress_manifest.json').read_text());hashes={x['path']:x['sha256'] for x in sealed['files']};routes={}
 for name,(path,proof) in ROUTES.items():
  for p in [path,proof]:assert sha(ROOT/p)==hashes[p],p
  assert json.loads((ROOT/proof).read_text())['status']=='PASS'
  routes[name]=dict(path=path,sha256=sha(ROOT/path),verification=dict(path=proof,sha256=sha(ROOT/proof)),supersedes=before['selected'].get(name),scope='local repaired research output, no production or strict PIT claim')
 current=json.loads((ROOT/'outputs/current_sources.json').read_text());legacy_before={k:v for k,v in current['selected'].items() if k!=ENTRY}
 for k,v in before['selected'].items():assert legacy_before[k]['path']==v['path']
 refreshed={k:dict(before=v,after=legacy_before[k]) for k,v in before['selected'].items() if legacy_before[k]!=v}
 untouched={k:dict(**v,review_status='retained_historical_not_revalidated_by_basket_repair') for k,v in legacy_before.items() if k not in routes and k!=ENTRY}
 release=dict(revision='R139',quality='Historical-proxy',overall_status='active_not_complete',monitor_dates=['2026-09-30','2026-10-21'],routes=routes,unreviewed_legacy_routes=untouched,legacy_registry_refreshes=refreshed,source_snapshot_sha256=sha(out/'prior_progress_manifest.json'),next='Review remaining mechanism branches that depend on corrected basket features/labels; distinguish unchanged provenance from affected numerical claims. No parameter search without new grounds.')
 js(out/'release.json',release);current=json.loads((ROOT/'outputs/current_sources.json').read_text());current['selected'][ENTRY]=dict(path='outputs/r139/release.json',sha256=sha(out/'release.json'));js(ROOT/'outputs/current_sources.json',current);load()
 js(out/'receipt.json',dict(status='PASS',routes=len(routes),legacy_routes_preserved=len(before['selected']),unreviewed_routes=len(untouched),release_sha256=sha(out/'release.json'),code_sha256=sha(__file__),resolver_sha256=sha(ROOT/'src/research_entry_r139.py'),protocol_sha256=sha(ROOT/'protocols/r139.json')))
 print('RESEARCH ENTRY',len(routes),'adopted;',len(untouched),'legacy routes not revalidated',flush=True)
if __name__=='__main__':run()
