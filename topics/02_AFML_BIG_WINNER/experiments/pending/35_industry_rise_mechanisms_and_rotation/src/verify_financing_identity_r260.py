from common import *
import pandas as pd
from margin_inventory_r44 import SOURCE

def run():
 out=ROOT/'outputs/r260';z=pd.read_parquet(out/'endpoints.parquet');p=pd.read_parquet(out/'pairs.parquet');d=pd.read_parquet(SOURCE/'normalized_detail.parquet');stock=pd.read_parquet(CACHE/'extension_v2/products/panel.parquet');members=pd.read_parquet(CACHE/'extension_v2/products/assignments.parquet',columns=['month','instrument','security_id']).drop_duplicates()
 src=d.set_index(['date','instrument']);obs=z.set_index(['date','instrument']);pd.testing.assert_frame_equal(obs[['snapshot_date','financing']].sort_index(),src[['snapshot_date','financing']].sort_index())
 maps={k:set(g.security_id) for k,g in members.groupby(['month','instrument'])}
 for row in z[['date','instrument','security_id','identity_count']].itertuples():
  ids=maps.get((row.date.to_period('M')-1,row.instrument),set())
  if len(ids)==1:assert row.security_id in ids and row.identity_count==1
  elif not ids:assert pd.isna(row.identity_count) and pd.isna(row.security_id)
  else:assert row.identity_count==len(ids) and pd.isna(row.security_id)
 mapped=z[z.security_id.notna()];check=mapped.merge(stock,on=['date','security_id'],how='left',suffixes=('','_source'),validate='many_to_one')
 for col in ['raw_close','total_shares','share_effective_date','listed']:assert (check[col].eq(check[col+'_source'])|(check[col].isna()&check[col+'_source'].isna())).all()
 validity=z.identity_count.eq(1)&z.listed.eq(True)&z.share_effective_date.le(z.date)
 for col in ['financing','raw_close','total_shares']:validity&=z[col].gt(0)&np.isfinite(z[col])
 assert validity.eq(z.valid).all()
 v=p[p.complete];ratio_growth=(v.financing_current/v.financing_previous)/(v.raw_close_current/v.raw_close_previous)/(v.total_shares_current/v.total_shares_previous)
 assert np.allclose(np.exp(v.dlog_intensity),ratio_growth,rtol=1e-12,atol=0)
 for field,col in [('balance','financing'),('price','raw_close'),('shares','total_shares')]:assert np.allclose(np.exp(v['dlog_'+field]),v[col+'_current']/v[col+'_previous'],rtol=1e-12,atol=0)
 for side,date in [('previous','previous_date'),('current','current_date')]:
  source=z.rename(columns={'date':date});merged=p.merge(source,on=[date,'instrument'],how='left',suffixes=('','_source'),validate='many_to_one')
  for col in ['financing','raw_close','total_shares','security_id','valid']:
   a=merged[col+'_'+side];b=merged[col];assert (a.eq(b)|(a.isna()&b.isna())).all(),col
 expected_complete=p._merge.eq('both')&p.valid_previous.eq(True)&p.valid_current.eq(True)&p.security_id_previous.eq(p.security_id_current);assert expected_complete.eq(p.complete).all()
 assert p.loc[~p.complete,['dlog_balance','dlog_price','dlog_shares','dlog_intensity','intensity_up']].isna().all().all()
 cal=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index;lookup={d:i for i,d in enumerate(cal)};assert (z.date.map(lookup)-z.snapshot_date.map(lookup)).eq(2).all()
 summary=json.loads((out/'summary.json').read_text());assert summary['complete_pairs']==len(v);assert summary['intensity_up']==v.dlog_intensity.gt(0).sum();assert summary['up_balance_nonincrease']==(v.dlog_intensity.gt(0)&v.financing_current.le(v.financing_previous)).sum()
 ds=pd.read_csv(out/'date_summary.csv');assert ds.complete.sum()==len(v) and ds.candidates.sum()==len(p)
 js(out/'independent_verification.json',dict(status='PASS',endpoint_source_checks=len(z),pair_endpoint_checks=len(p)*2,complete_multiplicative_identity_checks=len(v),zero_complete_date_pairs=int(ds.complete.eq(0).sum()),near_zero_nonzero_log_changes=int((v.dlog_intensity.ne(0)&v.dlog_intensity.abs().lt(1e-12)).sum()),scope='Source fields, prior-month mapping, eligibility and algebra; no causal or trading claim',adoption=False));print('VERIFIED',len(z),len(v))
if __name__=='__main__':run()
