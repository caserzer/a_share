"""Inspect every legacy-only route and distinguish historical records from actual work."""
import pandas as pd
from common import *
from research_entry_r139 import load

def run():
 out=ROOT/'outputs/r163';out.mkdir(parents=True,exist_ok=True);entry=load();protocol=json.loads((ROOT/'protocols/r163.json').read_text());old=entry['unreviewed_legacy_routes'];assert {x['key'] for x in protocol['routes']}==set(old);rows=[]
 for item in protocol['routes']:
  source=ROOT/old[item['key']]['path'];evidence=ROOT/item['evidence'];assert source.is_file() and evidence.is_file();kind=source.suffix;data=json.loads(source.read_text()) if kind=='.json' else pd.read_parquet(source) if kind=='.parquet' else pd.read_csv(source)
  rows.append(dict(**item,source=old[item['key']]['path'],source_sha256=sha(source),source_bytes=source.stat().st_size,records=len(data),content_type=type(data).__name__,evidence_sha256=sha(evidence),predictive_adoption=False))
 raw=json.loads((ROOT/'outputs/r16/raw_parameters.json').read_text());models=[m for m in raw if m['cohort']=='F' and m['method']=='F' and m['task']=='reversal'];p=pd.read_parquet(ROOT/'outputs/r16/raw_predictions.parquet');p=p[p.cohort.eq('F')&p.method.eq('F')&p.task.eq('reversal')];actions=dict(dictionary_refresh=dict(status='locally_executable',definition_count=len(json.loads((ROOT/'outputs/r124/current_factor_dictionary.json').read_text()))),l1_reversal_exit=dict(status='local_inputs_available_protocol_needed',models=len(models),prediction_rows=len(p),horizons=sorted(p.horizon.unique().tolist()),years=sorted(p.year.unique().tolist()),calibrated=False),new_data=dict(status='scope_specific_gaps_not_overall_stop',needs=['first release/revision history','ETF share corporate actions and historical industry mapping','complete executable portfolio paths','future independent samples']))
 js(out/'route_audit.json',dict(entry_revision=entry['revision'],slots=len(rows),unique_source_paths=len({x['source'] for x in rows}),classifications=pd.Series([x['classification'] for x in rows]).value_counts().to_dict(),items=rows));js(out/'next_actions.json',actions)
 js(out/'verification.json',dict(status='PASS',all_legacy_slots_inspected=len(rows),unique_source_paths=len({x['source'] for x in rows}),current_verified_routes=len(entry['routes']),scope='file content inventory and explicit interpretation triage; not independent validation of all historical results',protocol_sha256=sha(ROOT/'protocols/r163.json'),code_sha256=sha(Path(__file__))))
 print(json.dumps(actions,ensure_ascii=False));print('R163 AUDITED',len(rows))
if __name__=='__main__':run()
