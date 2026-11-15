import pandas as pd
from common import *
import verify_capital_coverage_r68,verify_capital_cashflow_r69,verify_capital_profit_r70,verify_capital_controls_r71,verify_capital_monthly_r73,verify_capital_monitor_r74
from integrated_monitor_r93 import build

def run():
 out=ROOT/'outputs/r147';root=out/'evaluation';summary=json.loads((out/'summary.json').read_text())
 for p,h in summary['reads'].items():assert sha(p)==h,p
 mods=[verify_capital_coverage_r68,verify_capital_cashflow_r69,verify_capital_profit_r70,verify_capital_controls_r71,verify_capital_monthly_r73,verify_capital_monitor_r74]
 for m in mods:m.ROOT=root;m.run()
 changes=[]
 specs=[(68,'industry_coverage',KEY+['period','field']),(69,'industry_evidence',KEY+['period']),(70,'industry_evidence',KEY+['period']),(71,'industry_contrasts',KEY+['period','outcome']),(73,'industry_evidence',KEY+['snapshot','period']),(74,'monthly_observations',KEY+['snapshot'])]
 for n,name,keys in specs:
  a=pd.DataFrame(json.loads((ROOT/f'outputs/r{n}/{name}.json').read_text()));b=pd.DataFrame(json.loads((root/f'outputs/r{n}/{name}.json').read_text()));p=a.merge(b,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');p.to_json(out/f'r{n}_pairs.json',orient='records',force_ascii=False,indent=2);g=p[p._merge.eq('both')];fields={}
  for c in a:
   if c in keys:continue
   x=g[c+'_old'];y=g[c+'_new'];fields[c]=sum(not ((pd.isna(u) and pd.isna(v)) if not isinstance(u,list) and not isinstance(v,list) else False) and u!=v for u,v in zip(x,y))
  added=p[p._merge.eq('right_only')];gate='coverage_gate' if 'coverage_gate' in b else 'eligible' if 'eligible' in b else None
  changes.append(dict(round=n,old=len(a),new=len(b),added=len(added),removed=int(p._merge.eq('left_only').sum()),common_field_changes=fields,added_gate_pass=int(added[gate+'_new'].eq(True).sum()) if gate else None))
 pp=ROOT/'outputs/r138/predictions.parquet';ep=root/'outputs/r74/evidence_matrix.parquet';tasks=pd.read_parquet(pp);d,e,extra=build(tasks,pd.read_parquet(ep));d['model_source_round']=np.where(d.level.eq('L1'),'R16','R131');d['integration_scope']='repaired_historical_display_no_evidence_in_model';d['model_clock_scope']='corrected_basket_historical_proxy_not_forward'
 prior=ROOT/'outputs/r138/task_evidence.parquet';old=pd.read_parquet(prior);keys=KEY+['asof','task','horizon','method','cohort'];a=old.sort_values(keys).reset_index(drop=True);b=d.sort_values(keys).reset_index(drop=True);pd.testing.assert_frame_equal(a[keys],b[keys]);fields={}
 for c in a:
  same=a[c].eq(b[c])|(a[c].isna()&b[c].isna());fields[c]=int((~same).sum())
 for c in tasks.columns:assert fields.get(c,0)==0,c
 d.to_parquet(out/'task_evidence.parquet',index=False);pd.DataFrame([dict(field=k,changed=v) for k,v in fields.items() if v]).to_csv(out/'monitor_field_changes.csv',index=False)
 monitor=dict(rows=len(d),changed_fields={k:v for k,v in fields.items() if v},all_original_task_columns_unchanged=True,states_old=old.evidence_operating_status.value_counts(dropna=False).to_dict(),states_new=d.evidence_operating_status.value_counts(dropna=False).to_dict())
 js(out/'verification.json',dict(status='PASS',comparisons=changes,monitor=monitor,monitor_reads={str(p):sha(p) for p in [pp,ep,prior,ROOT/'src/integrated_monitor_r93.py']},subchecks={str(p.relative_to(root)):sha(p) for p in root.glob('outputs/*/verification.json')},verifier_sha256=sha(__file__)))
 print(json.dumps(changes,default=str));print(json.dumps(monitor,default=str))
if __name__=='__main__':run()
