"""Replay frozen event studies on corrected daily baskets without changing reports."""
import shutil
import pandas as pd
from common import *
import events_r26,horizon_prices_r91,unknown_controls_r26

def run():
 out=ROOT/'outputs/r144';root=out/'evaluation';cache=root/'cache'
 paths=['data/r24_source_exclusion_overlay.parquet','outputs/r11/receipt.json','outputs/r89/paired_events.parquet','protocols/r26.json','protocols/r91.json','data/r14_industry_events.parquet','protocols/r26_control_sensitivity.json']
 for rel in paths:
  dst=root/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,dst)
 ep24='24_conditional_return_distribution_exploration';link=root.parent/ep24
 if not link.exists():link.symlink_to(ROOT.parent/ep24,target_is_directory=True)
 for rel in ['forecast_v5/CSI_ALL.parquet','extension_v2/products/assignments.parquet']:
  dst=cache/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(CACHE/rel,dst)
 source=ROOT/'outputs/r129/daily_2026-10-21.parquet';shutil.copyfile(source,cache/'forecast_v5/daily_industries.parquet')
 for mod,round_ in [(events_r26,26),(horizon_prices_r91,91),(unknown_controls_r26,26)]:
  (root/f'outputs/r{round_}').mkdir(parents=True,exist_ok=True);mod.ROOT=root;mod.CACHE=cache;mod.run()
 pairs={};metrics=['pre20','pre60','reaction','post20','post60']
 for name,rel,keys in [('context','data/r26_non_event_context.parquet',KEY+['date']),('events','data/r26_industry_events.parquet',KEY+['signal_date','fiscal_year']),('horizon','outputs/r91/industry_events.parquet',KEY+['signal_date','publication_year'])]:
  a=pd.read_parquet(ROOT/rel);b=pd.read_parquet(root/rel);p=a.merge(b,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');p.to_parquet(out/f'{name}_pairs.parquet',index=False);g=p[p._merge.eq('both')];changes={}
  for c in metrics+(['quintile'] if name!='horizon' else [])+(['control_'+x for x in metrics]+['matched_'+x for x in metrics] if name=='events' else []):
   x=g[c+'_old'];y=g[c+'_new'];same=np.isclose(x,y,atol=1e-12,rtol=1e-10,equal_nan=True);changes[c]=dict(changed=int((~same).sum()),known_to_unknown=int((x.notna()&y.isna()).sum()),unknown_to_known=int((x.isna()&y.notna()).sum()),max_abs=float((x-y).abs().max()))
  pairs[name]=dict(old=len(a),new=len(b),added=int(p._merge.eq('right_only').sum()),removed=int(p._merge.eq('left_only').sum()),changes=changes)
 pd.testing.assert_frame_equal(pd.read_parquet(ROOT/'data/r26_mapped_report_events.parquet'),pd.read_parquet(root/'data/r26_mapped_report_events.parquet'))
 for rel in ['outputs/r91/mapped_pairs.parquet','outputs/r91/company_events.parquet']:
  pd.testing.assert_frame_equal(pd.read_parquet(ROOT/rel),pd.read_parquet(root/rel))
 js(out/'summary.json',dict(comparisons=pairs,unchanged='all report event mappings, fiscal-year revisions and company aggregation',reads={str(p):sha(p) for p in [ROOT/x for x in paths]+[source,Path(__file__),ROOT/'protocols/r144.json',ROOT/'src/events_r26.py',ROOT/'src/horizon_prices_r91.py']},quality='Historical-proxy descriptive timing, not predictive acceptance'))
 print(json.dumps(pairs,default=str))
if __name__=='__main__':run()
