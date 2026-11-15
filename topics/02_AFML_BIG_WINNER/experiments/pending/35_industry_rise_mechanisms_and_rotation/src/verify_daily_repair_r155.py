"""Check repaired-source equivalence, protocol identity and replay verification receipts."""
import pandas as pd
from common import *

def run():
 out=ROOT/'outputs/r155';root=out/'evaluation';rec=json.loads((out/'input_receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h,p
 for rel,h in rec['copies'].items():assert sha(root/rel)==h,rel
 old=pd.read_parquet(ROOT/'outputs/r129/daily_2026-10-21.parquet');new=pd.read_parquet(root/'cache/forecast_v5/daily_industries.parquet')
 pd.testing.assert_frame_equal(old,new.drop(columns='day_i'))
 calendar=pd.read_parquet(root/'cache/forecast_v5/CSI_ALL.parquet').index;assert new.day_i.eq(new.date.map({d:i for i,d in enumerate(calendar)})).all()
 for n in [9,97,98,99]:assert sha(ROOT/f'protocols/r{n:02d}.json')==sha(root/f'protocols/r{n:02d}.json')
 execution=json.loads((out/'execution_receipt.json').read_text());assert execution['status']=='PASS'
 assert len(execution['verification_hashes'])==4
 for p,h in execution['verification_hashes'].items():assert sha(p)==h and json.loads(Path(p).read_text())['status']=='PASS'
 comparison=json.loads((out/'comparison.json').read_text());p=pd.read_csv(out/'uncertainty_comparison.csv');assert len(p)==8
 for side in ['old','new']:
  expected=np.where(p['high_family_'+side]<0,'daily_better',np.where(p['low_family_'+side]>0,'daily_worse','inconclusive'));assert (p['family_conclusion_'+side]==expected).all()
 assert comparison['uncertainty']['family_conclusion_changes']==int((p.family_conclusion_old!=p.family_conclusion_new).sum())
 js(out/'verification.json',dict(status='PASS',source_rows=len(new),unchanged_protocols=4,upstream_verifications=4,uncertainty_folds=8,scope='Exact corrected input equivalence except independently checked exchange calendar ordinal; original protocol verifiers; paired familywise conclusions',verifier_sha256=sha(Path(__file__))))
 print('R155 VERIFIED',len(new))
if __name__=='__main__':run()
