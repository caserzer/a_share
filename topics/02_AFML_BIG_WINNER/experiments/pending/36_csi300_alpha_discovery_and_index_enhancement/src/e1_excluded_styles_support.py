"""Post-support diagnostic of infeasibility, no changed tolerance or new portfolios."""
from e1_excluded_styles import *
def capped_extreme(x,budget,cap,reverse=False):
 x=np.sort(np.asarray(x,float))
 if reverse:x=x[::-1]
 remaining=budget;total=0.
 for value in x:
  w=min(cap,remaining);total+=w*value;remaining-=w
  if remaining<1e-12:break
 assert remaining<1e-9
 return total/budget
def main():
 for s in ['freeze','selection_complete','accounts_complete','analysis_complete']:verify(s)
 assert not (D/'support_audit.json').exists()
 support=pd.read_csv(D/'support.csv',parse_dates=['signal_date'])
 a=pd.read_csv(OUT/'diagnostics'/PREV/'matching.csv',parse_dates=['signal_date']);a=a[(a['mode']=='P')&(a.status=='MATCHED')]
 panel=pd.read_parquet(PRIVATE/PREV/'panel.parquet');targets=pd.read_parquet(PRIVATE/PREV/'targets.parquet');targets=targets[targets.strategy=='O']
 rows=[]
 for date,g in panel.groupby('signal_date'):
  if date not in set(a.signal_date):continue
  g=g.set_index('instrument');g=g[np.isfinite(g[STYLES]).all(axis=1)]
  z=pd.DataFrame(standard(g[STYLES]),index=g.index,columns=STYLES)
  ow=targets[targets.signal_date==date].set_index('instrument').weight
  for ind,chosen in a[a.signal_date==date].groupby('industry'):
   state=support[(support.signal_date==date)&(support.industry==ind)&(support.test=='SM')].status.iloc[0]
   if state!='INFEASIBLE':continue
   codes=chosen.instrument.tolist();peer=sorted(set('|'.join(chosen.peer_codes).split('|'))&set(z.index));budget=ow.loc[codes].sum();cap=ow.loc[codes].max();center=z.loc[codes].T@ow.loc[codes]/budget
   for feature in STYLES:
    lo=capped_extreme(z.loc[peer,feature],budget,cap);hi=capped_extreme(z.loc[peer,feature],budget,cap,True);gap=max(lo-center[feature],center[feature]-hi,0.)
    rows.append(dict(signal_date=date,industry=ind,style=feature,budget=budget,target=center[feature],attainable_low=lo,attainable_high=hi,minimum_gap=gap,univariate_blocked=gap>.2500001))
 detail=pd.DataFrame(rows);write(detail,'feasibility_ranges.csv')
 group=detail.groupby(['signal_date','industry']).univariate_blocked.any();summary=detail.groupby('style').agg(groups_blocked=('univariate_blocked','sum'),max_required_gap=('minimum_gap','max')).reset_index();write(summary,'feasibility_summary.csv')
 coverage=pd.read_csv(D/'coverage.csv');summ=[]
 for test,g in coverage.groupby('test'):summ.append(dict(test=test,mean_covered_total_budget=g.covered_budget.mean(),excluded_budget_coverage=g.covered_budget.sum()/g.excluded_budget.sum(),prior_P_budget_coverage=g.covered_budget.sum()/g.prior_P_budget.sum()))
 write(pd.DataFrame(summ),'coverage_summary.csv')
 # Explicitly validate zero-support evidence is not silently presented as measured zero.
 stats=pd.read_csv(D/'statistics.csv');sm=stats[stats.comparison.isin(['O-SM','SM_O-SM_PEER'])]
 assert sm['mean'].isna().all() and sm.p.isna().all() and sm.n.eq(0).all()
 amend=json.loads((D/'evaluation_amendment.json').read_text())
 for f in amend['original_source']+amend['evaluation_source']:assert sha(f['path'])==f['sha256']
 for s in ['freeze','selection_complete','accounts_complete','analysis_complete']:verify(s)
 save_json(D/'support_audit.json',dict(status='PASS',post_result_descriptive=True,no_new_strategy=True,infeasible_groups=len(group),univariate_blocked_groups=int(group.sum()),joint_or_capacity_coupled_groups=int((~group).sum()),zero_support_inference_verified=True,files=record([D/'feasibility_ranges.csv',D/'feasibility_summary.csv',D/'coverage_summary.csv']),sources=record([Path(__file__)])))
 print(summary.sort_values('groups_blocked',ascending=False).to_string(index=False));print('groups',len(group),int(group.sum()),flush=True)
if __name__=='__main__':main()
