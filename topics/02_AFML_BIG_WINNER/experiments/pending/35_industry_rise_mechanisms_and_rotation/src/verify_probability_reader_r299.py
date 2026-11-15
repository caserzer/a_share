from common import *
import pandas as pd
import tempfile,shutil,subprocess,sys
from reversal_probability_reader_r299 import read,load_sources,project,FIELDS

def run():
 out=ROOT/'outputs/r299';data,_,_=load_sources();source=pd.read_parquet(ROOT/'outputs/r295/predictions.parquet');assert len(data)==len(source)
 total=0
 for day,g in source.groupby('date'):
  actual=project(data,str(day.date()));expected=g[FIELDS].sort_values(['era','level','industry_code','variant']).copy();expected['date']=expected.date.dt.strftime('%Y-%m-%d');pd.testing.assert_frame_equal(actual.reset_index(drop=True),expected.reset_index(drop=True));total+=len(actual)
 for day in ['2026-09-30','2026-10-21','2030-01-01','2026-10-18']:
  result=read(day);assert result['future_outcomes_exposed'] is False
  assert all(set(row)==set(FIELDS) and row['date']==day for row in result['rows'])
  assert len(result['rows'])==int(source.date.eq(pd.Timestamp(day)).sum())
  js(out/('sample_'+day+'.json'),result)
 for invalid in ['2026-09','2026-09-30T00:00:00','2026-09-30Z','2026-02-30','latest']:
  try:project(data,invalid)
  except (ValueError,TypeError):pass
  else:raise AssertionError('invalid date accepted')
 with tempfile.TemporaryDirectory() as tmp:
  root=Path(tmp);manifest=json.loads((out/'sources.json').read_text());(root/'outputs/r299').mkdir(parents=True);shutil.copy2(out/'sources.json',root/'outputs/r299/sources.json')
  for name in manifest:
   p=root/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,p)
  target=root/'outputs/r295/predictions.parquet'
  with target.open('ab') as f:f.write(b'changed')
  try:read('2026-09-30',root)
  except ValueError:pass
  else:raise AssertionError('changed source accepted')
 cmd=[sys.executable,str(ROOT/'src/reversal_probability_reader_r299.py'),'--as-of','2026-09-30'];proc=subprocess.run(cmd,capture_output=True,text=True,check=True);actual=json.loads(proc.stdout);assert actual==read('2026-09-30')
 assert not set(['y','maturity20','linear']).intersection(FIELDS)
 js(out/'verification.json',dict(status='PASS',all_source_rows_checked=total,source_dates=source.date.nunique(),invalid_dates_rejected=5,changed_source_rejected=True,cli_rows=len(actual['rows']),future_fields_excluded=True,inputs={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'src/reversal_probability_reader_r299.py',ROOT/'src/verify_probability_reader_r299.py',out/'sources.json',ROOT/'protocols/r299.json']},adoption=False));print('VERIFIED',total,source.date.nunique(),len(actual['rows']))
if __name__=='__main__':run()
