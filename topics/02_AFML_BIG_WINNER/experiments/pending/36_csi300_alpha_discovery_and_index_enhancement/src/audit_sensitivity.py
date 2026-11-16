import numpy as np,pandas as pd
from common import *

def main():
 checks=[]
 for scenario in ['suspend_flat','suspend_haircut20']:
  root=OUT/'sensitivity'/scenario;private=PRIVATE/'sensitivity'/scenario
  for receipt in sorted(root.glob('*.json')):
   key=receipt.stem;r=json.loads(receipt.read_text());nav=pd.read_csv(root/(key+'.csv'));orders=pd.read_parquet(private/(key+'_orders.parquet'));hold=private/(key+'_holdings.parquet');d=orders.units_after-orders.units_before
   ok=sha(root/(key+'.csv'))==r['nav_sha256'] and sha(private/(key+'_orders.parquet'))==r['orders_sha256'] and sha(hold)==r['holdings_sha256']
   ok=ok and not ((d>1e-10)&(~orders.can_buy|~orders.current_member)).any() and not ((d< -1e-10)&~orders.can_sell).any()
   if r['failures']:ok=ok and pd.to_datetime(nav.date).max()<pd.Timestamp(r['failures'][0]['date'])
   checks.append(dict(scenario=scenario,account=key,passed=bool(ok),valuation_blocked=bool(r['failures'])))
 save_json(OUT/'manifests/sensitivity_validation.json',dict(status='PASS' if len(checks)==32 and all(x['passed'] for x in checks) else 'FAIL',checks=checks))
 print('sensitivity audit',len(checks),all(x['passed'] for x in checks))
if __name__=='__main__':main()
