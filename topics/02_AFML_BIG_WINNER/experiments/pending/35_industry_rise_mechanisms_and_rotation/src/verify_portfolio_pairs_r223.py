from common import *
import pandas as pd
out=ROOT/'outputs/r223';raw=pd.read_parquet(out/'paired_dates.parquet');lookup={};whole={}
for rnd in [210,211,212,214,215,216,217]:
 d=pd.read_csv(ROOT/f'outputs/r{rnd}/intervals.csv',parse_dates=['origin'])
 for key,g in d.groupby(['era','level','horizon','cohort','method']):
  k=(str(rnd),str(key[0]),str(key[1]),float(key[2]),str(key[3]),str(key[4]));whole[k]=bool(g.status.eq('valid').all())
  for row in g.to_dict('records'):lookup[k+(row['origin'],)]=row
maximum=0.
for row in raw.to_dict('records'):
 common=(str(row['round']),row['era'],row['level'],float(row['horizon']));a=common+(row['first_cohort'],row['first_variant']);b=common+(row['second_cohort'],row['second_variant']);assert (row['whole_pair']=='True')==(whole[a] and whole[b]);aa=lookup[a+(row['date'],)];bb=lookup[b+(row['date'],)];assert aa['entry']==bb['entry'] and aa['exit']==bb['exit'];value=aa[row['metric']]-bb[row['metric']] if aa['status']=='valid' and bb['status']=='valid' else np.nan;assert np.isclose(value,row['delta'],equal_nan=True,atol=1e-12);err=abs(value-row['delta']);maximum=max(maximum,err if np.isfinite(err) else 0)
s=pd.read_csv(out/'uncertainty.csv');assert (s.loc[s.eligible,'whole_pair']==True).all();assert not s.loc[~s.whole_pair,'eligible'].any()
js(out/'independent_pair_verification.json',dict(status='PASS',dated_contrasts=len(raw),max_error=maximum,scope='All deltas from original intervals, same entry/exit, all whole-path flags and incomplete-case exclusion',script_sha256=sha(__file__)));print('PASS',len(raw),maximum)
