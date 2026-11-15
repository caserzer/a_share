import pandas as pd
from common import *


def run():
 out=ROOT/'outputs/r24';receipt=json.loads((out/'receipt.json').read_text())
 for p,h in receipt['reads'].items():assert sha(p)==h
 for p,h in receipt['outputs'].items():assert sha(p)==h
 p=pd.read_parquet(ROOT/'data/r24_report_pairs.parquet');s=pd.read_csv(out/'revision_pairs.csv')
 good=p[p.pair_status.eq('positive_pair')];assert np.allclose(good.implied_shares,good.profit/good.eps)
 g=s[s.status.eq('positive_comparable_candidate')]
 assert np.allclose(g.implied_share_ratio,(g.profit_new*g.eps_old)/(g.eps_new*g.profit_old))
 assert np.allclose(g.profit_revision,(g.profit_new-g.profit_old)/(g.profit_new+g.profit_old))
 assert np.allclose(g.eps_revision,(g.eps_new-g.eps_old)/(g.eps_new+g.eps_old))
 assert ((pd.to_datetime(g.publication_date)-pd.to_datetime(g.previous_date)).dt.days<=365).all()
 review=json.loads((out/'source_review.json').read_text())
 for row in review['sources']:assert sha(row['path'])==row['compressed_sha256']
 assert sha(review['overlay_path'])==review['overlay_sha256']
 original=pd.read_parquet(ROOT/'data/r11_analyst_forecasts.parquet');overlay=pd.read_parquet(review['overlay_path'])
 excluded=pd.read_csv(out/'quarantined_source_values.csv')
 assert len(original)==len(overlay)+len(excluded) and len(excluded)==6
 for issue in review['issues']:
  if issue['decision'].startswith('quarantine'):assert not (overlay.infoCode.eq(issue['infoCode'])&overlay.basis.eq(issue['basis'])).any()
 keys=['infoCode','basis','fiscal_year'];z=overlay.merge(original,on=keys,validate='one_to_one',suffixes=('_overlay','_old'));assert np.array_equal(z.value_overlay,z.value_old)
 js(out/'verification.json',dict(status='PASS_AUDIT_NOT_DATA_CERTIFICATION',positive_revision_pairs=len(g),quarantined_source_values=6,reviewed_html_reports=len(review['sources']),code_sha256=sha(__file__),limitation='selected raw review and arithmetic checks, not exhaustive forecast-source validity; R15 downstream replay pending'))
 print('R24 verified',len(g),'positive pairs and six source exclusions')

if __name__=='__main__':run()
