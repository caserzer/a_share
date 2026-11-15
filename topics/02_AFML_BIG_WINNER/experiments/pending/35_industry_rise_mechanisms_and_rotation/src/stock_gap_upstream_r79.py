"""Check whether missing normalized dates survive in frozen upstream inputs."""
import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r79';inp=out/'missing_dates.json';d=pd.DataFrame(json.loads(inp.read_text())).drop_duplicates(['security_id','date']);d['date']=pd.to_datetime(d.date)
 r=json.loads((out/'receipt.json').read_text());release=Path(next(iter(r['price_partitions']))).parents[2]
 rows=[];reads={};missing=[]
 for label,base in [('immediate_input',release/'inputs/normalized/prices'),('baseline_input',release/'inputs/inputs/baseline/normalized/prices')]:
  for sid,g in d.groupby('security_id'):
   p=base/f'{sid}.parquet'
   if not p.is_file():missing.append(dict(layer=label,security_id=sid,path=str(p)));continue
   reads[str(p)]=sha(p);f=pd.read_parquet(p);assert 'date' in f.columns
   found=set(pd.to_datetime(f.date)).intersection(g.date)
   for date in sorted(found):rows.append(dict(layer=label,security_id=sid,date=date))
 js(out/'upstream_matches.json',rows)
 js(out/'upstream_receipt.json',dict(reads={str(inp):sha(inp),str(Path(__file__)):sha(Path(__file__))},source_partitions=reads,missing_partitions=missing,unique_stock_dates=len(d),matches_by_layer={k:sum(x['layer']==k for x in rows) for k in ['immediate_input','baseline_input']},limitation='frozen normalized upstream inputs only; does not establish absence from original vendor payload or trading suspension'))
 print('UPSTREAM',len(reads),'partitions',len(rows),'matches',len(missing),'absent partitions')
if __name__=='__main__':run()
