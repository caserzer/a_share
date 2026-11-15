"""Audit exact stock-source eligibility at fixed portfolio endpoints."""
import pandas as pd
from common import *

def run():
 out=ROOT/'outputs/r173';mp=CACHE/'extension_v2/products/assignments.parquet';bp=CACHE/'forecast_v5/CSI_ALL.parquet';dp=ROOT/'outputs/r129/daily_2026-10-21.parquet';rp=ROOT/'outputs/r129/receipt.json';receipt=json.loads(rp.read_text());m=pd.read_parquet(mp,columns=KEY+['month','security_id','unresolved']);m=m[m.level.eq('L2')];ml={k:g for k,g in m.groupby(KEY+['month'])};cal=pd.DatetimeIndex(pd.read_parquet(bp).index);ends=pd.Series(cal,index=cal.to_period('M')).groupby(level=0).max();links=[];requests={};endpoints=set();reads=[mp,bp,dp,rp,ROOT/'protocols/r173.json',Path(__file__)]
 for variant,n in [('top10',169),('top20',137)]:
  root=ROOT/f'outputs/r{n}/evaluation/outputs/r04';hp=root/'holdings.parquet';ip=root/'intervals.csv';reads += [hp,ip];h=pd.read_parquet(hp);h=h[h.level.eq('L2')];iv=pd.read_csv(ip,parse_dates=['origin','entry','exit']).set_index(['era','level','method','origin'])
  for row in h.itertuples():
   rec=iv.loc[(row.era,row.level,row.method,row.origin)]
   for phase in ['entry','exit']:
    date=rec[phase];key=(row.era,row.level,row.industry_code,date);endpoints.add(key);links.append(dict(variant=variant,era=row.era,level=row.level,method=row.method,origin=row.origin,industry_code=row.industry_code,phase=phase,date=date,industry_weight=row.weight))
 for era,level,code,date in endpoints:
  g=ml.get((era,level,code,date.to_period('M')-1))
  if g is not None:
   for sid in g.security_id:requests.setdefault(sid,set()).add(date)
 paths={Path(p).stem:Path(p) for p in receipt['reads'] if '/normalized/prices_qfq/' in p};observations=[];source_hashes={}
 for sid,dates in sorted(requests.items()):
  path=paths[sid];assert sha(path)==receipt['reads'][str(path)];source_hashes[str(path)]=sha(path);f=pd.read_parquet(path,columns=['date','qfq_close','close_conflict','factor_chain_id']).set_index('date');dates=sorted(dates);anchors=[ends[x.to_period('M')-1] for x in dates];a=f.reindex(dates);b=f.reindex(anchors);pa=pd.to_numeric(a.qfq_close).to_numpy();pb=pd.to_numeric(b.qfq_close).to_numpy();goodprice=(pa>0)&(pb>0)&a.close_conflict.eq(False).to_numpy()&b.close_conflict.eq(False).to_numpy();ca=a.factor_chain_id.fillna('__MISSING__').to_numpy();cb=b.factor_chain_id.fillna('__MISSING__').to_numpy();chain=(ca!='__MISSING__')&(cb!='__MISSING__')&(ca==cb)
  for j,date in enumerate(dates):observations.append(dict(security_id=sid,date=date,anchor=anchors[j],valid_price=bool(goodprice[j]),valid_chain=bool(chain[j]),eligible=bool(goodprice[j]&chain[j]),relative=float(pa[j]/pb[j]-1) if goodprice[j]&chain[j] else np.nan))
 stock=pd.DataFrame(observations);stock.to_parquet(out/'stock_endpoint_eligibility.parquet',index=False);sl=stock.set_index(['security_id','date']);daily=pd.read_parquet(dp).set_index(KEY+['date']);rows=[]
 for era,level,code,date in sorted(endpoints):
  g=ml.get((era,level,code,date.to_period('M')-1));base=dict(era=era,level=level,industry_code=code,date=date);key=(era,level,code,date);dr=daily.loc[key] if key in daily.index else None;kind='missing' if dr is None else dr.source_kind
  if g is None:rows.append(dict(base,source_kind=kind,status='no_monthly_members'));continue
  ids=list(g.security_id);q=sl.loc[[(sid,date) for sid in ids]];n=len(ids);u=int(g.unresolved.max());den=n+u;cnt=int(q.eligible.sum());coverage=cnt/den;status='observed' if kind=='observed' else kind
  if kind=='observed':assert n>=5 and coverage>=.8 and np.isclose(dr.coverage,coverage) and dr.members==n
  rows.append(dict(base,source_kind=kind,status=status,known=n,unresolved=u,denominator=den,priced=cnt,invalid_price=int((~q.valid_price).sum()),price_valid_chain_invalid=int((q.valid_price&~q.valid_chain).sum()),coverage=coverage,eligible_rule=n>=5 and coverage>=.8,relative_mean=q.relative.mean()))
 ep=pd.DataFrame(rows);ep.to_csv(out/'industry_endpoints.csv',index=False);z=pd.DataFrame(links).merge(ep,on=KEY+['date'],how='left',validate='many_to_one');diff=[]
 for row in z.itertuples():
  a=ml.get((row.era,row.level,row.industry_code,row.origin.to_period('M')));b=ml.get((row.era,row.level,row.industry_code,row.date.to_period('M')-1));aa=set() if a is None else set(a.security_id);bb=set() if b is None else set(b.security_id);diff.append((len(bb-aa),len(aa-bb)))
 z[['added_price_members','removed_nominal_members']]=diff;z.to_parquet(out/'holding_endpoint_links.parquet',index=False);summary=[]
 for key,g in z.groupby(['variant','era','method','origin','phase']):
  ready=g.status.eq('observed');mass=g.industry_weight*(1-g.coverage);summary.append(dict(zip(['variant','era','method','origin','phase'],key),selected_industries=len(g),observed_industries=int(ready.sum()),anchor_industries=int(g.source_kind.eq('anchor').sum()),missing_industries=int(g.source_kind.eq('missing').sum()),observed_industry_weight=g.loc[ready,'industry_weight'].sum(),unpriced_nominal_mass=mass.sum() if g.coverage.notna().all() else np.nan,added_price_members=int(g.added_price_members.sum()),removed_nominal_members=int(g.removed_nominal_members.sum())))
 pd.DataFrame(summary).to_csv(out/'portfolio_endpoints.csv',index=False);js(out/'receipt.json',dict(status='PASS',reads={str(p):sha(p) for p in reads},stock_source_hashes=source_hashes,stock_rows=len(stock),unique_industry_endpoints=len(ep),holding_endpoints=len(z),portfolio_endpoints=len(summary),adoption=False,whole_stock_path_certified=False))
 print('R173',len(stock),len(ep),len(z),len(summary),flush=True)
if __name__=='__main__':run()
