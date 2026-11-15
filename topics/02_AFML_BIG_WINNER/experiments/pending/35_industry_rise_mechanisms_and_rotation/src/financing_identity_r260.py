from common import *
import pandas as pd
from margin_inventory_r44 import SOURCE

def run():
 out=ROOT/'outputs/r260';dp=SOURCE/'normalized_detail.parquet';mp=CACHE/'extension_v2/products/assignments.parquet';sp=CACHE/'extension_v2/products/panel.parquet'
 d=pd.read_parquet(dp,columns=['date','snapshot_date','instrument','financing']);m=pd.read_parquet(mp,columns=['month','security_id','instrument']).drop_duplicates();s=pd.read_parquet(sp,columns=['date','security_id','raw_close','total_shares','share_effective_date','listed'])
 assert not d.duplicated(['date','instrument']).any() and not s.duplicated(['date','security_id']).any()
 ambiguity=m.groupby(['month','instrument']).security_id.nunique().rename('identity_count');m=m.merge(ambiguity,on=['month','instrument']);unique=m[m.identity_count.eq(1)]
 d['month']=d.date.dt.to_period('M')-1;z=d.merge(unique,on=['month','instrument'],how='left',validate='many_to_one').merge(s,on=['date','security_id'],how='left',validate='many_to_one')
 # Missing unique mapping includes unavailable or ambiguous identities; record separately.
 z=z.drop(columns='identity_count').merge(ambiguity.reset_index(),on=['month','instrument'],how='left',validate='many_to_one')
 z['valid']=z.identity_count.eq(1)&z.listed.eq(True)&z.share_effective_date.le(z.date)
 for c in ['financing','raw_close','total_shares']:z['valid']&=z[c].gt(0)&np.isfinite(z[c])
 z.to_parquet(out/'endpoints.parquet',index=False);dates=sorted(d.date.unique());pairs=[];skips=[]
 for prev,now in zip(dates[:-1],dates[1:]):
  prev,now=pd.Timestamp(prev),pd.Timestamp(now)
  if now.to_period('M').ordinal-prev.to_period('M').ordinal!=1:skips.append(dict(previous=prev,current=now));continue
  old=z[z.date.eq(prev)];new=z[z.date.eq(now)];q=old.merge(new,on='instrument',how='outer',suffixes=('_previous','_current'),validate='one_to_one',indicator=True);q['previous_date']=prev;q['current_date']=now;q['complete']=q._merge.eq('both')&q.valid_previous.eq(True)&q.valid_current.eq(True)&q.security_id_previous.eq(q.security_id_current)
  for name,col in [('balance','financing'),('price','raw_close'),('shares','total_shares')]:q['dlog_'+name]=np.log(q[col+'_current'].where(q.complete)/q[col+'_previous'].where(q.complete))
  ratio0=q.financing_previous/(q.raw_close_previous*q.total_shares_previous);ratio1=q.financing_current/(q.raw_close_current*q.total_shares_current);q['dlog_intensity']=np.log(ratio1.where(q.complete)/ratio0.where(q.complete));q['residual']=q.dlog_intensity-q.dlog_balance+q.dlog_price+q.dlog_shares
  if q.complete.any():assert q.loc[q.complete,'residual'].abs().max()<1e-12
  # Nullable flags never treat unavailable pairs as no change.
  for name in ['intensity','balance','price','shares']:
   q[name+'_up']=q['dlog_'+name].gt(0).astype('boolean').where(q.complete)
  pairs.append(q)
 p=pd.concat(pairs,ignore_index=True);p.to_parquet(out/'pairs.parquet',index=False);rows=[]
 for (prev,now),g in p.groupby(['previous_date','current_date']):
  v=g[g.complete];up=v[v.intensity_up];rows.append(dict(previous=prev,current=now,candidates=len(g),complete=len(v),left_only=int(g._merge.eq('left_only').sum()),right_only=int(g._merge.eq('right_only').sum()),both_invalid=int((g._merge.eq('both')&~g.complete).sum()),intensity_up=len(up),up_balance_nonincrease=int(up.dlog_balance.le(0).sum()),up_balance_increase=int(up.dlog_balance.gt(0).sum()),up_price_decline=int(up.dlog_price.lt(0).sum()),share_changed=int(v.dlog_shares.ne(0).sum())))
 pd.DataFrame(rows).to_csv(out/'date_summary.csv',index=False);js(out/'skipped_nonadjacent_dates.json',skips)
 summary=dict(status='PASS',endpoint_rows=len(z),unique_mapping=int(z.identity_count.eq(1).sum()),ambiguous_mapping=int(z.identity_count.gt(1).sum()),missing_mapping=int(z.identity_count.isna().sum()),valid_endpoints=int(z.valid.sum()),pair_rows=len(p),complete_pairs=int(p.complete.sum()),date_pairs=len(rows),skipped_date_gaps=len(skips),intensity_up=int(p.intensity_up.sum()),up_balance_nonincrease=int((p.complete&p.dlog_intensity.gt(0)&p.dlog_balance.le(0)).sum()),max_identity_residual=float(p.residual.abs().max()),adoption=False)
 js(out/'summary.json',summary);js(out/'receipt.json',dict(inputs={str(path):sha(path) for path in [dp,mp,sp,ROOT/'protocols/r260.json',Path(__file__)]},outcomes_read=False,quality='Historical-proxy; financing snapshot and denominator signal-date clocks differ'))
 print(summary)
if __name__=='__main__':run()
