import pandas as pd
from pandas.testing import assert_frame_equal
from common import *
def run():
 out=ROOT/'outputs/r93';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h,p
 for p,h in rec['outputs'].items():assert sha(out/p)==h,p
 t=pd.read_csv(ROOT/'outputs/r22/task_monitor.csv');e=pd.read_parquet(ROOT/'outputs/r74/evidence_matrix.parquet');t['asof']=pd.to_datetime(t['asof']);e['asof']=pd.to_datetime(e['asof']);d=pd.read_parquet(out/'task_evidence.parquet');saved=pd.read_parquet(out/'all_clock_evidence.parquet');assert_frame_equal(saved,e)
 key=KEY+['asof'];tk=key+['task','horizon','method','cohort'];assert not d.duplicated(tk).any();left=d[t.columns].sort_values(tk).reset_index(drop=True);right=t.sort_values(tk).reset_index(drop=True);assert_frame_equal(left.isna(),right.isna());assert_frame_equal(left.astype(object).where(left.notna(),None),right.astype(object).where(right.notna(),None),check_dtype=False)
 pub=e[e.clock.eq('publication_proxy')].set_index(key).sort_index();projected=d[key+['evidence_'+c for c in e if c not in key]].drop_duplicates().rename(columns={'evidence_'+c:c for c in e if c not in key}).set_index(key).sort_index();assert_frame_equal(projected,pub,check_dtype=False)
 catalogue=pd.read_csv(ROOT/'outputs/universe_current.csv');catalogue=catalogue[catalogue.era.eq('SW2021')];ids=set(map(tuple,catalogue[KEY].to_numpy()));assert len(ids)==511
 for date,g in d.groupby('asof'):
  assert set(map(tuple,g[KEY].drop_duplicates().to_numpy()))==ids
  for _,q in g.groupby(KEY):assert set(map(tuple,q[['task','horizon','method','cohort']].to_numpy()))=={(task,h,m,m) for task in ['return','onset','reversal'] for h in [20,60] for m in ['F','FD']}
 assert d.evidence_join.eq('both').all() and len(pd.read_parquet(out/'evidence_without_task_key.parquet'))==0
 assert d.integration_scope.eq('historical_publication_proxy_display_no_model_change').all() and d.model_clock_scope.eq('frozen_historical_proxy_not_archive_or_acquisition_replay').all()
 assert d.loc[d.level.eq('L1'),'model_source_round'].eq('R16').all() and d.loc[d.level.ne('L1'),'model_source_round'].eq('R02').all()
 assert d.loc[d.status.ne('formal_historical_output'),'prediction'].isna().all();assert d.loc[d['asof'].eq('2026-10-21'),'prediction'].isna().all()
 forbidden={'actual','actual_profit_cny','realized_profit','return20','excess20','y','maturity20'};assert not forbidden.intersection(d.columns)
 for s in json.loads((out/'coverage.json').read_text()):
  g=d[d['asof'].eq(pd.Timestamp(s['asof']))&d.level.eq(s['level'])];unique=g.drop_duplicates(key);assert s['industries']==g.industry_code.nunique() and s['task_rows']==len(g) and s['matched_rows']==g.evidence_join.eq('both').sum() and s['formal_predictions']==g.prediction.notna().sum();assert s['industries_with_any_formal']==g.loc[g.prediction.notna(),'industry_code'].nunique();assert s['operating_current_industries']==unique.evidence_operating_status.eq('historical_proxy_available').sum();assert s['operating_states']==unique.evidence_operating_status.value_counts(dropna=False).to_dict() and s['task_statuses']==g.status.value_counts().to_dict()
 current=json.loads((ROOT/'outputs/current_sources.json').read_text())['selected']
 for k,n in [('integrated_historical_task_evidence','task_evidence.parquet'),('integrated_historical_clock_evidence','all_clock_evidence.parquet')]:assert current[k]==dict(path='outputs/r93/'+n,sha256=sha(out/n))
 js(out/'verification.json',dict(status='PASS',task_rows=len(d),evidence_rows=len(e),industry_keys=len(ids),scope='all source columns unchanged, full catalogue task grid, exact publication-clock evidence joins, model lineage, absent-current outputs and coverage summaries',verifier_sha256=sha(Path(__file__))));print('R93 VERIFIED',len(d),'task rows;',len(e),'multi-clock evidence rows')
if __name__=='__main__':run()
