"""Validate dictionary provenance and prevent stale missing-source/implementation claims."""
from common import *


def run():
 out=ROOT/'outputs/r23';receipt=json.loads((out/'receipt.json').read_text())
 for p,h in receipt['inputs'].items():assert sha(p)==h
 for p,h in receipt['outputs'].items():assert sha(out/p)==h
 rows=json.loads((out/'current_factor_dictionary.json').read_text());assert len(rows)==16
 assert set(x['module'] for x in rows)==set('ABCDEFGH')
 required=['theory','formula','direction','applicable_industries','economic_date','publication_date','available_at','frequency','source','historical_revisions','aggregation','missing_rule','failure_condition','replication_status','horizon','implemented','conclusion','monitor_scope']
 for row in rows:
  assert all(isinstance(row[k],str) and row[k].strip() for k in required)
  assert row['strict_pit_certified'] is False
  assert row['evidence_sha256']
  for p,h in row['evidence_sha256'].items():assert sha(ROOT/p)==h
 by={r['factor']:r for r in rows}
 assert 'macro_state_x_sensitivity' not in by
 assert by['PMI_M2_prior_sensitivity_interaction']['implemented']=='historical_proxy'
 assert by['fixed_fy_eps_revision']['implemented']=='eps_revision_not_tested'
 assert 'R15' in by['same_broker_fixed_FY_profit_revision']['missing_rule']
 assert by['industry_spread_inventory']['implemented']=='not_implemented_continuous_series'
 assert by['reviewed_company_operating_evidence']['implemented']=='reviewed_case_evidence'
 assert by['fund_etf_allocation']['implemented']=='not_integrated'
 js(out/'verification.json',dict(status='PASS',entries=len(rows),modules=8,source_links=sum(len(r['evidence_sha256']) for r in rows),code_sha256=sha(__file__),limitation='schema, lineage and current-status validation; does not prove factor validity'))
 print('R23 dictionary provenance and status verified')

if __name__=='__main__':run()
