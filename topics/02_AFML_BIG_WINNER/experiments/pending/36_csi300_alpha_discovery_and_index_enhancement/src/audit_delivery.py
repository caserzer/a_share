"""Independent consistency checks on model clocks, consumed hashes, and account ledgers."""
import json,numpy as np,pandas as pd
from common import *

def main():
 checks=[]
 def check(name,condition,details=None):
  checks.append(dict(check=name,passed=bool(condition),details=details))
 frozen=json.loads((OUT/'manifests/p0_freeze.json').read_text());check('protocol_unchanged_after_p0',sha(EP/'configs/protocol.json')==frozen['protocol_sha256']);check('features_unchanged_after_p0',sha(EP/'configs/feature_dictionary.csv')==frozen['feature_dictionary_sha256'])
 snapshot=json.loads((OUT/'manifests/data_snapshot.json').read_text());check('feature_bytes_match_snapshot',sha(PRIVATE/'features.parquet')==snapshot['features_sha256']);check('label_bytes_match_snapshot',sha(PRIVATE/'labels.parquet')==snapshot['labels_sha256'])
 for scheme in ['expanding','rolling36']:
  receipts=json.loads((OUT/'manifests'/f'{scheme}_predictions.json').read_text());check(scheme+'_24_quarter_folds',len(receipts)==24)
  for r in receipts:
   p=pd.read_parquet(r['prediction_path']);cut=pd.Timestamp(r['model_fit_cutoff']);q=pd.Period(r['fold'])
   check(scheme+'_'+r['fold']+'_prediction_hash',sha(r['prediction_path'])==r['prediction_sha256'])
   check(scheme+'_'+r['fold']+'_maturity_purge',pd.Timestamp(r['max_label_maturity'])<=cut and pd.Timestamp(r['inner_max_exit'])<pd.Timestamp(r['validation_min_entry']))
   check(scheme+'_'+r['fold']+'_model_clock',(p.signal_date.dt.to_period('Q')==q).all() and (p.feature_cutoff>cut).all())
   check(scheme+'_'+r['fold']+'_model_hashes',all(sha(m['path'])==m['sha256'] for m in r['models']))
   for model in ['E2','E3']:
    a=p.loc[p.model_id.eq(model)].pivot(index=['signal_date','instrument'],columns='seed_or_ensemble',values='score');diff=a['equal_seed_ensemble']-a[['17','42','2026']].mean(axis=1)
    check(scheme+'_'+r['fold']+'_'+model+'_equal_seed_mean',diff.dropna().abs().max()<1e-12)
  a=json.loads((OUT/'manifests'/f'path_a_{scheme}_consumption.json').read_text());b=json.loads((OUT/'manifests'/f'path_b_{scheme}_consumption.json').read_text());check(scheme+'_A_B_identical_prediction_hashes',a==b)
 account_files=sorted((OUT/'accounts').glob('*.csv'));check('all_registered_account_branches',len(account_files)==192,dict(expected=192,actual=len(account_files)))
 failcount=0;ledger_checks=[]
 for f in account_files:
  k=f.stem;r=json.loads((OUT/'manifests'/(k+'.json')).read_text());df=pd.read_csv(f);check(k+'_nav_hash',sha(f)==r['nav_sha256']);check(k+'_execution_version',r.get('execution_version')=='v2_2_membership_execution_gate')
  orders=PRIVATE/'ledgers'/(k+'_orders.parquet');holdings=PRIVATE/'ledgers'/(k+'_holdings.parquet')
  check(k+'_ledger_hashes',sha(orders)==r['orders_sha256'] and sha(holdings)==r['holdings_sha256'])
  z=pd.read_parquet(orders)
  if len(z):
   delta=z.units_after-z.units_before
   valid=(~((delta>1e-8)&~z.can_buy)).all() and (~((delta< -1e-8)&~z.can_sell)).all() and z.units_after.min()>=-1e-9
   check(k+'_blocked_orders_never_filled',valid)
   check(k+'_no_nonmember_buys',not ((delta>1e-10)&~z.current_member).any())
   buyfee,sellfee=np.array(protocol()['costs_bps'][k.split('_')[-1]])/10000
   z['buy_value']=delta.clip(lower=0)*z.qfq_open;z['sell_value']=(-delta).clip(lower=0)*z.qfq_open
   g=z.groupby('date').agg(buy_value=('buy_value','sum'),sell_value=('sell_value','sum'),cash_before=('cash_before','first'),cash_after=('cash_after','first'))
   err=g.cash_before+g.sell_value*(1-sellfee)-g.buy_value*(1+buyfee)-g.cash_after
   check(k+'_cash_fee_conservation',err.abs().max()<1e-8)
  check(k+'_cash_nonnegative',len(df)==0 or df.cash_weight.min()>=-1e-9)
  if r['failures']:
   failcount+=1;bad=pd.Timestamp(r['failures'][0]['date']);check(k+'_stop_before_missing_mark',len(df)==0 or pd.to_datetime(df.date).max()<bad)
 # Price-limit source shape and no duplicate historical keys.
 lim=pd.read_parquet(PRIVATE/'limits/daily.parquet');check('limit_unique_daily_security',not lim.duplicated(['trade_date','ts_code']).any())
 replay=json.loads((OUT/'manifests/model_replay.json').read_text());check('all_models_replay_exact',replay['status']=='PASS' and replay['models']==336)
 report=dict(status='PASS' if all(c['passed'] for c in checks) else 'FAIL',checks=checks,account_branches=len(account_files),valuation_blocked_branches=failcount,statement='Passing engineering checks does not certify PIT sources, actual fills or formal index enhancement.')
 save_json(OUT/'manifests/final_validation.json',report);print(report['status'],'checks',len(checks),'valuation_blocked',failcount)
 if report['status']!='PASS':
  print([x for x in checks if not x['passed']]);raise SystemExit(1)
if __name__=='__main__':main()
