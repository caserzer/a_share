"""Post-result disclosure: missing exits, calendar concentration, decision-time cases.
No selection changes, no new strategy and no promotion to confirmatory tests.
"""
from e1_excluded_holdings import *
def main():
 for x in ['freeze','selection_complete','accounts_complete','analysis_complete']:verify(x)
 assert not (D/'disclosure_audit.json').exists()
 e=pd.read_csv(D/'events.csv',parse_dates=['signal_date','exit_date'])
 e=e[e.exit_date<=END];dates=sorted(e.signal_date.unique());extra=[]
 for field,label in [('marked_return','mark_to_market_entry_cost_only'),('net_return','executable_liquidation')]:
  panel=e.pivot(index='signal_date',columns='strategy',values=field);s=panel.SELECTED-panel.PEERS
  for sample,a in [('all',s),('2022_onward_posthoc',s[s.index>=pd.Timestamp('2022-01-01')])]:
   extra.append(dict(metric=label,sample=sample,**bootstrap(a,'M',3)))
 frames={s:pd.read_csv(D/'accounts'/(s+'__main.csv'),parse_dates=['date']).set_index('date') for s in ['O','P']}
 daily=daily_returns(frames['O'].nav)-daily_returns(frames['P'].nav)
 extra.append(dict(metric='annual_daily_original_path',sample='2022_onward_posthoc',**daily_stat(daily[daily.index>=pd.Timestamp('2022-01-01')])))
 write(pd.DataFrame(extra),'disclosure_sensitivity.csv')
 # Full decision-case table, joined only after primary execution and analysis.
 p=pd.read_parquet(L/'panel.parquet')
 p['E1_sector_percentile']=p.groupby(['signal_date','industry']).E1.rank(method='average',pct=True)
 cases=pd.read_csv(D/'matching.csv',parse_dates=['signal_date'])
 cases=cases[cases['mode']=='P'].merge(p,on=['signal_date','instrument'],how='left',validate='one_to_one',suffixes=('','_panel'))
 labels=pd.read_parquet(PRIVATE/'labels.parquet')[['signal_date','instrument','h10','h10_mature']]
 cases=cases.merge(labels,on=['signal_date','instrument'],validate='one_to_one')
 cases.loc[cases.h10_mature>END,'h10']=np.nan
 c=pd.read_parquet(PRIVATE/OLD/'score_contributions.parquet')
 groups=['range_position','returns_trend','volatility_drawdown','volume_liquidity','market_common']
 cases=cases.merge(c[['signal_date','instrument']+groups],on=['signal_date','instrument'],how='left',validate='one_to_one')
 ledger=pd.read_parquet(L/'excluded_daily.parquet')
 linked=ledger.groupby(['signal_date','instrument']).wealth_contribution.sum().rename('original_linked_active_contribution').reset_index()
 cases=cases.merge(linked,on=['signal_date','instrument'],how='left',validate='one_to_one')
 write(cases,'decision_cases.csv')
 coverage=pd.read_csv(D/'coverage.csv');summary=[]
 for mode,g in coverage.groupby('mode'):
  summary.append(dict(mode=mode,mean_excluded_budget=g.excluded_budget.mean(),mean_matched_budget=g.matched_budget.mean(),budget_weighted_coverage=g.matched_budget.sum()/g.excluded_budget.sum(),mean_date_coverage=g.excluded_coverage.mean(),min_date_coverage=g.excluded_coverage.min(),max_target_weight=g.max_control_weight.max(),mean_control_count=g.control_count.mean()))
 write(pd.DataFrame(summary),'coverage_summary.csv')
 # Availability-aware profile differences, no outcome fit and no threshold selection.
 profiles=pd.read_csv(D/'signal_profiles.csv');out=[]
 for (mode,feature),g in profiles.groupby(['mode','feature']):
  values=g.pivot(index='signal_date',columns='side',values='value');known=g.pivot(index='signal_date',columns='side',values='known_budget');budget=g.groupby('signal_date').matched_budget.first()
  out.append(dict(mode=mode,feature=feature,n_dates=int((values.selected-values.peers).notna().sum()),mean_selected=values.selected.mean(),mean_peers=values.peers.mean(),mean_gap=(values.selected-values.peers).mean(),selected_coverage=known.selected.sum()/budget.sum(),peer_coverage=known.peers.sum()/budget.sum()))
 write(pd.DataFrame(out),'profile_summary.csv')
 # Check known metadata and disclosure closure; no observed outcome affects targets.
 checks=[]
 def ck(name,ok):assert bool(ok),name;checks.append(dict(name=name,passed=True))
 ck('unique decision cases',not cases.duplicated(['signal_date','instrument']).any())
 ck('signal no later than source cap date',cases.source_date.dropna().le(cases.loc[cases.source_date.notna(),'signal_date']).all())
 ck('50 planned dates',len(dates)==50)
 ck('marked pair retains all dates',e.pivot(index='signal_date',columns='strategy',values='marked_return')[['SELECTED','PEERS']].notna().all(axis=1).sum()==50)
 ck('case counterfactual not assigned zero to legacy',cases.original_linked_active_contribution.notna().any())
 for x in ['freeze','selection_complete','accounts_complete','analysis_complete']:verify(x)
 save_json(D/'disclosure_audit.json',dict(status='PASS',count=len(checks),checks=checks,post_result=True,not_confirmatory=True,files=record([D/n for n in ['disclosure_sensitivity.csv','decision_cases.csv','coverage_summary.csv','profile_summary.csv']]),source=record([Path(__file__)])))
 print(pd.DataFrame(extra).to_string(index=False));print(pd.DataFrame(summary).to_string(index=False),flush=True)
if __name__=='__main__':main()
