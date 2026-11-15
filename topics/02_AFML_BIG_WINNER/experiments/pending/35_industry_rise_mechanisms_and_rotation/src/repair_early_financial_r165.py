"""Re-evaluate R03/R07 financial definitions with corrected price history."""
import shutil
import pandas as pd
import evaluate_r03,financial_delay_r07
from common import *

def run():
 out=ROOT/'outputs/r165';root=out/'evaluation';out.mkdir(parents=True,exist_ok=True)
 paths=['data/financial_archive_all_market.parquet','data/industry_financial_factors.parquet','outputs/r03/archive_receipt.json','protocols/r03.json','protocols/r07.json','src/supplement_financials.py','src/evaluate_r01.py'];sources={x:ROOT/x for x in paths};sources['data/monthly_panel.parquet']=ROOT/'outputs/r130/monthly_panel.parquet'
 for rel,p in sources.items():
  dst=root/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
 panel=pd.read_parquet(root/'data/monthly_panel.parquet');panel=panel[panel.era.eq('SW2021')&panel.date.between('2026-04-01','2026-09-30')];old=pd.read_parquet(ROOT/'data/financial_monthly_panel.parquet');assert set(panel.date)==set(old.date);industry=pd.read_parquet(root/'data/industry_financial_factors.parquet');d=panel.merge(industry,on=KEY+['date'],how='left',suffixes=('','_financial'),validate='one_to_one');d.to_parquet(root/'data/financial_monthly_panel.parquet',index=False);(root/'outputs/r07').mkdir(parents=True,exist_ok=True)
 for mod in [evaluate_r03,financial_delay_r07]:mod.ROOT=root;mod.run()
 pd.testing.assert_frame_equal(pd.read_parquet(ROOT/'data/r07_industry_factors.parquet'),pd.read_parquet(root/'data/r07_industry_factors.parquet'))
 comparisons={}
 for name,rel,keys in [('r03','outputs/r03/date_metrics.csv',['era','level','date','horizon','method']),('r07','outputs/r07/date_metrics.csv',['level','date','delay','cohort','method','horizon']),('coverage','outputs/r07/coverage.csv',['level','date','delay'])]:
  a=pd.read_csv(ROOT/rel);b=pd.read_csv(root/rel);p=a.merge(b,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');p.to_csv(out/f'{name}_comparison.csv',index=False);g=p[p._merge.eq('both')];changes={}
  for c in a.select_dtypes('number').columns:
   if c in keys:continue
   x=g[c+'_old'];y=g[c+'_new'];changes[c]=dict(changed=int((~np.isclose(x,y,atol=1e-12,rtol=1e-10,equal_nan=True)).sum()),max_abs=float((x-y).abs().max()))
  comparisons[name]=dict(old=len(a),new=len(b),added=int(p._merge.eq('right_only').sum()),removed=int(p._merge.eq('left_only').sum()),changes=changes)
 js(out/'comparison.json',comparisons);js(out/'receipt.json',dict(status='PASS',reads={str(p):sha(p) for p in list(sources.values())+[ROOT/'data/r07_industry_factors.parquet',ROOT/'data/financial_monthly_panel.parquet',ROOT/'protocols/r165.json',ROOT/'src/evaluate_r03.py',ROOT/'src/financial_delay_r07.py',Path(__file__)]},financial_factor_values_unchanged=True,original_protocols_preserved=True,adoption=False));print(json.dumps(comparisons,default=str,indent=2))
if __name__=='__main__':run()
