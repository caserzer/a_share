from common import *
import pandas as pd

def run():
 out=ROOT/'outputs/r261';qp=ROOT/'outputs/r143/evaluation/data/r45_financing_intensity.parquet';pp=ROOT/'outputs/r260/pairs.parquet';mp=CACHE/'extension_v2/products/assignments.parquet';lp=ROOT/'data/l1_assignments.parquet'
 q=pd.read_parquet(qp);p=pd.read_parquet(pp);cols=KEY+['month','instrument','security_id'];m=pd.concat([pd.read_parquet(mp,columns=cols),pd.read_parquet(lp,columns=cols)]);assert not m.duplicated(KEY+['month','security_id']).any()
 members={k:set(zip(g.instrument,g.security_id)) for k,g in m.groupby(KEY+['month'])};dates=sorted(set(p.previous_date)|set(p.current_date));nextdate=dict(zip(dates[:-1],dates[1:]));prevdate={v:k for k,v in nextdate.items()}
 old=q[q.date.isin(nextdate)].copy();old['current_date']=old.date.map(nextdate);new=q[q.date.isin(prevdate)].copy();new['current_date']=new.date
 census=old.merge(new,on=KEY+['current_date'],how='outer',suffixes=('_previous','_current'),validate='one_to_one',indicator=True);census['previous_date']=census.current_date.map(prevdate)
 pairlookup={k:g.set_index('instrument') for k,g in p.groupby(['previous_date','current_date'])};rows=[];links=[]
 for x in census.itertuples():
  ident={k:getattr(x,k) for k in KEY};k=tuple(ident.values());s0=members.get(k+(x.previous_date.to_period('M')-1,),set());s1=members.get(k+(x.current_date.to_period('M')-1,),set())
  for side,ss in [('previous',s0),('current',s1)]:
   n=getattr(x,'members_'+side)
   if pd.notna(n):assert len(ss)==n
  common=s0&s1;source=pairlookup[(x.previous_date,x.current_date)];selected=[]
  for instrument,sid in sorted(common):
   if instrument in source.index:
    row=source.loc[instrument]
    if row.complete and row.security_id_previous==sid and row.security_id_current==sid:selected.append(row);links.append(dict(ident,previous_date=x.previous_date,current_date=x.current_date,instrument=instrument,security_id=sid))
  n=len(selected);qualified=pd.notna(x.members_previous) and pd.notna(x.members_current) and n>=5 and n>=.8*len(s0) and n>=.8*len(s1)
  rec=dict(ident,previous_date=x.previous_date,current_date=x.current_date,members_previous=len(s0),members_current=len(s1),common_members=len(common),entered_members=len(s1-s0),exited_members=len(s0-s1),complete_common=n,native_rows_present=pd.notna(x.members_previous) and pd.notna(x.members_current),qualified=qualified,native_ready_previous=bool(x.ready_previous) if pd.notna(x.ready_previous) else False,native_ready_current=bool(x.ready_current) if pd.notna(x.ready_current) else False,native_previous=x.financing_intensity_previous,native_current=x.financing_intensity_current)
  fields=['f00','f10','f01','f11','balance_component','cap_component','common_change','native_change','selection_change_difference','balance_nonincrease_share']
  rec.update({f:np.nan for f in fields})
  if qualified:
   v=pd.DataFrame(selected);b0=v.financing_previous.to_numpy();b1=v.financing_current.to_numpy();m0=(v.raw_close_previous*v.total_shares_previous).to_numpy();m1=(v.raw_close_current*v.total_shares_current).to_numpy();f00=np.median(b0/m0);f10=np.median(b1/m0);f01=np.median(b0/m1);f11=np.median(b1/m1);balance=.5*(f10-f00+f11-f01);cap=.5*(f01-f00+f11-f10)
   rec.update(f00=f00,f10=f10,f01=f01,f11=f11,balance_component=balance,cap_component=cap,common_change=f11-f00,balance_nonincrease_share=float((b1<=b0).mean()))
   assert abs(balance+cap-(f11-f00))<1e-12
  if rec['native_ready_previous'] and rec['native_ready_current']:rec['native_change']=rec['native_current']-rec['native_previous']
  if qualified and pd.notna(rec['native_change']):rec['selection_change_difference']=rec['native_change']-rec['common_change']
  rows.append(rec)
 result=pd.DataFrame(rows);result.to_parquet(out/'industry_pairs.parquet',index=False);pd.DataFrame(links).to_parquet(out/'common_company_links.parquet',index=False)
 summary=[]
 for key,g in result.groupby(['era','level']):
  v=g[g.qualified];up=v[v.common_change.gt(0)];both=g[g.native_ready_previous&g.native_ready_current];matched=v[v.native_change.notna()]
  summary.append(dict(zip(['era','level'],key),candidates=len(g),native_both_ready=len(both),qualified=len(v),qualified_dates=v.current_date.nunique(),up=len(up),up_balance_nonpositive=int(up.balance_component.le(0).sum()),up_cap_larger=int((up.cap_component>up.balance_component).sum()),native_common_sign_disagree=int((np.sign(matched.native_change)!=np.sign(matched.common_change)).sum()),native_common_comparable=len(matched)))
 pd.DataFrame(summary).to_csv(out/'summary.csv',index=False);js(out/'receipt.json',dict(status='PASS',industry_pairs=len(result),complete_common_links=len(links),inputs={str(path):sha(path) for path in [qp,pp,mp,lp,ROOT/'protocols/r261.json',Path(__file__)]},outcomes_read=False,adoption=False));print(pd.DataFrame(summary).to_string(index=False))
if __name__=='__main__':run()
