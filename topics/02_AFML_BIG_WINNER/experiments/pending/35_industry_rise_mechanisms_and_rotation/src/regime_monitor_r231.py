"""Explicit-date historical state monitor; never a model or trading decision."""
from common import *
import pandas as pd
import argparse

def snapshot(as_of,clock):
 if clock not in ['signal_close','prior_close']:raise ValueError('explicit supported clock required')
 source=ROOT/'outputs/r195/market_regimes.parquet';receipt=json.loads((ROOT/'outputs/r195/verification.json').read_text());assert sha(source)==receipt['outputs']['market_regimes.parquet'],'state source hash mismatch';s=pd.read_parquet(source);date=pd.Timestamp(as_of)
 if date!=date.normalize() or date.tz is not None:raise ValueError('date-only as-of required')
 if date>s.index.max():raise ValueError('as-of beyond frozen state coverage')
 if clock=='signal_close':
  if date not in s.index:raise ValueError('requested signal date missing; no stale fallback')
  chosen=date
 else:
  prior=s.index[s.index<date]
  if len(prior)==0:raise ValueError('no prior observed trading close')
  chosen=prior[-1]
 row=s.loc[chosen];known=pd.notna(row.regime);dummies={name:int(row.regime==name) for name in ['down_high','up_low','up_high']} if known else None
 result=dict(schema='ep35.regime_research_monitor.v1',as_of=str(date.date()),clock=clock,state_date=str(chosen.date()),known_at_proxy=str(chosen.date()),known_at_precision='date only; usable after market close, no first-publication timestamp certification',source_last_date=str(s.index.max().date()),regime=row.regime if known else None,state_status='known_historical_proxy' if known else 'unknown_insufficient_history',features={k:float(row[k]) if pd.notna(row[k]) else None for k in ['trend63','vol21','prior_vol_median']},dummy_reference='down_low',state_dummies=dummies,model_eligibility='not_established_by_market_state',prediction=None,adoption=False,production_enabled=False,strict_pit=False,interpretation='historical market state only; not economic phase, calibrated probability, recommendation or current live signal',source=dict(path=str(source.relative_to(ROOT)),sha256=sha(source)))
 return result

def write_snapshot(data,dest):
 content=json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n';dest=Path(dest)
 if dest.exists():
  if dest.read_text()!=content:raise ValueError('refuse to overwrite a different research snapshot')
  return 'unchanged'
 dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(content);return 'created'

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--as-of',required=True);parser.add_argument('--clock',required=True,choices=['signal_close','prior_close']);parser.add_argument('--output',required=True);args=parser.parse_args();print(write_snapshot(snapshot(args.as_of,args.clock),args.output))
