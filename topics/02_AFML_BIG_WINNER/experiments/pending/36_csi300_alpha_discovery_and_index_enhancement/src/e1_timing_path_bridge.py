"""Exact normalized starting-composition x execution-calendar 2x2 monthly bridge."""
import sys,json
from e1_timing_mechanism_evaluate_v2 import *

def freeze_bridge():
 assert not (D/'path_freeze.json').exists()
 save_json(D/'path_freeze.json',dict(created_at=datetime.now(timezone.utc).isoformat(),source_sha256=sha(__file__),authorized='Approved account-path mechanism analysis',prior_fixed_horizon_and_ledger_results_seen=True,definition='Monthly phase1 pretrade open to next phase1 pretrade open; last ends primary last close. Clone normalized actual A and B pretrade states; execute frozen actual A/B target calendars. Four self-financing accounts. Average two log-return decomposition orders (Shapley); keep both order-specific effects. Link across intervals to exact terminal wealth difference. Fixed original phase1 state for stock components.',limits='Inherited composition encodes past decisions; timing includes old-vs-current carry, cash, gates and calendar market path. Not causal effects of investor behavior; original B membership renormalization retained explicitly.',new_model_or_rule=False))

def bridge():
 verify(True);assert sha(__file__)==json.loads((D/'path_freeze.json').read_text())['source_sha256']
 inp=Inputs();marks(inp,0.);a,ao,ah=load_account(ORIGINAL);b,bo,bh=load_account(DELAY);sched=pd.read_csv(D/'schedule.csv',parse_dates=['signal_date','entry_date']);states=pd.read_parquet(L/'states.parquet');accounts={'A':(a,ao,ah),'B':(b,bo,bh)}
 def before(tag,ei):
  f,o,h=accounts[tag];prev=inp.days[ei-1];u=np.zeros(inp.n);cash=1.
  if prev in f.index:
   hh=h[h.date.eq(prev)];u[inp.symbols.get_indexer(hh.instrument)]=hh.synthetic_units;cash=float(f.at[prev,'nav']*f.at[prev,'cash_weight'])
  nav=cash+u@np.nan_to_num(inp.o[ei]);return u/nav,cash/nav,nav
 maps={}
 for tag,(f,o,h) in accounts.items():
  maps[tag]={}
  for date,g in o.groupby('date'):
   v=np.zeros(inp.n+1);v[inp.symbols.get_indexer(g.instrument)]=g.target_weight;maps[tag][inp.days.get_loc(date)]=v
 rows=[];stock=[];checks=[]
 for index,ev in enumerate(sched.itertuples()):
  ei=inp.days.get_loc(ev.entry_date);last=index==len(sched)-1;end=inp.days.get_loc(END) if last else inp.days.get_loc(sched.entry_date.iloc[index+1]);endpx=inp.c[end] if last else inp.o[end];stop=end+1 if last else end
  outcomes={};components={};initial={};starts={}
  for anchor in ['A','B']:
   old,cash,nav=before(anchor,ei);initial[anchor]=nav;starts[anchor]=(old,cash)
   for policy in ['A','B']:
    u=old.copy();c=cash;flow=np.zeros(inp.n);fees=0.
    for j in range(ei,stop):
     if j in maps[policy]:
      member,_,_,_,_,buy,sell,_=inp.context(j-1,j);new,c,info=trade(u.copy(),c,inp.o[j],maps[policy][j],buy&member,sell,.001,.002);flow+=(new-u)*np.nan_to_num(inp.o[j]);u=new;fees+=info['fees']
     check(f'{index}_{anchor}{policy}_{j}_valuation',not np.any((u>1e-12)&~np.isfinite(inp.c[j])))
    check(f'{index}_{anchor}{policy}_endvaluation',not np.any((u>1e-12)&~np.isfinite(endpx)))
    navend=c+u@np.nan_to_num(endpx);comp=np.r_[u*np.nan_to_num(endpx)-old*np.nan_to_num(inp.o[ei])-flow,-fees]
    check(f'{index}_{anchor}{policy}_reconcile',abs(comp.sum()-(navend-1))<1e-10);outcomes[anchor+policy]=navend;components[anchor+policy]=comp
  for tag in ['A','B']:
   endnav=accounts[tag][0].nav.iloc[-1] if last else before(tag,end)[2]
   check(f'{index}_{tag}_actual_account_replay',abs(outcomes[tag+tag]-endnav/initial[tag])<1e-9)
  logs={k:np.log(v) for k,v in outcomes.items()}
  timing_A=logs['AA']-logs['AB'];timing_B=logs['BA']-logs['BB'];inherited_A=logs['AA']-logs['BA'];inherited_B=logs['AB']-logs['BB']
  row=dict(signal_date=ev.signal_date,month=ev.month,end=inp.days[end],last_close=last,**outcomes,timing_on_A=timing_A,timing_on_B=timing_B,inherited_under_A=inherited_A,inherited_under_B=inherited_B,timing=.5*(timing_A+timing_B),inherited=.5*(inherited_A+inherited_B),total=logs['AA']-logs['BB']);rows.append(row)
  def pair(x,y):return (components[x]-components[y])*log_link(np.array([outcomes[x]-1]),np.array([outcomes[y]-1]))[0]
  tc=.5*(pair('AA','AB')+pair('BA','BB'));ic=.5*(pair('AA','BA')+pair('AB','BB'))
  meta=states[states.signal_date.eq(ev.signal_date)].set_index('instrument').reindex(inp.symbols);labels=np.r_[meta.state.to_numpy(),'__FEES__']
  for st in STATES+['__FEES__']:
   ids=labels==st;stock.append(dict(signal_date=ev.signal_date,state=st,timing=tc[ids].sum(),inherited=ic[ids].sum(),total=(tc[ids]+ic[ids]).sum()))
  print('path',ev.month,flush=True)
 z=pd.DataFrame(rows);detail=pd.DataFrame(stock);scale=wealth_scale(a.nav.iloc[-1],b.nav.iloc[-1]);check('whole_continuous_path_log_closure',abs(z.total.sum()-np.log(a.nav.iloc[-1]/b.nav.iloc[-1]))<1e-9)
 for col in ['timing','inherited','total']:detail[col+'_wealth']=detail[col]*scale;z[col+'_wealth']=z[col]*scale
 check('state_path_closure',abs(detail.total_wealth.sum()-100*(a.nav.iloc[-1]-b.nav.iloc[-1]))<1e-8)
 dump(z,'path_bridge_months');dump(detail,'path_bridge_state_month');dump(detail.groupby('state',as_index=False)[['timing_wealth','inherited_wealth','total_wealth']].sum(),'path_bridge_state')
 summary=[]
 for col in ['timing','inherited','total','timing_on_A','timing_on_B','inherited_under_A','inherited_under_B']:summary.append(dict(component=col,linked_wealth=float(z[col].sum()*scale),**stats(z.set_index('signal_date')[col])))
 dump(pd.DataFrame(summary),'path_bridge_summary');save_json(D/'path_validation.json',dict(status='PASS',checks=CHECKS,scale=scale,whole_gap=float(100*(a.nav.iloc[-1]-b.nav.iloc[-1]))))

if __name__=='__main__':globals()[sys.argv[1]]()
