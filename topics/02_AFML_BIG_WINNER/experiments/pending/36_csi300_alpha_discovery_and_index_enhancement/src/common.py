from pathlib import Path
import hashlib,json
import pandas as pd
EP=Path(__file__).resolve().parents[1]
PRIVATE=EP/'private'; OUT=EP/'outputs'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save_json(p,obj):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str)+'\n')
def protocol():return json.loads((EP/'configs/protocol.json').read_text())
def release():
 r=json.loads((EP.parent/'30_pit_data_foundation_v1/outputs/pit_v5/release.json').read_text());root=Path(r['path'])
 assert sha(root/'FULL_MANIFEST.json')==r['release_id']
 return root,{x['relative_path']:x for x in json.loads((root/'FULL_MANIFEST.json').read_text())}
def read_sealed(root,manifest,name):
 assert sha(root/name)==manifest[name]['sha256'],name
 return pd.read_parquet(root/name)
def zscore(s,min_n=100):
 n=s.count();sd=s.std(ddof=0)
 return (s-s.mean())/sd if n>=min_n and sd>1e-12 else s*float('nan')
def signal_days(days):
 s=pd.Series(days,index=days).groupby(days.to_period('W-FRI')).max()
 # End-of-dataset midweek is not a completed weekly signal.
 if days[-1].dayofweek<4:s=s.iloc[:-1]
 return pd.DatetimeIndex(s)
