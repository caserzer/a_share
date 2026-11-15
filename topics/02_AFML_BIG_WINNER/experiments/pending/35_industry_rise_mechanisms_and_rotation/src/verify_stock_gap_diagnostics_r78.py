import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r78';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h
 paths={Path(p).stem:Path(p) for p in rec['price_partitions']}
 for p,h in rec['price_partitions'].items():assert sha(p)==h
 rows=pd.DataFrame(json.loads((out/'gap_rows.json').read_text()));rows['origin']=pd.to_datetime(rows.origin);source=pd.read_parquet(ROOT/'outputs/r77/stock_interval_audit.parquet');bad=source[~(source.price_valid&source.chain_stable)];keys=['method','origin','security_id'];assert set(map(tuple,rows[keys].values))==set(map(tuple,bad[keys].values));calendar=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index);checks=0
 for sid,g in rows.groupby('security_id'):
  raw=pd.read_parquet(paths[sid]).set_index('date');lookup=raw.to_dict('index');memo={}
  for x in g.to_dict('records'):
   key=(x['entry'],x['exit'])
   if key not in memo:
    counts={k:0 for k in ['absent_dates','raw_close_missing','raw_close_nonpositive','close_conflict_true','close_conflict_unknown','adjusted_close_missing','adjusted_close_nonpositive','chain_missing']};chains=set();dates=calendar[(calendar>=pd.Timestamp(x['entry']))&(calendar<=pd.Timestamp(x['exit']))]
    for day in dates:
     z=lookup.get(day)
     if z is None:counts['absent_dates']+=1;counts['chain_missing']+=1;continue
     a=z['close'];b=z['qfq_close'];flag=z['close_conflict'];chain=z['factor_chain_id']
     counts['raw_close_missing']+=int(pd.isna(a));counts['raw_close_nonpositive']+=int(pd.notna(a) and a<=0);counts['adjusted_close_missing']+=int(pd.isna(b));counts['adjusted_close_nonpositive']+=int(pd.notna(b) and b<=0);counts['close_conflict_unknown']+=int(pd.isna(flag));counts['close_conflict_true']+=int(pd.notna(flag) and flag==True);counts['chain_missing']+=int(pd.isna(chain))
     if pd.notna(chain):chains.add(chain)
    counts['observed_chain_count']=len(chains);memo[key]=counts
   assert all(x[k]==v for k,v in memo[key].items());checks+=1
 summary=json.loads((out/'summary.json').read_text());unique=rows.drop_duplicates(['origin','security_id']);assert len(rows)==summary['failed_method_stock_rows'] and len(unique)==summary['distinct_stock_origins'] and rows.security_id.nunique()==summary['affected_securities']
 for k,v in summary['method_rows_by_reason'].items():assert int(rows[k].gt(0).sum())==v
 for k,v in summary['distinct_stock_origins_by_reason'].items():assert int(unique[k].gt(0).sum())==v
 assert int(rows.observed_chain_count.gt(1).sum())==summary['multi_chain_method_rows']
 concentration=json.loads((out/'security_concentration.json').read_text());counts=unique.groupby('security_id').size().to_dict();assert {x['security_id']:x['distinct_origins'] for x in concentration}==counts
 assert abs(sum(sorted(counts.values(),reverse=True)[:10])/len(unique)-summary['top10_share_of_distinct_stock_origins'])<1e-12
 js(out/'verification.json',dict(status='PASS',all_failed_rows_replayed=checks,source_partitions=len(paths),deduplicated_stock_origins=len(unique),no_source_modified=True));print('R78 VERIFIED',checks,len(paths))
if __name__=='__main__':run()
