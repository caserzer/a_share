from common import *
import pandas as pd
from portfolio_r04 import path_for
G=KEY+['horizon','method','variant']
def run():
 out=ROOT/'outputs/r218';out.mkdir(exist_ok=True);paths=[ROOT/'outputs/r198/predictions.parquet',ROOT/'outputs/r140/cohort_new.parquet',ROOT/'outputs/r129/daily_2026-10-21.parquet',CACHE/'forecast_v5/CSI_ALL.parquet'];p=pd.read_parquet(paths[0]);co=pd.read_parquet(paths[1]);p=p.merge(co[KEY+['date','entry_date']],on=KEY+['date'],validate='many_to_one');prices=pd.read_parquet(paths[2]);market=pd.read_parquet(paths[3]).close;cal=pd.DatetimeIndex(market.index);prices['day_i']=cal.get_indexer(prices.date);lookup={k:g.set_index('date') for k,g in prices.groupby(KEY)};cache={};rows=[];maxerr=0
 for row in p.to_dict('records'):
  key=tuple(row[x] for x in KEY)+ (row['date'],row['horizon']);rec={c:row[c] for c in G+['date','entry_date','maturity','prediction','target','regime']};rec['choose_industry']=row['prediction']>0
  if key not in cache:
   entry=row['entry_date'];end=row['maturity'];v=None
   if pd.notna(entry) and pd.notna(end) and entry in cal and end in cal:
    days=cal[(cal>=entry)&(cal<=end)];a=path_for(lookup[key[:3]],days);b=market.reindex(days).to_numpy()/market.loc[entry]
    if a is not None and np.isfinite(b).all():
     ir=a[-1]-1;mr=b[-1]-1;dd=lambda w:float(np.min(w/np.maximum.accumulate(w)-1));v=dict(industry_return=ir,market_return=mr,industry_dd=dd(a),market_dd=dd(b),days=len(days));assert len(days)==row['horizon']+1
   cache[key]=v
  v=cache[key]
  if v is None:rec['status']='unknown_path'
  else:
   err=abs(v['industry_return']-v['market_return']-row['target']);assert np.isfinite(row['target']) and err<1e-10;maxerr=max(maxerr,err);rec.update(v,status='valid');chosen=v['industry_return'] if rec['choose_industry'] else v['market_return'];rec['gross']=chosen;rec['drawdown']=v['industry_dd'] if rec['choose_industry'] else v['market_dd'];rec['excess']=chosen-v['market_return'];rec['wrong_industry']=rec['choose_industry'] and row['target']<0;rec['missed_positive']=not rec['choose_industry'] and row['target']>0
   for label,cost in [('net20',.002),('net50',.005)]:rec[label]=chosen-cost*(2+chosen);rec['industry_'+label]=v['industry_return']-cost*(2+v['industry_return']);rec['market_'+label]=v['market_return']-cost*(2+v['market_return'])
  rows.append(rec)
 d=pd.DataFrame(rows);d.to_parquet(out/'decisions.parquet',index=False);summary=[]
 for key,g in d.groupby(G):
  v=g[g.status.eq('valid')];rec=dict(zip(G,key),planned=len(g),known=len(v),industry_choices=int(g.choose_industry.sum()),mean_net50=v.net50.mean(),net50_vs_market=(v.net50-v.market_net50).mean(),net50_vs_industry=(v.net50-v.industry_net50).mean(),mean_drawdown=v.drawdown.mean(),wrong_industry=int(v.wrong_industry.sum()),missed_positive=int(v.missed_positive.sum()));summary.append(rec)
 pd.DataFrame(summary).to_csv(out/'summary.csv',index=False);pairs=[]
 for key,g in d.groupby(KEY+['horizon']):
  methods=sorted(g.method.unique());cases=[((m,v),(m,'base'),'regime') for m in methods for v in ['state','interaction']]+[((a,v),(b,v),'mechanism') for a,b in [('FSB','FS'),('FSMB','FSM')] for v in ['base','state','interaction']]
  for (am,av),(bm,bv),kind in cases:
   q=g[g.method.eq(am)&g.variant.eq(av)].merge(g[g.method.eq(bm)&g.variant.eq(bv)],on='date',validate='one_to_one',suffixes=('_a','_b'));valid=q.status_a.eq('valid')&q.status_b.eq('valid');v=q[valid];r=dict(zip(KEY+['horizon'],key),kind=kind,first=am+'_'+av,second=bm+'_'+bv,planned=len(q),matched=int(valid.sum()),decision_changes=int(v.choose_industry_a.ne(v.choose_industry_b).sum()))
   for c in ['gross','net20','net50','drawdown']:r['delta_'+c]=(v[c+'_a']-v[c+'_b']).mean()
   pairs.append(r)
 pd.DataFrame(pairs).to_csv(out/'comparisons.csv',index=False);js(out/'verification.json',dict(status='PASS',predictions=len(d),valid=int(d.status.eq('valid').sum()),unique_paths=len(cache),target_max_error=maxerr,adoption=False,inputs={str(x):sha(x) for x in paths+[ROOT/'protocols/r218.json',Path(__file__)]},outputs={x:sha(out/x) for x in ['decisions.parquet','summary.csv','comparisons.csv']}));print('paths',len(cache),'predictions',len(d),'valid',sum(d.status.eq('valid')));print(pd.DataFrame(pairs).query("horizon==20")[['level','kind','first','second','matched','decision_changes','delta_net50']].to_string(index=False))
if __name__=='__main__':run()
