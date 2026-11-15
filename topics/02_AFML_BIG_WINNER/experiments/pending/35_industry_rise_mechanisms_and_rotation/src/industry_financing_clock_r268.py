from common import *
import pandas as pd
K=KEY+['previous_date','current_date']
def run():
 out=ROOT/'outputs/r268';out.mkdir(exist_ok=True);base=pd.read_parquet(ROOT/'outputs/r261/industry_pairs.parquet');links=pd.read_parquet(ROOT/'outputs/r261/common_company_links.parquet');end=pd.read_parquet(ROOT/'outputs/r267/endpoints.parquet');cols=['date','instrument','security_id','common_valid','financing','raw_close','total_shares','snapshot_raw_close','snapshot_shares'];z=links.copy()
 for side in ['previous','current']:
  e=end[cols].rename(columns={c:c+'_'+side for c in cols if c not in ['instrument','security_id']});z=z.merge(e,left_on=[side+'_date','instrument','security_id'],right_on=['date_'+side,'instrument','security_id'],how='left',validate='many_to_one')
 z['dual_complete']=z.common_valid_previous.eq(True)&z.common_valid_current.eq(True);z.to_parquet(out/'company_links.parquet',index=False);v=z[z.dual_complete].copy();aggcols=[]
 for clock in ['signal','snapshot']:
  prefix='' if clock=='signal' else 'snapshot_';price='raw_close' if clock=='signal' else 'snapshot_raw_close';shares='total_shares' if clock=='signal' else 'snapshot_shares';m0=v[price+'_previous']*v[shares+'_previous'];m1=v[price+'_current']*v[shares+'_current'];b0=v.financing_previous;b1=v.financing_current
  for name,values in [('f00',b0/m0),('f10',b1/m0),('f01',b0/m1),('f11',b1/m1)]:v[clock+'_'+name]=values;aggcols.append(clock+'_'+name)
 med=v.groupby(K)[aggcols].median().reset_index();count=v.groupby(K).size().rename('dual_common').reset_index();keep=K+['members_previous','members_current','complete_common','native_rows_present','qualified','balance_component','cap_component','common_change'];b=base[keep].rename(columns={'qualified':'original_qualified','balance_component':'original_balance','cap_component':'original_cap','common_change':'original_change'});r=b.merge(count,on=K,how='left',validate='one_to_one').merge(med,on=K,how='left',validate='one_to_one');r.dual_common=r.dual_common.fillna(0).astype(int);r['qualified']=r.native_rows_present&r.dual_common.ge(5)&r.dual_common.ge(.8*r.members_previous)&r.dual_common.ge(.8*r.members_current);r.loc[~r.qualified,aggcols]=np.nan
 for clock in ['signal','snapshot']:
  a,b,c,d=[r[clock+'_'+x] for x in ['f00','f10','f01','f11']];r[clock+'_balance']=.5*(b-a+d-c);r[clock+'_cap']=.5*(c-a+d-b);r[clock+'_change']=d-a;assert np.allclose(r[clock+'_balance']+r[clock+'_cap'],r[clock+'_change'],equal_nan=True,atol=1e-12)
 r.to_parquet(out/'industry_pairs.parquet',index=False);summary=[]
 for k,g in r.groupby(['era','level']):
  q=g[g.qualified];up=q[q.snapshot_change.gt(0)];summary.append(dict(zip(['era','level'],k),candidates=len(g),original_qualified=int(g.original_qualified.sum()),qualified=len(q),dates=q.current_date.nunique(),removed_links=int((g.complete_common-g.dual_common).sum()),change_sign_disagree=int(np.sign(q.signal_change).ne(np.sign(q.snapshot_change)).sum()),balance_sign_disagree=int(np.sign(q.signal_balance).ne(np.sign(q.snapshot_balance)).sum()),signal_up=int(q.signal_change.gt(0).sum()),snapshot_up=len(up),snapshot_up_balance_nonpositive=int(up.snapshot_balance.le(0).sum()),median_abs_clock_change_difference=float((q.snapshot_change-q.signal_change).abs().median())))
 pd.DataFrame(summary).to_csv(out/'summary.csv',index=False);js(out/'receipt.json',dict(status='PASS',original_links=len(z),dual_links=len(v),qualified=int(r.qualified.sum()),inputs={s:sha(ROOT/s) for s in ['outputs/r261/industry_pairs.parquet','outputs/r261/common_company_links.parquet','outputs/r267/endpoints.parquet','protocols/r268.json','src/industry_financing_clock_r268.py']},outcomes_read=False,adoption=False));print(pd.DataFrame(summary).to_string(index=False))
if __name__=='__main__':run()
