from pathlib import Path
from decimal import Decimal as D
import json,hashlib
import pandas as pd
import numpy as np
R=Path(__file__).resolve().parents[1];O=R/'outputs/r305';K=['era','level','industry_code','date']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
r=json.loads((O/'receipt.json').read_text())
for p,h in r['inputs'].items():assert sha(R/p)==h
assert sha(r['benchmark_path'])==r['benchmark_sha256']
for p,h in r['outputs'].items():assert sha(O/p)==h
cases=pd.read_parquet(O/'cases.parquet');points=pd.read_parquet(O/'path_points.parquet');old=pd.read_parquet(R/'outputs/r291/path_keys.parquet');cached=np.load(R/'outputs/r291/normalized_paths.npz');joined=cases.merge(old,on=K,validate='one_to_one');assert len(joined)==51
raw=pd.read_parquet(R/'outputs/r129/daily_2026-10-21.parquet').set_index(K);market=pd.read_parquet(r['benchmark_path']).close
for x in joined.itertuples(index=False):
 g=points[points.case_id==x.case_id].sort_values('step');assert list(g.step)==list(range(21));expected_dates=list(market.loc[x.entry_date:x.terminal_date].index);assert list(g.date)==expected_dates
 p=[D(str(raw.loc[(x.era,x.level,x.industry_code,t),'nav'])) for t in expected_dates];m=[D(str(market.loc[t])) for t in expected_dates];rel=[(a/p[0])/(b/m[0])-1 for a,b in zip(p,m)];ret=p[-1]/p[0]-1;ex=p[-1]/p[0]-m[-1]/m[0];low=min(range(1,21),key=lambda i:rel[i]);first=next(i for i in range(1,21) if rel[i]<=D('-.08'))
 assert ret>=D('.05') and ex>=D('.03') and rel[low]<=D('-.08');assert low==x.trough_step and first==x.first_breach_step
 for a,b in [(ret,x.terminal_return),(ex,x.terminal_excess),(rel[low],x.relative_trough)]:assert abs(a-D(str(b)))<D('1e-10')
 assert np.allclose(g.industry_wealth,cached['stock'][x.path_id],atol=1e-12,rtol=0);assert np.allclose(g.market_wealth,cached['market'][x.path_id],atol=1e-12,rtol=0)
 assert all(abs(D(str(v))-z)<D('1e-10') for v,z in zip(g.relative_wealth_return,rel))
result={'status':'PASS','all_case_paths':51,'raw_price_points':1071,'prior_R291_path_matches':51,'decimal_labels_reconstructed':51,'verifier_sha256':sha(__file__)}
(O/'independent_verification.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
