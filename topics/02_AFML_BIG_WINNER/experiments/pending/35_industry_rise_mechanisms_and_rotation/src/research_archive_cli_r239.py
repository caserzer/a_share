"""Immutable explicit-date historical research archives; no live model invocation."""
from common import *
import pandas as pd
import argparse,tempfile,shutil
from archive_view_builder_r239 import build
from regime_monitor_r231 import snapshot

def seal(directory,request):
 files={p.name:sha(p) for p in Path(directory).iterdir() if p.is_file() and p.name!='manifest.json'};js(Path(directory)/'manifest.json',dict(request=request,files=files))
def check(directory):
 directory=Path(directory);m=json.loads((directory/'manifest.json').read_text())
 for name,digest in m['files'].items():assert sha(directory/name)==digest,'changed archive output'
 receipt=directory/'verification.json'
 if receipt.is_file():
  v=json.loads(receipt.read_text())
  for name,digest in v.get('inputs',{}).items():assert sha(name)==digest,'changed source input'
 return m

def capture(as_of,dest):
 date=pd.Timestamp(as_of)
 if date.tz is not None or date!=date.normalize():raise ValueError('date-only required')
 snapshot(as_of,'signal_close');snapshot(as_of,'prior_close');dest=Path(dest);request=dict(action='snapshot',as_of=str(date.date()),builder_sha256=sha(ROOT/'src/archive_view_builder_r239.py'))
 if dest.exists():
  m=check(dest)
  if m['request']!=request:raise ValueError('existing archive belongs to a different request')
  return 'unchanged'
 dest.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(dir=dest.parent) as temp:
  stage=Path(temp)/'snapshot';build(str(date.date()),stage);seal(stage,request);stage.rename(dest)
 return 'created'

def compare_frames(before,after):
 # Events are distinct observations; do not equate two events merely by industry/model.
 a=before[before.family_registry.ne('profit_events')];b=after[after.family_registry.ne('profit_events')];keys=['family_registry','source_round','model_slice','era','level','industry_code'];fields=['date','research_score','ranking_value','display_rank','slice_count'];q=a[keys+fields].merge(b[keys+fields],on=keys,how='outer',suffixes=('_before','_after'),indicator=True,validate='one_to_one');q['status']=q['_merge'].astype(str).map({'both':'matched_configuration','left_only':'missing_after','right_only':'new_after'});q=q.drop(columns='_merge');q['score_change']=q.research_score_after-q.research_score_before;q['rank_change']=q.display_rank_after-q.display_rank_before;q['model_year_changed']=pd.to_datetime(q.date_before).dt.year.ne(pd.to_datetime(q.date_after).dt.year)&q.status.eq('matched_configuration');return q

def compare(before,after,dest):
 before=Path(before);after=Path(after);check(before);check(after);bs=json.loads((before/'snapshot.json').read_text());as_=json.loads((after/'snapshot.json').read_text());assert pd.Timestamp(bs['as_of'])<pd.Timestamp(as_['as_of']),'dates must increase';dest=Path(dest);request=dict(action='compare',before_sha256=sha(before/'manifest.json'),after_sha256=sha(after/'manifest.json'),code_sha256=sha(__file__))
 if dest.exists():
  if check(dest)['request']!=request:raise ValueError('conflicting comparison output')
  return 'unchanged'
 a=pd.read_parquet(before/'historical_score_view.parquet');b=pd.read_parquet(after/'historical_score_view.parquet');q=compare_frames(a,b);events=pd.concat([a[a.family_registry.eq('profit_events')].assign(side='before'),b[b.family_registry.eq('profit_events')].assign(side='after')],ignore_index=True);af={x['family']:x for x in as_['families']};coverage=[dict(family=x['family'],before_rows=x['exact_date_rows'],after_rows=af[x['family']]['exact_date_rows'],before_status=x['status'],after_status=af[x['family']]['status']) for x in bs['families']]
 dest.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(dir=dest.parent) as temp:
  stage=Path(temp)/'comparison';stage.mkdir();q.to_parquet(stage/'changes.parquet',index=False);events.to_parquet(stage/'unpaired_events.parquet',index=False);js(stage/'coverage.json',coverage);js(stage/'summary.json',dict(before=bs['as_of'],after=as_['as_of'],status_counts=q.status.value_counts().to_dict(),unpaired_event_rows=len(events),market_state_before=bs['market_state']['regime'],market_state_after=as_['market_state']['regime'],scope='Retrospective configuration/industry changes, not parameter-identical attribution; ranks depend on changing universe; no outcome or action claim',adoption=False));js(stage/'verification.json',dict(status='PASS',inputs={str(before/'manifest.json'):sha(before/'manifest.json'),str(after/'manifest.json'):sha(after/'manifest.json'),str(Path(__file__)):sha(__file__)},scope='Source archives checked; exact outer join and separate events'));seal(stage,request);stage.rename(dest)
 return 'created'
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True);a=sub.add_parser('snapshot');a.add_argument('--as-of',required=True);a.add_argument('--output',required=True);b=sub.add_parser('compare');b.add_argument('--before',required=True);b.add_argument('--after',required=True);b.add_argument('--output',required=True);args=p.parse_args();print(capture(args.as_of,args.output) if args.action=='snapshot' else compare(args.before,args.after,args.output))
