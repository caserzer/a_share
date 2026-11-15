from common import *
import pandas as pd
K=KEY+['date'];G=['family','era','level','method','variant','date'];out=ROOT/'outputs/r213';m=pd.read_parquet(ROOT/'outputs/r145/evaluation/outputs/r110/member_outcomes.parquet');p=pd.read_parquet(ROOT/'outputs/r200/predictions.parquet');p=p[p.task.eq('catchup')];ind=pd.read_parquet(out/'industry_baskets.parquet');d=pd.read_csv(out/'intervals.csv',parse_dates=['date','entry','exit']);hold=pd.read_parquet(out/'selected_industries.parquet')
valid=m.entry_date.eq(m.entry_expected)&m.exit_date.eq(m.exit_expected)&m.entry_listed.eq(True)&m.exit_listed.eq(True)&m.entry_qfq_close.gt(0)&m.exit_qfq_close.gt(0)&np.isfinite(m.entry_qfq_close)&np.isfinite(m.exit_qfq_close)&m.entry_close_chain.notna()&~m.entry_close_chain.isin(['','__MISSING__'])&m.entry_close_chain.eq(m.exit_close_chain)
m['check_return']=(m.exit_qfq_close/m.entry_qfq_close-1).where(valid);assert np.allclose(m.check_return,m.future_return,equal_nan=True);m['check_side']=np.where(m.prior_cap_rank.le(3),'leader','follower');assert m.check_side.eq(m.side).all()
means=m.groupby(K+['check_side']).check_return.mean().unstack();counts=m.groupby(K).check_return.agg(['size','count']);full=counts['size'].eq(counts['count']);means.loc[~full,:]=np.nan;lookup=means.to_dict('index');pm={k:g for k,g in p.groupby(G)};hm={k:g for k,g in hold.groupby(G)};maximum=0;checks=0
for row in d.to_dict('records'):
 key=tuple(row[c] for c in G);source_key=key if row['method']!='equal' else tuple(row[c] for c in G[:3])+('controls','base',row['date']);g=pm[source_key];ordered=sorted(g.to_dict('records'),key=lambda x:(-x['prediction'],x['industry_code']));chosen=ordered if row['method']=='equal' else ordered[:max(1,int(np.ceil(len(g)/5)))];names=[x['industry_code'] for x in chosen];h=hm[key];assert set(names)==set(h.industry_code) and np.allclose(h.industry_weight,1/len(names));sides=[lookup[(row['era'],row['level'],c,row['date'])] for c in names];good=all(np.isfinite(v.get('follower',np.nan)) and np.isfinite(v.get('leader',np.nan)) for v in sides);assert good==(row['status']=='valid')
 if not good:assert pd.isna(row.get('gross'));continue
 f=sum(x['follower']/len(names) for x in sides);l=sum(x['leader']/len(names) for x in sides);values={'follower':f,'leader':l,'gross':f-l}
 for label,rate in [('net20',.002),('net50',.005)]:
  follower_exit=1+f;leader_exit=1+l;fee_f=rate+rate*follower_exit;fee_l=rate+rate*leader_exit;values[label]=f-l-fee_f-fee_l;values['follower_'+label]=f-fee_f;values['leader_'+label]=l-fee_l
 for col,value in values.items():err=abs(value-row[col]);maximum=max(maximum,err);assert err<1e-12;checks+=1
js(out/'independent_verification.json',dict(status='PASS',member_returns_checked=len(m),selection_intervals=len(d),value_checks=checks,max_error=maximum,scope='Original stock endpoint dates/listing/chain returns, frozen selections, complete selected members, independent side fee cashflows',script_sha256=sha(__file__)))
print('PASS',len(m),len(d),checks,maximum)
