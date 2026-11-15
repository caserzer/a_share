from common import *
import pandas as pd
from itertools import combinations
from math import comb
import sys
clock=sys.argv[1];p=pd.read_parquet(ROOT/f'outputs/r271/{clock}/actions/actions.parquet');out=ROOT/'outputs/r271'/clock/'random';d=pd.read_csv(out/'date_metrics.csv',parse_dates=['date']);sy=pd.read_csv(out/'missing_sensitivity.csv');checks=0;fixtures=0
for row in d.to_dict('records'):
 mask=np.ones(len(p),bool)
 for k in ['era','level','horizon','method','variant','date']:mask&=p[k].eq(row[k]).to_numpy()
 g=p[mask];n=len(g);k=int(g.alert.sum());prob=comb(n-1,k-1)/comb(n,k);v=g[g.status.eq('valid')];c=row['cost'];gains=[]
 for x in v.to_dict('records'):
  hold=(1+x['ret'])*(1-c);exit_value=1-c if row['policy']=='cash' else (1-c)*(1-c)*(1+x['market'])*(1-c);gains.append(exit_value-hold)
 gains=np.array(gains);a=v.alert.to_numpy(float);assert np.isclose(row['random_known_conditional'],sum(gains)*prob/len(v));assert np.isclose(row['selection_constant'],sum(gains*a)/n);assert np.isclose(row['random_unknown_coefficient'],prob*(n-len(v))/n);checks+=3
 if row['complete'] and n<=12 and fixtures<20:
  values=[sum(gains[list(ix)])/n for ix in combinations(range(n),k)];assert np.isclose(np.mean(values),row['random_constant']);fixtures+=1
for row in sy.to_dict('records'):
 g=d[d.era.eq(row['era'])&d.level.eq(row['level'])&d.horizon.eq(row['horizon'])&d.cost.eq(row['cost'])&d.policy.eq(row['policy'])];method,variant=row['new'].split('/');a=g[g.method.eq(method)&g.variant.eq(variant)].sort_values('date')
 if row['kind']=='model_pair':
  method,variant=row['reference'].split('/');b=g[g.method.eq(method)&g.variant.eq(variant)].sort_values('date');bc=b.selection_constant.to_numpy();bu=b.selection_unknown_coefficient.to_numpy()
 else:bc=a.random_constant.to_numpy();bu=a.random_unknown_coefficient.to_numpy()
 for hypothetical_gain in [-2.,0.,3.]:
  # Algebra fixture only, not an imputed or economically bounded missing return.
  direct=np.mean(a.selection_constant.to_numpy()+a.selection_unknown_coefficient.to_numpy()*hypothetical_gain-bc-bu*hypothetical_gain);assert np.isclose(direct,row['constant']+row['unknown_coefficient']*hypothetical_gain,atol=1e-12);checks+=1
# Exhaustive algebra fixtures; not additional market samples.
for n in range(3,9):
 gains=np.arange(n,dtype=float)**2/100-.12
 for k in range(1,n):
  avg=np.mean([sum(gains[list(ix)])/n for ix in combinations(range(n),k)])
  assert np.isclose(avg,(k/n)*gains.mean());fixtures+=1
summary=pd.read_csv(out/'summary.csv')
for row in summary.to_dict('records'):
 z=d.copy()
 for k in ['era','level','horizon','method','variant','cost','policy']:z=z[z[k].eq(row[k])]
 if str(row['period'])!='all':z=z[z.date.dt.year.eq(int(row['period']))]
 if row['scope']=='complete_dates':z=z[z.complete]
 assert len(z)==row['dates']
 assert np.isclose((z.selection_known_conditional-z.random_known_conditional).mean(),row['model_minus_random']);checks+=1
js(out/'independent_verification.json',dict(status='PASS',checks=checks,enumerated_uniform_subset_fixtures=fixtures,scope='Combinatorial inclusion probabilities; independent liquidation cashflows; small full enumeration; symbolic missing-term algebra at arbitrary fixtures, not assumed missing outcomes',code_sha256=sha(__file__),adoption=False));print('VERIFIED',checks,fixtures)
