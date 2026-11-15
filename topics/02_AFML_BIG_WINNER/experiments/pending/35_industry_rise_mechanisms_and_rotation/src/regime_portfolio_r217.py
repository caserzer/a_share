from common import *
import pandas as pd
import regime_portfolio_engine_r217 as engine

def run():
 out=ROOT/'outputs/r217';out.mkdir(exist_ok=True);source=ROOT/'outputs/r202/scores.parquet';p=pd.read_parquet(source);p['family']='macro_lag'+p.lag.astype(str);p['cohort']=p.family;p['objective']='frozen_score';p['task']='return';p['horizon']=0;p['prediction']=p.score;inputs=[source]
 panels=[]
 for family,path in [('core','outputs/r158/evaluation/data/monthly_panel.parquet'),('l1','outputs/r158/evaluation/data/l1_monthly_panel.parquet')]:
  inputs.append(ROOT/path);q=pd.read_parquet(ROOT/path);q=q[KEY+['date','mom60']].copy();panels.append(q)
 panel=pd.concat(panels,ignore_index=True);assert not panel.duplicated(KEY+['date']).any()
 p=p.merge(panel,on=KEY+['date'],how='left',validate='many_to_one');assert p.mom60.notna().all()
 original=['family','objective','cohort','method'];mapping=p[original].drop_duplicates();mapping['mapped_cohort']=mapping[original].agg('__'.join,axis=1);mapping.to_csv(out/'mapping.csv',index=False)
 p['original_cohort']=p.cohort;p['original_method']=p.method;p['cohort']=p[original].agg('__'.join,axis=1);p['method']=p.variant
 m=p[p.variant.eq('base')].copy();m['method']='momentum';m['prediction']=m.mom60;p=pd.concat([p,m],ignore_index=True);p.to_parquet(out/'mapped_predictions.parquet',index=False)
 price_paths=[ROOT/'outputs/r129/daily_2026-10-21.parquet',ROOT/'data/l1_daily.parquet'];inputs+=price_paths
 frames=[pd.read_parquet(x) for x in price_paths];prices=pd.concat(frames,ignore_index=True);assert not prices.duplicated(KEY+['date']).any();prices.to_parquet(out/'combined_prices.parquet',index=False)
 js(out/'mapping_receipt.json',dict(status='PASS',rows=len(p),groups=len(mapping),inputs={str(x):sha(x) for x in inputs},outputs={x:sha(out/x) for x in ['mapped_predictions.parquet','combined_prices.parquet','mapping.csv']},code_sha256=sha(__file__)))
 engine.run()
if __name__=='__main__':run()
