"""Read exact-date historical calibration outputs; no fit, action or future labels."""
from common import *
import argparse,re
import pandas as pd
FIELDS=['era','level','industry_code','date','year','variant','monthly_probability','daily_probability']

def load_sources(root=ROOT):
 root=Path(root);manifest=json.loads((root/'outputs/r299/sources.json').read_text())
 for name,digest in manifest.items():
  p=(root/name).resolve()
  if not p.is_relative_to(root.resolve()) or not p.is_file() or sha(p)!=digest:raise ValueError('source missing or changed: '+name)
 if json.loads((root/'outputs/r295/independent_verification.json').read_text()).get('status')!='PASS':raise ValueError('source verification not passed')
 return pd.read_parquet(root/'outputs/r295/predictions.parquet',columns=FIELDS),json.loads((root/'outputs/r298/probability_use_contract.json').read_text()),manifest

def project(data,as_of):
 if not isinstance(as_of,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',as_of):raise ValueError('YYYY-MM-DD date required')
 date=pd.Timestamp(as_of)
 if pd.isna(date):raise ValueError('valid date required')
 result=data.loc[data.date.eq(date),FIELDS].sort_values(['era','level','industry_code','variant']).copy();result['date']=result.date.dt.strftime('%Y-%m-%d')
 return result

def read(as_of,root=ROOT):
 data,contract,sources=load_sources(root);rows=project(data,as_of)
 return dict(schema='ep35.reversal_probability_comparison.v1',as_of=as_of,status='historical_exact_date_records' if len(rows) else 'no_exact_date_output',scope='Core F/F reversal20 qualified archived folds only; all16 research scope is not replaced',quality='Historical-proxy',retrospective=True,strict_pit=False,production_enabled=False,adoption=False,future_outcomes_exposed=False,calibration_interpretation={k:contract[k] for k in ['monthly_probability','daily_probability','action_equivalence']},source_hashes=sources,rows=rows.to_dict('records'))
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--as-of',required=True);args=parser.parse_args();print(json.dumps(clean(read(args.as_of)),ensure_ascii=False,allow_nan=False))
