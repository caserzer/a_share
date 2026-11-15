"""Independent selections, complete paths, weight drift and wealth accounting."""
import pandas as pd
from common import *

def run():
 out=ROOT/'outputs/r137';root=out/'evaluation';dest=root/'outputs/r04';panel=pd.read_parquet(root/'data/monthly_panel.parquet');daily=pd.read_parquet(root/'cache/forecast_v5/daily_industries.parquet');market=pd.read_parquet(root/'cache/forecast_v5/CSI_ALL.parquet').close;cal=pd.DatetimeIndex(market.index)
 for p,h in json.loads((out/'summary.json').read_text())['reads'].items():assert sha(p)==h
 assert np.array_equal(daily.day_i,cal.get_indexer(daily.date));paths={k:g.set_index('date').sort_index() for k,g in daily.groupby(KEY)}
 intervals=pd.read_csv(dest/'intervals.csv',parse_dates=['origin','entry','exit']);holdings=pd.read_parquet(dest/'holdings.parquet');dr=pd.read_parquet(dest/'daily_returns.parquet');summary=pd.read_csv(dest/'summary.csv');ik=['era','level','method','origin'];il=intervals.set_index(ik);assert il.index.is_unique;seen=set();npaths=0;valids=0;drows=0
 ends=pd.Series(cal,index=cal).groupby(cal.to_period('M')).max();ends=[x for per,x in ends.items() if per.end_time.normalize()<=cal.max() and cal.get_loc(x)+1<len(cal)];nxt=dict(zip(ends[:-1],ends[1:]))
 for (era,level),u in panel.groupby(['era','level']):
  for method in ['equal','momentum','F','FD','FC']:
   drift={};invalid=False;accepted=[];events=[];expected_holdings=[]
   for date,g in u.groupby('date'):
    if date not in nxt:continue
    entry=cal[cal.get_loc(date)+1];exit=cal[cal.get_loc(nxt[date])+1]
    if (era=='SW2014' and exit>pd.Timestamp('2021-11-30')) or (era=='SW2021' and entry<pd.Timestamp('2022-01-01')):continue
    key=(era,level,method,date);seen.add(key);row=il.loc[key];assert row.entry==entry and row.exit==exit
    g=g[g.price_ready].dropna(subset=['breadth21','breadth63','turn_rank504']);assert row.universe==len(g)
    if len(g)<20:
     assert row.status=='insufficient_signal_universe'
     if accepted:invalid=True
     continue
    if method=='equal':selected=g.sort_values('industry_code')
    else:
     cols=['mom20','mom60','vol20','dd60','breadth21','breadth63','turn_rank504'];r=(g[cols].rank()-.5)/len(g)-.5;f=((r.mom20+r.mom60)/2-r.vol20+r.dd60)/3;s={'momentum':r.mom60,'F':f,'FD':(f+(r.breadth21+r.breadth63)/2)/2,'FC':(f-r.turn_rank504)/2}[method];selected=g.assign(score=s).sort_values(['score','industry_code'],ascending=[False,True]).head(int(np.ceil(.2*len(g))))
    target=pd.Series(1/len(selected),index=selected.industry_code);hh=holdings[holdings.era.eq(era)&holdings.level.eq(level)&holdings.method.eq(method)&holdings.origin.eq(date)].set_index('industry_code');assert set(hh.index)==set(target.index) and np.allclose(hh.weight,1/len(selected));assert hh.entry.eq(entry).all();expected_holdings.extend(hh.index)
    dates=cal[(cal>=entry)&(cal<=exit)];vectors=[];bad=[]
    for code in selected.industry_code:
     z=paths[(era,level,code)].reindex(dates);npaths+=1
     good=z.nav.notna().all() and z.block.nunique()==1 and z.day_i.diff().dropna().eq(1).all()
     if good:vectors.append(z.nav.to_numpy()/z.nav.iloc[0])
     else:bad.append(code)
    assert row.selected==len(selected)
    if bad:
     assert row.status=='missing_selected_path' and set(str(row.missing_codes).split(';'))==set(bad);invalid=True;drift={};continue
    assert row.status=='valid';valids+=1;nav=np.mean(vectors,axis=0);names=set(target.index)|set(drift);turn=sum(abs(target.get(k,0)-drift.get(k,0)) for k in names);gross=nav[-1]-1
    for field,v in dict(turnover=turn,max_weight=target.max(),gross_return=gross,benchmark_return=market.loc[exit]/market.loc[entry]-1,net20=(1-.002*turn)*nav[-1]-1,net50=(1-.005*turn)*nav[-1]-1).items():assert np.isclose(row[field],v,atol=1e-12),(key,field)
    drift={c:vec[-1]/len(selected)/nav[-1] for c,vec in zip(selected.industry_code,vectors)};accepted.append(row)
    events.append([entry,1.,1-.002*turn,1-.005*turn,1.])
    for j in range(1,len(dates)):events.append([dates[j],nav[j]/nav[j-1],nav[j]/nav[j-1],nav[j]/nav[j-1],market.loc[dates[j]]/market.loc[dates[j-1]]])
   hh=holdings[holdings.era.eq(era)&holdings.level.eq(level)&holdings.method.eq(method)];assert len(hh)==len(expected_holdings)
   actual=dr[dr.era.eq(era)&dr.level.eq(level)&dr.method.eq(method)].set_index('date');ss=summary[summary.era.eq(era)&summary.level.eq(level)&summary.method.eq(method)]
   if not accepted:assert actual.empty and ss.empty;continue
   events.append([accepted[-1]['exit'],1.,.998,.995,1.]);factors=pd.DataFrame(events,columns=['date','gross','net20','net50','benchmark']).groupby('date').prod();expected=factors-1;assert actual.index.equals(expected.index);assert np.allclose(actual[expected.columns],expected,atol=1e-12);assert actual.whole_path_valid.eq(not invalid).all();drows+=len(actual)
   assert len(ss)==3
   for row in ss.to_dict('records'):
    c=row['cost'];assert row['whole_path_valid']==(not invalid) and row['valid_intervals']==len(accepted);assert np.isclose(row['monthly_turnover_mean'],np.mean([a.turnover for a in accepted]));assert np.isclose(row['total_turnover_with_final_exit'],sum(a.turnover for a in accepted)+1);assert np.isclose(row['mean_valid_interval_return'],np.mean([a['gross_return' if c=='gross' else c] for a in accepted]));assert np.isclose(row['max_target_industry_weight'],max(a.max_weight for a in accepted))
    if invalid:
     for col in ['cagr','drawdown','vol','beta','benchmark_cagr','total_return']:assert pd.isna(row[col])
    else:
     wealth=factors[c].cumprod();years=(wealth.index[-1]-wealth.index[0]).days/365.25;values=dict(cagr=wealth.iloc[-1]**(1/years)-1,drawdown=(wealth/wealth.cummax().clip(lower=1)-1).min(),vol=expected[c].std()*np.sqrt(252),beta=expected[c].cov(expected.benchmark)/expected.benchmark.var(),benchmark_cagr=factors.benchmark.prod()**(1/years)-1,total_return=wealth.iloc[-1]-1)
     for col,v in values.items():assert np.isclose(row[col],v,atol=1e-12),(era,level,method,col)
 assert seen==set(il.index)
 js(out/'verification.json',dict(status='PASS',intervals=len(seen),selected_paths=npaths,valid_intervals=valids,daily_portfolio_rows=drows,summary_rows=len(summary),verifier_sha256=sha(__file__),checks=['all original schedules and selections','every selected path completeness','drifted weights and turnover','daily factors and shared rebalance fees','final liquidation','all valid summary risk metrics and missing-path gates']))
 print('PORTFOLIO VERIFIED',len(seen),npaths,drows,flush=True)
if __name__=='__main__':run()
