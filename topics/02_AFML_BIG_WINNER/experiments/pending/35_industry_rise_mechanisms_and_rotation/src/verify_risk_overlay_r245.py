from common import *
import pandas as pd
from risk_archive_overlay_r245 import capture,state_for
from research_archive_cli_r239 import check
import tempfile,shutil

def independent(g,market,date):
 q=g[g.date.le(date)].sort_values('date').copy();state='unknown';reason='no_exact_date_price';blank=dict(risk_state=state,risk_reason=reason,risk_peak_date=pd.NaT,risk_drawdown=np.nan,risk_breach_date=pd.NaT,risk_days_since_breach=np.nan,risk_segment_start=pd.NaT)
 if q.empty or not q.date.eq(date).any():return blank
 ix=pd.DatetimeIndex(market.index).get_indexer(q.date);rel=q.nav.to_numpy()/market.reindex(q.date).to_numpy();valid=np.isfinite(rel)&(rel>0)&(ix>=0)&q.block.notna().to_numpy()
 if 'known_at' in q:
  clock=pd.to_datetime(q.known_at);valid&=clock.notna().to_numpy()&clock.le(date).to_numpy()
  if pd.isna(clock.iloc[-1]) or clock.iloc[-1]>date:return dict(blank,risk_reason='recorded_clock_unavailable')
 if not valid[-1]:return dict(blank,risk_reason='invalid_exact_date_price')
 block=q.block.to_numpy();boundary=np.ones(len(q),dtype=bool)
 if len(q)>1:boundary[1:]=~valid[1:]|~valid[:-1]|(np.diff(ix)!=1)|(block[1:]!=block[:-1])
 start=int(np.flatnonzero(boundary)[-1]);vals=rel[start:];peak=vals.max();pi=start+int(np.flatnonzero(vals==peak)[-1]);cross=np.flatnonzero(rel[pi:]/peak<=.92);bi=pi+int(cross[0]) if len(cross) else None
 return dict(risk_state='clear' if bi is None else 'ongoing_left_boundary' if pi==start else 'ongoing',risk_reason=None,risk_peak_date=q.date.iloc[pi],risk_drawdown=float(rel[-1]/peak-1),risk_breach_date=q.date.iloc[bi] if bi is not None else pd.NaT,risk_days_since_breach=int(ix[-1]-ix[bi]) if bi is not None else np.nan,risk_segment_start=q.date.iloc[start])
def run():
 out=ROOT/'outputs/r245';market=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close;prices=pd.concat([pd.read_parquet(ROOT/'outputs/r129/daily_2026-10-21.parquet').assign(clock_source=True),pd.read_parquet(ROOT/'data/l1_daily.parquet').assign(clock_source=False)],ignore_index=True);lookup={k:g.drop(columns='known_at') if not g.clock_source.iloc[0] else g for k,g in prices.groupby(KEY)};checks=0;rows=0
 for date in ['2026-08-31','2026-09-30']:
  archive=ROOT/f'outputs/r239/{date}';dest=out/date
  # September's initial CLI used workspace-relative paths; retain its frozen request.
  arg=archive if date=='2026-08-31' else Path('topics/02_AFML_BIG_WINNER/experiments/pending/35_industry_rise_mechanisms_and_rotation/outputs/r239/2026-09-30')
  result=capture(arg,dest);assert result in ['created','unchanged'];assert capture(arg,dest)=='unchanged';check(dest)
  original=pd.read_parquet(archive/'historical_score_view.parquet');annotated=pd.read_parquet(dest/'annotated_scores.parquet');pd.testing.assert_frame_equal(original,annotated[original.columns]);rows+=len(original)
  saved=pd.read_parquet(dest/'industry_risk_states.parquet')
  for r in saved.to_dict('records'):
   key=tuple(r[k] for k in KEY);expected=independent(lookup[key],market,pd.Timestamp(date))
   for k,v in expected.items():
    if pd.isna(v):assert pd.isna(r[k])
    elif isinstance(v,float):assert np.isclose(v,r[k],atol=1e-14)
    else:assert v==r[k]
    checks+=1
 # Future suffix perturbation, exact-date absence and publication clock refusal.
 dates=pd.bdate_range('2020-01-01',periods=6);m=pd.Series([1.]*6,index=dates);g=pd.DataFrame(dict(date=dates,nav=[1,1.1,.99,.98,.8,2],block=[1]*6,known_at=dates));cut=dates[3];a=state_for(g,m,cut);modified=g.copy();modified.loc[modified.date>cut,'nav']=[1000,.0001];mm=m.copy();mm.loc[mm.index>cut]=[.00001,10000];b=state_for(modified,mm,cut)
 for k in a:assert pd.isna(a[k]) and pd.isna(b[k]) or a[k]==b[k]
 assert state_for(g[g.date.ne(cut)],m,cut)['risk_reason']=='no_exact_date_price'
 late=g.copy();late.loc[late.date.eq(cut),'known_at']=dates[4];assert state_for(late,m,cut)['risk_reason']=='recorded_clock_unavailable'
 # A valid date prefix must still record an anchor as left-boundary rather than proven history.
 x=g.iloc[:2].copy();x['nav']=[1,.9];assert state_for(x,m,dates[1])['risk_state']=='ongoing_left_boundary'
 with tempfile.TemporaryDirectory() as temp:
  dest=Path(temp)/'tampered';shutil.copytree(out/'2026-08-31',dest);(dest/'snapshot.json').write_text('{}')
  try:check(dest)
  except AssertionError:pass
  else:raise AssertionError('tamper not detected')
  try:capture(ROOT/'outputs/r239/2026-09-30',out/'2026-08-31')
  except ValueError:pass
  else:raise AssertionError('conflicting request accepted')
 js(out/'independent_verification.json',dict(status='PASS',state_field_checks=checks,unchanged_score_rows=rows,snapshot_dates=2,idempotence_checks=2,boundary_checks=4,rejection_checks=2,code_sha256=sha(Path(__file__)),adoption=False));print('PASS',checks,rows)
if __name__=='__main__':run()
