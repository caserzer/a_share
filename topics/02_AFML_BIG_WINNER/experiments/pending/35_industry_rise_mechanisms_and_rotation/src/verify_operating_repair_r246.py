from common import *
import pandas as pd

def run():
 out=ROOT/'outputs/r246';root=out/'evaluation';receipt=json.loads((out/'verification.json').read_text())
 for p,h in receipt['inputs'].items():assert sha(Path(p))==h
 for p,h in receipt['outputs'].items():assert sha(out/p)==h
 copies={'outputs/r73/industry_evidence.json':'outputs/r147/evaluation/outputs/r73/industry_evidence.json','outputs/r73/member_evidence.parquet':'outputs/r147/evaluation/outputs/r73/member_evidence.parquet','outputs/r72/selected_fields.parquet':'outputs/r72/selected_fields.parquet','outputs/r93/task_evidence.parquet':'outputs/r147/task_evidence.parquet','data/r10_alert_followup.parquet':'outputs/r156/evaluation/data/r10_alert_followup.parquet','data/monthly_panel.parquet':'outputs/r130/monthly_panel.parquet'}
 for local,source in copies.items():assert sha(root/local)==sha(ROOT/source)
 keys=KEY+['date','strategy'];old=pd.read_parquet(ROOT/'outputs/r95/alerts.parquet').set_index(keys);new=pd.read_parquet(root/'outputs/r95/alerts.parquet').set_index(keys);saved=json.loads((out/'comparison.json').read_text());both=old.index.intersection(new.index);added=new.index.difference(old.index);removed=old.index.difference(new.index)
 assert len(added)==saved['identities']['right_only'] and len(removed)==saved['identities']['left_only'] and len(both)==saved['identities']['both']
 checked=0
 for col,values in saved['shared_changes'].items():
  a=old.loc[both,col];b=new.loc[both,col]
  if col in ['accounting_coherence','excess20','return20','continuation_excess20_60','breadth_change20']:same=np.isclose(a,b,rtol=1e-10,atol=1e-12,equal_nan=True)
  else:same=a.eq(b)|(a.isna()&b.isna())
  assert int((~same).sum())==values['changed'];checked+=len(a)
 assert sorted(new.accounting_period.dropna().unique())==saved['new_periods']
 for n in [94,95,96]:assert json.loads((root/f'outputs/r{n}/verification.json').read_text())['status']=='PASS'
 # All revised summary values must originate in the fully verified replay.
 for n,keys in [(95,['era','level','strategy','accounting_group','metric']),(96,['era','level','metric'])]:
  a=pd.DataFrame(json.loads((ROOT/f'outputs/r{n}/summary.json').read_text())).set_index(keys);b=pd.DataFrame(json.loads((root/f'outputs/r{n}/summary.json').read_text())).set_index(keys);c=pd.read_csv(out/f'r{n}_summary_comparison.csv').set_index(keys)
  for side,source in [('old',a),('new',b)]:
   for col in source.select_dtypes('number'):
    assert np.allclose(source[col],c.loc[source.index,col+'_'+side],equal_nan=True,atol=1e-12)
 obs=pd.DataFrame(json.loads((root/'outputs/r94/observations.json').read_text()));known=obs[obs.status.eq('source_limited_disclosed_period_available')];evidence=dict(source_snapshots=int(obs.snapshot.nunique()),observations=len(obs),periods=sorted(obs.period.dropna().unique()),qualified_observations=len(known),qualified_industry_period_pairs=len(known[KEY+['period']].drop_duplicates()),alert_known_rows=int(new.accounting_coherence.notna().sum()),alert_economic_periods=int(new.accounting_period.nunique()),independent_period_claim=False)
 js(out/'economic_period_coverage.json',evidence)
 js(out/'independent_verification.json',dict(status='PASS',source_copy_checks=len(copies),shared_field_checks=checked,common_alerts=len(both),added=len(added),removed=len(removed),original_replay_verifiers=[94,95,96],code_sha256=sha(Path(__file__)),adoption=False));print(evidence)
if __name__=='__main__':run()
