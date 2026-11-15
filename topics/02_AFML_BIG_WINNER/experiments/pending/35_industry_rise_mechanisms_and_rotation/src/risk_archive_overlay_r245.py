"""Read-only retrospective price-risk annotation, never an exit gate."""
from common import *
import pandas as pd
import argparse,tempfile
from research_archive_cli_r239 import check,seal
PRICE_SOURCES=['outputs/r129/daily_2026-10-21.parquet','data/l1_daily.parquet']
def state_for(g,market,asof):
 date=pd.Timestamp(asof);g=g[g.date.le(date)].sort_values('date').copy();result=dict(risk_state='unknown',risk_reason='no_exact_date_price',risk_peak_date=pd.NaT,risk_drawdown=np.nan,risk_breach_date=pd.NaT,risk_days_since_breach=np.nan,risk_segment_start=pd.NaT,risk_recorded_known_at=pd.NaT,risk_clock='historical_proxy_no_first_release_clock')
 if g.empty or not g.date.eq(date).any():return result
 cal=pd.DatetimeIndex(market.loc[:date].index);g['idx']=cal.get_indexer(g.date);g['relative']=g.nav.to_numpy()/market.reindex(g.date).to_numpy();g['valid']=g.idx.ge(0)&np.isfinite(g.relative)&g.relative.gt(0)&g.block.notna()
 if 'known_at' in g:
  clock=pd.to_datetime(g.known_at);g['valid'] &=clock.notna()&clock.le(date);result['risk_clock']='recorded_known_at_checked_not_strict_PIT';result['risk_recorded_known_at']=clock.iloc[-1]
  if pd.isna(clock.iloc[-1]) or clock.iloc[-1]>date:result['risk_reason']='recorded_clock_unavailable';return result
 if not g.valid.iloc[-1]:result['risk_reason']='invalid_exact_date_price';return result
 prev=None;peak=None;breach=None
 for row in g.itertuples():
  reset=prev is None or not row.valid or not prev.valid or row.block!=prev.block or row.idx!=prev.idx+1
  if reset:peak=None;breach=None
  if row.valid:
   if peak is None:peak=row.relative;peak_date=row.date;start=row.date;peak_i=row.idx
   elif row.relative>=peak:peak=row.relative;peak_date=row.date;peak_i=row.idx;breach=None
   elif breach is None and row.relative/peak<=.92:breach=(row.date,row.idx)
  prev=row
 result.update(risk_state='clear' if breach is None else 'ongoing_left_boundary' if peak_date==start else 'ongoing',risk_reason=None,risk_peak_date=peak_date,risk_drawdown=float(g.relative.iloc[-1]/peak-1),risk_breach_date=breach[0] if breach else pd.NaT,risk_days_since_breach=int(g.idx.iloc[-1]-breach[1]) if breach else np.nan,risk_segment_start=start)
 return result

def capture(archive,dest):
 archive=Path(archive);dest=Path(dest);check(archive);snap=json.loads((archive/'snapshot.json').read_text());date=pd.Timestamp(snap['as_of']);scores=pd.read_parquet(archive/'historical_score_view.parquet');assert scores.date.eq(date).all()
 sources=[ROOT/x for x in PRICE_SOURCES]+[CACHE/'forecast_v5/CSI_ALL.parquet'];inputs={str(p):sha(p) for p in sources+[archive/'manifest.json',ROOT/'protocols/r245.json',Path(__file__),ROOT/'src/research_archive_cli_r239.py']};request=dict(action='price_risk_overlay',as_of=str(date.date()),inputs=inputs)
 if dest.exists():
  if check(dest)['request']!=request:raise ValueError('conflicting existing overlay')
  return 'unchanged'
 market=pd.read_parquet(sources[-1]).close
 if date not in market.index:raise ValueError('not an exact market date')
 rows=[];found=set()
 for path in sources[:-1]:
  data=pd.read_parquet(path,filters=[('date','<=',date)])
  for key,g in data.groupby(KEY):
   assert key not in found;found.add(key);rows.append(dict(zip(KEY,key),**state_for(g,market,date),risk_source=str(path.relative_to(ROOT)),risk_source_sha256=inputs[str(path)]))
 for key in scores[KEY].drop_duplicates().itertuples(index=False,name=None):
  if key not in found:rows.append(dict(zip(KEY,key),risk_state='unknown',risk_reason='no_source_history',risk_source=None,risk_source_sha256=None))
 states=pd.DataFrame(rows);annotated=scores.merge(states,on=KEY,how='left',validate='many_to_one');assert len(annotated)==len(scores);pd.testing.assert_frame_equal(scores.reset_index(drop=True),annotated[scores.columns].reset_index(drop=True))
 dest.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(dir=dest.parent) as temp:
  stage=Path(temp)/'overlay';stage.mkdir();states.to_parquet(stage/'industry_risk_states.parquet',index=False);annotated.to_parquet(stage/'annotated_scores.parquet',index=False)
  js(stage/'snapshot.json',dict(schema='ep35.price_risk_overlay.v1',as_of=str(date.date()),source_archive=str(archive),score_rows=len(scores),source_price_identities=len(states),state_counts=states.risk_state.value_counts().to_dict(),score_row_state_counts=annotated.risk_state.value_counts().to_dict(),scope='Observed price process only; clear is not low-risk; source-prefix clocks do not certify strict PIT; L1 proxy source aggregation limitations remain',no_future_episode_catalogue=True,adoption=False,production_enabled=False,exit_gate_enabled=False))
  js(stage/'verification.json',dict(status='PASS',inputs=inputs,score_rows_unchanged=True,outputs={f:sha(stage/f) for f in ['industry_risk_states.parquet','annotated_scores.parquet','snapshot.json']}));seal(stage,request);stage.rename(dest)
 return 'created'
if __name__=='__main__':
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--archive',required=True);a.add_argument('--output',required=True);args=a.parse_args();print(capture(args.archive,args.output))
