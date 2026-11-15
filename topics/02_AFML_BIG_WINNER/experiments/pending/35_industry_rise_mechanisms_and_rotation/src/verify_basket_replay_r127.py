"""Independent stored R05/R102 comparisons, hashes and append-contract checks."""
import pandas as pd
from common import *
from cutoff_features_r102 import DAILY

def run():
    out=ROOT/'outputs/r127';receipt=json.loads((out/'receipt.json').read_text())
    for p,digest in receipt['reads'].items():assert sha(p)==digest,p
    daily=pd.read_parquet(ROOT/'data/l1_daily.parquet',columns=DAILY)
    checks=[];old=None
    for item in receipt['results']:
        cutoff=item['cutoff'];p=out/f'daily_{cutoff}.parquet';assert sha(p)==item['sha256']
        actual=pd.read_parquet(p)
        expected=daily[daily.date.le(cutoff)].sort_values(KEY+['date']).reset_index(drop=True)
        pd.testing.assert_frame_equal(actual,expected,check_exact=False,atol=1e-12,rtol=1e-12)
        fp=out/f'features_{cutoff}.parquet';assert sha(fp)==item['feature_sha256']
        features=pd.read_parquet(fp);ref=pd.read_parquet(ROOT/f'outputs/r102/features_{cutoff}.parquet')
        ref=ref[ref.level.eq('L1')].sort_values(KEY+['date']).reset_index(drop=True)
        pd.testing.assert_frame_equal(features,ref,check_exact=False,atol=1e-12,rtol=1e-12)
        if old is not None:
            prefix=actual[actual.date.le(old.date.max())].reset_index(drop=True)
            pd.testing.assert_frame_equal(prefix,old,check_exact=True)
        checks.append(dict(cutoff=cutoff,daily_rows=len(actual),feature_rows=len(features),status='PASS'))
        old=actual
    js(out/'verification.json',dict(status='PASS',comparisons=checks,references={str(p):sha(p) for p in [ROOT/'data/l1_daily.parquet',*[ROOT/f'outputs/r102/features_{x["cutoff"]}.parquet' for x in receipt['results']]]},limitation='Existing-source replay only; L2/L3 and real new-data acquisition unverified'))
    print(checks)

if __name__=='__main__':run()
