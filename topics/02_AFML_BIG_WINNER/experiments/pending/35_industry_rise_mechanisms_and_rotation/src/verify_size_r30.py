import pandas as pd
from common import *

def run():
 out=ROOT/'outputs/r30';receipt=json.loads((out/'receipt.json').read_text())
 for p,d in receipt['reads'].items():assert sha(p)==d
 f=pd.read_parquet(ROOT/'data/r30_size_control.parquet');assert sha(ROOT/'data/r30_size_control.parquet')==receipt['feature_sha256']
 assert not f.duplicated(KEY+['date']).any();assert f.membership_month.eq(f.date.dt.to_period('M')-1).all();assert f.size_known.le(f.size_members).all()
 assert f.size_ready.eq(f.size_known.ge(5)&f.size_coverage.ge(.8)).all();assert f.size_control.notna().eq(f.size_ready).all()
 cols=['month']+KEY+['security_id'];members=pd.concat([pd.read_parquet(CACHE/'extension_v2/products/assignments.parquet',columns=cols),pd.read_parquet(ROOT/'data/l1_assignments.parquet',columns=cols)],ignore_index=True)
 stock=pd.read_parquet(CACHE/'extension_v2/products/panel.parquet',columns=['security_id','date','listed','raw_close','total_shares','share_effective_date'])
 selected=f.groupby(['era','level'],group_keys=False).sample(n=20,random_state=30);checked=0
 for row in selected.itertuples():
  m=members[members.month.eq(row.membership_month)&members.era.eq(row.era)&members.level.eq(row.level)&members.industry_code.eq(row.industry_code)]
  z=stock[stock.date.eq(row.date)&stock.security_id.isin(m.security_id)].copy();cap=z.raw_close*z.total_shares;good=z.listed&cap.gt(0)&np.isfinite(cap)&z.raw_close.gt(0)&z.total_shares.gt(0)
  assert z.loc[good,'share_effective_date'].le(row.date).all();values=np.log(cap[good]);assert len(m)==row.size_members and len(values)==row.size_known
  assert np.isclose(values.median(),row.size_median_log_cap,equal_nan=True);checked+=1
 js(out/'verification.json',dict(status='PASS',direct_industry_checks=checked,rows=len(f),checks=['all source hashes','unique identities','prior-month membership','unchanged denominator','5/80 eligibility and missing values','raw close times shares direct median'],limitations='effective dates alone do not certify first availability; no return evaluation',code_sha256=sha(__file__)))
 print('R30 VERIFIED',checked,'direct industry medians')
if __name__=='__main__':run()
