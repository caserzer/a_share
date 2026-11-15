import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r82';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h,p
 old=pd.read_parquet(ROOT/'outputs/r77/stock_interval_audit.parquet');new=pd.read_parquet(out/'stock_audit.parquet');pd.testing.assert_frame_equal(old,new[old.columns])
 iv={(x['method'],pd.Timestamp(x['origin'])):x for x in json.loads((ROOT/'outputs/r77/intervals.json').read_text())};paths={Path(p).stem:Path(p) for p in rec['reads'] if '/prices_qfq/' in p};expected=(old.price_valid&old.chain_stable).copy()
 for sid,g in old[~expected].groupby('security_id'):
  f=pd.read_parquet(paths[sid]).set_index('date')
  for ix,x in g.iterrows():
   v=iv[x['method'],x['origin']];dates=[pd.Timestamp(v['entry']),pd.Timestamp(v['exit'])];valid=True;chains=[]
   for date in dates:
    if date not in f.index:valid=False;continue
    z=f.loc[date];chain=z.factor_chain_id
    if not (pd.notna(z.qfq_close) and z.qfq_close>0 and z.close_conflict==False and pd.notna(chain)):valid=False
    chains.append(chain)
   expected.loc[ix]=bool(valid and len(chains)==2 and chains[0]==chains[1])
 assert expected.equals(new.endpoint_valued)
 rows=json.loads((out/'intervals.json').read_text());mapping={(x['method'],pd.Timestamp(x['origin'])):x for x in rows};assert len(mapping)==len(iv)
 for key,g in new.groupby(['method','origin']):
  v=iv[key];r=mapping[key];ready=v['unknown_weight']<1e-12 and all(g.endpoint_valued) and abs(sum(g.weight)-1)<1e-8;assert r['endpoint_valued']==ready
  assert r['full_path_valued']==v['full_path_valued'] and r['unvalued_stock_count']==int((~g.endpoint_valued).sum())
  assert np.isclose(r['unvalued_known_weight'],sum(g.loc[~g.endpoint_valued,'weight']))
  if ready:
   total=sum(x.weight*(x.exit_price/x.entry_price-1) for x in g.itertuples());assert np.isclose(total,r['fixed_stock_gross'])
   if v['r17_gross'] is not None:assert np.isclose(total-v['r17_gross'],r['difference'])
   if v['full_path_valued']:assert np.isclose(total,v['fixed_stock_gross'])
  else:assert r['fixed_stock_gross'] is None and r['difference'] is None
 for s in json.loads((out/'summary.json').read_text()):
  rr=[x for x in rows if x['method']==s['method']];gg=[x for x in rr if x['endpoint_valued']];delta=[x['difference'] for x in gg if x['difference'] is not None]
  assert s['planned']==len(rr) and s['endpoint_valued']==len(gg) and s['full_path_valued']==sum(x['full_path_valued'] for x in rr)
  assert s['whole_monthly_path']==(len(gg)==len(rr))
  for k,v in [('mean_difference',np.mean(delta) if delta else None),('min_difference',min(delta) if delta else None),('max_difference',max(delta) if delta else None)]:assert s[k] is None if v is None else np.isclose(s[k],v)
 js(out/'verification.json',dict(status='PASS',stock_rows=len(new),intervals=len(rows),scope='all R77 failures reread at endpoints; full-path passes inherited; all weights unchanged and interval returns independently aggregated',receipt_sha256=sha(out/'receipt.json'),verifier_sha256=sha(Path(__file__))))
 print('R82 VERIFIED',len(new),len(rows))
if __name__=='__main__':run()
