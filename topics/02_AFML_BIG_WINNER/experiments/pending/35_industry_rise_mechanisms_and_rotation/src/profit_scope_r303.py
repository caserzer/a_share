from common import *
import pandas as pd,zipfile
from decimal import Decimal as D
from supplement_financials import SOURCE

def direction(a,b):return 'up' if a>b else 'down' if a<b else 'flat'
def run():
 out=ROOT/'outputs/r303';out.mkdir(exist_ok=True);sources={};old=json.loads((ROOT/'outputs/r70/receipt.json').read_text())
 for p,h in old['reads'].items():assert sha(p)==h;sources[p]=h
 receipts=json.loads((SOURCE/'query_receipts.json').read_text());pages=[]
 with zipfile.ZipFile(SOURCE/'inputs/provider_responses.zip') as z:
  for r in receipts:
   if r['api']!='income_vip':continue
   payload=z.read(r['archived_response']);assert hashlib.sha256(payload).hexdigest()==r['raw_sha256'];obj=json.loads(payload);fields=obj['data']['fields'];assert obj['code']==0 and len(obj['data']['items'])==r['rows']
   pages.append(dict(query_id=r['query_id'],archive_path=r['archived_response'],sha256=r['raw_sha256'],fields=fields,rows=r['rows'],params=r['params'],retrieved_at=r['retrieved_at'],has_consolidated='n_income' in fields,has_minority='minority_gain' in fields))
 raw=pd.read_parquet(ROOT/'data/financial_archive_all_market.parquet');base=pd.read_parquet(ROOT/'outputs/r70/member_evidence.parquet');valid=base[base.joint_profit_known];keys=['instrument','audit_period'];unique=valid.drop_duplicates(keys)
 # No substitution using later reports. All known original pairs remain unavailable for this sensitivity if original source has neither field.
 assert not any(x['has_consolidated'] or x['has_minority'] for x in pages),'New source field found: implement qualified same-row bridge before continuing'
 assert 'n_income' not in raw and 'minority_gain' not in raw
 unavailable=unique[keys+['profit_current','profit_prior','mechanism_scope']].copy();unavailable['consolidated_sensitivity_status']='source_fields_absent';unavailable.to_parquet(out/'unavailable_original_pairs.parquet',index=False)
 cells=json.loads((ROOT/'outputs/r302/profit_scope_comparison.json').read_text());bs={x['symbol']:x for x in json.loads((ROOT/'outputs/r302/bridges.json').read_text())};lookup={(x['symbol'],x['period']):x for x in cells};rows=[]
 for s,b in bs.items():
  a=lookup[s,'2026H1'];p=lookup[s,'2025H1'];cons=direction(D(a['consolidated']),D(p['consolidated']));attr=direction(D(a['attributable']),D(p['attributable']));ocf=direction(D(b['values'][0]['cashflow']),D(b['values'][1]['cashflow']))
  rows.append(dict(symbol=s,name=b['name'],financial=b['financial'],consolidated_direction=cons,attributable_direction=attr,direction_changed=cons!=attr,consolidated_current_loss=D(a['consolidated'])<0,attributable_current_loss=D(a['attributable'])<0,consolidated_change=str(D(a['consolidated'])-D(p['consolidated'])),attributable_change=str(D(a['attributable'])-D(p['attributable'])),cashflow_direction=ocf,announce_date=b['announce_date'],observed_at=b['observed_at'],usage='separate descriptive pair, not original historical-asof sensitivity',strict_pit=False))
 js(out/'source_field_audit.json',pages);js(out/'fixed10_comparison.json',rows)
 summary=dict(original_income_pages=len(pages),original_income_rows=sum(x['rows'] for x in pages),original_member_rows=len(base),original_joint_known_rows=len(valid),original_unique_known_pairs=len(unique),consolidated_available_pairs=0,original_sensitivity_result='unknown_source_fields_absent',fixed10_comparisons=len(rows),fixed10_nonfinancial=sum(not x['financial'] for x in rows),fixed10_direction_changes=sum(x['direction_changed'] for x in rows),fixed10_loss_flag_changes=sum(x['consolidated_current_loss']!=x['attributable_current_loss'] for x in rows),status='AUDITED_NOT_PREDICTIVELY_VALIDATED',new_models=0,strict_pit=False,whole_goal_complete=False)
 js(out/'summary.json',summary)
 for p in [SOURCE/'query_receipts.json',SOURCE/'inputs/provider_responses.zip',ROOT/'outputs/r70/member_evidence.parquet',ROOT/'outputs/r70/receipt.json',ROOT/'outputs/r302/profit_scope_comparison.json',ROOT/'outputs/r302/bridges.json',ROOT/'protocols/r303.json',Path(__file__)]:sources[str(p)]=sha(p)
 js(out/'receipt.json',dict(inputs=sources,outputs={str(p.relative_to(out)):sha(p) for p in out.iterdir() if p.is_file() and p.name!='receipt.json'}));print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':run()
