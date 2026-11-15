"""Frozen L2 stock-path audit, retaining all failed intervals and positions."""
import pandas as pd
from common import *

def run():
 out=ROOT/'outputs/r174';pp=ROOT/'outputs/r172/nominal_positions.parquet';cp=ROOT/'outputs/r172/concentration.csv';rp=ROOT/'outputs/r129/receipt.json';bp=CACHE/'forecast_v5/CSI_ALL.parquet';pos=pd.read_parquet(pp);cov=pd.read_csv(cp,parse_dates=['origin']).set_index(['variant','era','level','method','origin']);calendar=pd.DatetimeIndex(pd.read_parquet(bp).index);ev=json.loads(rp.read_text());paths={Path(p).stem:Path(p) for p in ev['reads'] if '/normalized/prices_qfq/' in p};ids=sorted(pos.security_id.unique());idx={s:i for i,s in enumerate(ids)};shape=(len(calendar),len(ids));prices=np.full(shape,np.nan);chains=np.full(shape,-1,dtype=np.int32);volume=np.zeros(shape,bool);buy=np.zeros(shape,dtype=np.uint8);sell=buy.copy();hashes={}
 for j,sid in enumerate(ids):
  p=paths[sid];h=sha(p);assert h==ev['reads'][str(p)];hashes[str(p)]=h;f=pd.read_parquet(p,columns=['date','qfq_close','close_conflict','factor_chain_id','volume','volume_conflict','can_buy','can_sell']).set_index('date').reindex(calendar);price=pd.to_numeric(f.qfq_close);prices[:,j]=price.where(price.gt(0)&f.close_conflict.eq(False));chains[:,j]=pd.factorize(f.factor_chain_id)[0];volume[:,j]=(pd.to_numeric(f.volume).gt(0)&f.volume_conflict.eq(False)).to_numpy()
  for name,a in [('can_buy',buy),('can_sell',sell)]:a[:,j]=np.where(f[name].eq(True),1,np.where(f[name].eq(False),2,0))
  if (j+1)%1500==0:print('read',j+1,len(ids),flush=True)
 groups={k:g for k,g in pos.groupby(['variant','era','level','method','origin'])};rows=[];detail=[];reads=[pp,cp,rp,bp,ROOT/'protocols/r174.json',ROOT/'protocols/r77.json',Path(__file__)]
 for variant,n in [('top10',169),('top20',137)]:
  ip=ROOT/f'outputs/r{n}/evaluation/outputs/r04/intervals.csv';reads.append(ip);iv=pd.read_csv(ip,parse_dates=['origin','entry','exit']);iv=iv[iv.level.eq('L2')]
  for x in iv.itertuples():
   key=(variant,x.era,x.level,x.method,x.origin)
   if key not in groups:continue
   g=groups[key];columns=[idx[s] for s in g.security_id];lo=calendar.get_loc(x.entry);hi=calendar.get_loc(x.exit);p=prices[lo:hi+1,columns];ch=chains[lo:hi+1,columns];valid=np.isfinite(p).all(axis=0);stable=(ch==ch[0]).all(axis=0)&(ch[0]>=0);endpoint=np.isfinite(p[0])&np.isfinite(p[-1])&(ch[0]>=0)&(ch[-1]==ch[0]);good=valid&stable;w=g.weight.to_numpy();u=cov.loc[key,'unknown_weight'];ready=bool(u<1e-12 and good.all() and np.isclose(w.sum(),1));ret=float(w@(p[-1]/p[0])-1) if ready else np.nan;identity=dict(zip(['variant','era','level','method','origin'],key));bu=buy[lo,columns];se=sell[hi,columns];volgood=volume[lo,columns]&volume[hi,columns]
   rows.append(dict(identity,entry=x.entry,exit=x.exit,stocks=len(g),unknown_weight=u,price_bad=int((~valid).sum()),chain_bad=int((~stable).sum()),unvalued_known_weight=float(w[~good].sum()),full_path_valued=ready,endpoint_only_valued=bool(u<1e-12 and endpoint.all()),fixed_stock_gross=ret,synthetic_status=x.status,synthetic_gross=x.gross_return,gross_difference=ret-x.gross_return if ready and pd.notna(x.gross_return) else np.nan,buy_unknown=int((bu==0).sum()),sell_unknown=int((se==0).sum()),buy_disallowed=int((bu==2).sum()),sell_disallowed=int((se==2).sum()),endpoint_volume_bad=int((~volgood).sum()),standalone_entry_exit_eligible=bool(ready and (bu==1).all() and (se==1).all() and volgood.all())))
   for j,z in enumerate(g.itertuples()):detail.append(dict(identity,security_id=z.security_id,weight=z.weight,price_valid=bool(valid[j]),chain_stable=bool(stable[j]),endpoint_valid=bool(endpoint[j]),entry_price=p[0,j],exit_price=p[-1,j],buy_state=int(bu[j]),sell_state=int(se[j]),endpoint_volume_valid=bool(volgood[j])))
 a=pd.DataFrame(rows);a.to_csv(out/'intervals.csv',index=False);pd.DataFrame(detail).to_parquet(out/'stock_interval_audit.parquet',index=False);summary=[]
 for key,g in a.groupby(['variant','era','method']):
  q=g[g.full_path_valued];summary.append(dict(zip(['variant','era','method'],key),planned=len(g),full_path_valued=len(q),endpoint_only_valued=int(g.endpoint_only_valued.sum()),unknown_identity=int(g.unknown_weight.ge(1e-12).sum()),price_gaps=int(g.price_bad.gt(0).sum()),chain_gaps=int(g.chain_bad.gt(0).sum()),standalone_eligible=int(g.standalone_entry_exit_eligible.sum()),comparison_complete=int(q.gross_difference.notna().sum()),mean_difference=q.gross_difference.mean(),min_difference=q.gross_difference.min(),max_difference=q.gross_difference.max(),whole_path_valid=bool(g.full_path_valued.all())))
 pd.DataFrame(summary).to_csv(out/'summary.csv',index=False);js(out/'receipt.json',dict(status='PASS',reads={str(p):sha(p) for p in reads},price_partitions=hashes,intervals=len(rows),stock_rows=len(detail),no_net_curve=True,adoption=False))
 print(pd.DataFrame(summary).to_string(index=False),flush=True)
if __name__=='__main__':run()
