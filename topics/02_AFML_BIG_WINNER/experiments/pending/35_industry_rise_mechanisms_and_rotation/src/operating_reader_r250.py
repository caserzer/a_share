"""Explicit-date, immutable historical operating diagnostics; never model inference."""
from common import *
import pandas as pd
import argparse,tempfile
from research_archive_cli_r239 import seal,check

def capture(as_of,output):
 date=pd.Timestamp(as_of)
 if pd.isna(date) or date.tz is not None or date!=date.normalize():raise ValueError('date-only required')
 entrypath=ROOT/'outputs/r250/research_entry.json';entry=json.loads(entrypath.read_text())
 for route in entry['routes'].values():assert sha(ROOT/route['path'])==route['sha256'],'changed source'
 output=Path(output).resolve();request=dict(action='operating_snapshot',as_of=str(date.date()),entry_sha256=sha(entrypath),code_sha256=sha(Path(__file__)))
 if output.exists():
  if check(output)['request']!=request:raise ValueError('conflicting existing request')
  return 'unchanged'
 source=ROOT/entry['routes']['annotated_industry_evidence']['path'];d=pd.read_parquet(source,filters=[('snapshot','==',date)])
 output.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(dir=output.parent) as temp:
  stage=Path(temp)/'snapshot';stage.mkdir();d.to_parquet(stage/'operating_diagnostics.parquet',index=False);js(stage/'snapshot.json',dict(as_of=str(date.date()),status='historical_exact_date_diagnostics' if len(d) else 'no_exact_date_evidence',rows=len(d),industry_identities=len(d[KEY].drop_duplicates()),no_stale_fallback=True,scope='Retrospective same-cutoff derived accounting proxy; not current-quarter or certified PIT; no forecast or action score',feature_dictionary=entry['routes']['dictionary'],historical_training_assessment=entry['routes']['training_gates'],training_assessment_scope='Frozen2026 annual gates, not recomputed for arbitrary requested future years',adoption=False,production_enabled=False))
  js(stage/'verification.json',dict(status='PASS',inputs={str(p):sha(p) for p in [entrypath,source,Path(__file__)]},outputs={f:sha(stage/f) for f in ['operating_diagnostics.parquet','snapshot.json']}));seal(stage,request);stage.rename(output)
 return 'created'
if __name__=='__main__':
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--as-of',required=True);a.add_argument('--output',required=True);args=a.parse_args();print(capture(args.as_of,args.output))
