"""Nominal member concentration with explicit unknown mass and target distances."""
import pandas as pd
from common import *

def run():
 out=ROOT/'outputs/r172';mp=CACHE/'extension_v2/products/assignments.parquet';m=pd.read_parquet(mp,columns=KEY+['month','date','security_id','unresolved']);m=m[m.level.eq('L2')];assert not m.duplicated(['era','level','month','security_id']).any();lookup={k:g for k,g in m.groupby(KEY+['month'])};positions=[];records=[];links=[];vectors={};industry={};reads=[mp,ROOT/'protocols/r172.json',Path(__file__)]
 for variant,n in [('top10',169),('top20',137)]:
  hp=ROOT/f'outputs/r{n}/evaluation/outputs/r04/holdings.parquet';reads.append(hp);h=pd.read_parquet(hp);h=h[h.level.eq('L2')]
  for key,g in h.groupby(['era','level','method','origin']):
   era,level,method,origin=key;weights={};unknown=0.;rawcount=0;missing=0;maxdate=pd.NaT
   for row in g.itertuples():
    source=lookup.get((era,level,row.industry_code,origin.to_period('M')));usable=source is not None and len(source)>0 and source.date.le(origin).all()
    if not usable:unknown+=row.weight;missing+=1;links.append(dict(variant=variant,era=era,level=level,method=method,origin=origin,industry_code=row.industry_code,industry_weight=row.weight,known=0,unresolved=None,denominator=None,unknown_weight=row.weight,status='missing_or_future_snapshot'));continue
    assert source.unresolved.nunique()==1;ids=sorted(source.security_id.unique());u=int(source.unresolved.iloc[0]);den=len(ids)+u;assert den>0 and u>=0;rawcount+=len(ids);unknown+=row.weight*u/den
    mx=source.date.max();maxdate=mx if pd.isna(maxdate) else max(maxdate,mx)
    for sid in ids:weights[sid]=weights.get(sid,0)+row.weight/den
    links.append(dict(variant=variant,era=era,level=level,method=method,origin=origin,industry_code=row.industry_code,industry_weight=row.weight,known=len(ids),unresolved=u,denominator=den,unknown_weight=row.weight*u/den,status='nominal_known_and_unresolved'))
   known=sum(weights.values());largest=max(weights.values(),default=0);hhi=sum(w*w for w in weights.values());assert np.isclose(known+unknown,1)
   identity=dict(variant=variant,era=era,level=level,method=method,origin=origin)
   records.append(dict(identity,known_stocks=len(weights),known_weight=known,unknown_weight=unknown,missing_industries=missing,duplicate_member_entries=rawcount-len(weights),membership_max_date=maxdate,known_max_weight=largest,known_hhi=hhi,total_hhi_lower=hhi,total_hhi_upper=min(1,hhi+2*largest*unknown+unknown**2),max_weight_upper=min(1,largest+unknown)))
   positions.extend(dict(identity,security_id=sid,weight=w) for sid,w in sorted(weights.items()));vectors[(variant,*key)]=(weights,unknown);industry[(variant,*key)]=dict(zip(g.industry_code,g.weight))
 pd.DataFrame(records).to_csv(out/'concentration.csv',index=False);pd.DataFrame(positions).to_parquet(out/'nominal_positions.parquet',index=False);pd.DataFrame(links).to_csv(out/'industry_links.csv',index=False);trans=[]
 for (variant,era,level,method),g in pd.DataFrame(records).groupby(['variant','era','level','method']):
  dates=sorted(g.origin)
  for before,after in zip(dates[:-1],dates[1:]):
   ka=(variant,era,level,method,before);kb=(variant,era,level,method,after);a,u=vectors[ka];b,v=vectors[kb];ia=industry[ka];ib=industry[kb];dist=sum(abs(b.get(x,0)-a.get(x,0)) for x in set(a)|set(b));idist=sum(abs(ib.get(x,0)-ia.get(x,0)) for x in set(ia)|set(ib))
   trans.append(dict(variant=variant,era=era,level=level,method=method,prior_origin=before,origin=after,consecutive_month=after.to_period('M')==before.to_period('M')+1,industry_target_distance=idist,known_stock_distance=dist,stock_distance_lower=max(0,dist-u-v),stock_distance_upper=min(2,dist+u+v),prior_unknown=u,current_unknown=v,new_known_names=len(set(b)-set(a)),removed_known_names=len(set(a)-set(b))))
 pd.DataFrame(trans).to_csv(out/'target_transitions.csv',index=False);summary=[]
 for key,g in pd.DataFrame(records).groupby(['variant','era','method']):
  t=pd.DataFrame(trans);t=t[t.variant.eq(key[0])&t.era.eq(key[1])&t.method.eq(key[2])&t.consecutive_month]
  summary.append(dict(zip(['variant','era','method'],key),origins=len(g),mean_known_stocks=g.known_stocks.mean(),max_unknown_weight=g.unknown_weight.max(),mean_known_hhi=g.known_hhi.mean(),mean_known_max_weight=g.known_max_weight.mean(),max_known_max_weight=g.known_max_weight.max(),duplicate_entries=int(g.duplicate_member_entries.sum()),adjacent_transitions=len(t),mean_industry_distance=t.industry_target_distance.mean(),mean_stock_lower=t.stock_distance_lower.mean(),mean_stock_upper=t.stock_distance_upper.mean(),stock_lower_exceeds_industry=int(t.stock_distance_lower.gt(t.industry_target_distance+1e-12).sum())))
 pd.DataFrame(summary).to_csv(out/'summary.csv',index=False);js(out/'receipt.json',dict(status='PASS',reads={str(p):sha(p) for p in reads},origins=len(records),position_rows=len(positions),links=len(links),transitions=len(trans),adoption=False,strict_pit=False,actual_holdings_certified=False))
 print('R172',len(records),len(positions),len(links),len(trans))
if __name__=='__main__':run()
