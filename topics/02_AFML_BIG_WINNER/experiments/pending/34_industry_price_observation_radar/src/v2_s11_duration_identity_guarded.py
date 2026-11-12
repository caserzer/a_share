"""Integrated identity prototype, no signal or method-outcome inputs."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP, PRIOR, sha
from v2_path_probe03_symmetric_calendar_corrected import excursions as old_excursions, checks as old_checks


def excursions(y):
 y=np.asarray(y,float);assert np.isfinite(y).all()
 n=len(y);rows=[]
 if n<9:return rows
 def scale(t):return float(max(.002,2*np.median(abs(np.diff(y[t-8:t+1])))))
 low=8;eps=scale(low);active=False;seen=None;confirmed=None;peak=low;route=None;last_end=-1
 def record(end,breach,reason):
  return dict(start_i=low,visible_i=seen,confirm_i=confirmed,end_i=end,breach_i=breach,peak_i=peak,epsilon=eps,route=route,
   left_context_unknown=bool(low==8 and y[8]>y[0]),status='CONFIRMED' if confirmed is not None else 'UNCONFIRMED_INTERRUPTED' if breach is not None else 'RIGHT_UNKNOWN',
   right_open=breach is None,end_reason=reason,peak_log_gain=float(y[peak]-y[low]),final_log_gain=float(y[end]-y[low]))
 for i in range(9,n):
  if not active:
   if y[i]<=y[low]:low=i;eps=scale(low)
   elif y[i]-y[low]>=eps:
    active=True;seen=i;peak=i;confirmed=None;route='AMPLITUDE'
   if not active:
    ref=i-8
    if ref>=8 and ref>last_end and y[ref]<=min(y[ref-8:ref+1]):
     a=y[i-7:i-3];b=y[i-3:i+1]
     if (y[ref+1:i+1]>y[ref]).all() and np.median(b)-np.median(a)>=.002 and np.median(b)-y[ref]>=.002 and max(y[ref:i+1])-y[i]<scale(ref):
      low=ref;eps=scale(low);active=True;confirmed=i;route='DURATION8'
      seen=next(j for j in range(ref+1,i+1) if y[j]-y[ref]>=.002)
      peak=ref+int(np.argmax(y[ref:i+1]))
  if active:
   if y[i]>y[peak]:peak=i
   loss=y[i]<=y[low];drawdown=y[peak]-y[i]>=eps
   if loss or drawdown:
    rows.append(record(i-1,i,'REFERENCE_LOST' if loss else 'SCALE_DRAWDOWN'));last_end=i-1
    active=False;low=i;eps=scale(low);seen=None;confirmed=None;peak=low;route=None
   elif confirmed is None and i-low>=4 and (y[i-3:i+1]>y[low]).all() and y[i]-y[low]>=eps:confirmed=i
 if active:rows.append(record(n-1,None,None))
 return rows


def check_identity(y,rows):
 fields=['start_i','visible_i','confirm_i','end_i','breach_i','status','route']
 assert [{k:r[k] for k in fields} for r in rows]==[{k:r[k] for k in fields} for r in excursions(np.array(y)+2)]
 for j,r in enumerate(rows):
  assert r['start_i']<=r['visible_i']<=r['end_i']
  if r['confirm_i'] is not None:assert r['visible_i']<=r['confirm_i']<=r['end_i']
  if j:assert rows[j-1]['end_i']<r['start_i']


def main():
 out=EP/'outputs/v2_s11_duration_identity_guarded';out.mkdir(exist_ok=False)
 checks=[]
 for c in old_checks():
  y=c['log_prices'];rows=excursions(y);check_identity(y,rows)
  actual=sum(r['status']=='CONFIRMED' for r in rows)
  passed=actual==c['expected_confirmed']
  if c['path']=='long_gain_then_decline':passed=passed and len(rows)==1 and rows[0]['breach_i'] is not None
  if c['path']=='right_unknown':passed=passed and len(rows)==1 and rows[0]['status']=='RIGHT_UNKNOWN'
  if c['path']=='steady_left_unknown':passed=passed and rows[0]['left_context_unknown']
  checks.append(dict(name=c['path'],passed=bool(passed),processes=rows,log_prices=y))
 prior=np.array([.16,.12,.15,.09,.12,.06,.09,.03,0.]);mild=.003*np.arange(1,17)
 fixtures={
  'mild_duration':np.r_[prior,mild],
  'mild_lost':np.r_[prior,mild,0.],
  'mild_restart':np.r_[prior,mild,0.,.003*np.arange(1,17)],
  'strong_no_duplicate':np.r_[prior,.02*np.arange(1,17)],
  'old_low_then_plateau_then_rise':np.r_[prior,np.full(40,.01),.01+mild],
  'flat':np.zeros(45),
  'late_retracement':np.r_[prior,np.full(40,.01),[.012,.014,.016,.018,.05,.06,.04,.025]],
  'stationary_alternation':np.r_[prior,np.tile([.01,.03],16)],
 }
 for name,y in fixtures.items():
  rows=excursions(y);check_identity(y,rows);confirmed=[r for r in rows if r['status']=='CONFIRMED']
  if name=='mild_duration':passed=len(confirmed)==1 and confirmed[0]['route']=='DURATION8'
  elif name=='mild_lost':passed=len(confirmed)==1 and confirmed[0]['end_reason']=='REFERENCE_LOST'
  elif name=='mild_restart':passed=len(confirmed)==2 and confirmed[0]['end_i']<confirmed[1]['start_i']
  elif name=='strong_no_duplicate':passed=len(confirmed)==1
  elif name=='old_low_then_plateau_then_rise':passed=len(confirmed)==1 and confirmed[0]['route']=='DURATION8' and confirmed[0]['start_i']>=40
  else:passed=not confirmed
  checks.append(dict(name=name,passed=bool(passed),processes=rows,log_prices=y.tolist()))
 (out/'synthetic_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
 if not all(c['passed'] for c in checks):
  print(json.dumps({'status':'SEMANTIC_FAILURE','failed':[c['name'] for c in checks if not c['passed']]}));return
 casefile=EP/'outputs/v2_s09_mild_paths/selected_cases.csv';cases=pd.read_csv(casefile)
 rawfile=PRIOR/'daily_industries.parquet';raw=pd.read_parquet(rawfile,columns=['date','era','industry_code','block','nav']);raw=raw[raw.nav.gt(0)&raw.block.notna()].copy();raw['week']=raw.date.dt.to_period('W-SUN').astype(str);raw['y']=np.log(raw.nav)
 statefile=EP/'outputs/r00_v2_path_probe03_symmetric_calendar_corrected/weekly_evaluation_states.parquet';states=pd.read_parquet(statefile)
 rec=json.loads((PRIOR/'receipt.json').read_text());calpath=Path(next(k for k in rec['inputs'] if k.endswith('/calendar.parquet')));cal=pd.read_parquet(calpath);cal['week']=cal.date.dt.to_period('W-SUN').astype(str);dates=cal.groupby('week').date.max();wi={w:i for i,w in enumerate(dates.index)}
 records=[];summary=[];pathrows=[]
 for c in cases.itertuples():
  g=raw[raw.era.eq(c.era)&raw.industry_code.eq(c.industry_code)&raw.block.eq(c.block)&raw.date.le(pd.Timestamp(c.end))]
  w=g.groupby('week').y.median().reset_index();s=states[states.era.eq(c.era)&states.industry_code.eq(c.industry_code)&states.block.eq(c.block)]
  w=w.merge(s[['week','state']],on='week',validate='one_to_one');w=w[~w.state.eq('PARTIAL_WEEK_UNKNOWN')].copy();w['wi']=w.week.map(wi);w['date']=w.week.map(dates);w=w.sort_values('wi');w['run']=w.wi.diff().ne(1).cumsum();key=f'{c.era}/{c.industry_code}/{c.date}'
  for run,z in w.groupby('run'):
   z=z.reset_index(drop=True);y=z.y.to_numpy();z['case_key']=key;pathrows.append(z)
   for method,func in [('OLD',old_excursions),('D8_INTEGRATED',excursions)]:
    rows=func(y)
    if method=='D8_INTEGRATED':check_identity(y,rows)
    for row in rows:
     r=dict(row,case_key=key,method=method,run=int(run))
     for field in ['start','visible','confirm','end','breach']:
      idx=row[field+'_i'];r[field+'_date']=None if idx is None else str(z.date.iloc[idx].date())
     r['fixed_interval_overlap']=r['start_date']<=c.end and r['end_date']>=c.date
     records.append(r)
  for method in ['OLD','D8_INTEGRATED']:
   rr=[r for r in records if r['case_key']==key and r['method']==method]
   summary.append(dict(case_key=key,industry_name=c.industry_name,method=method,total_processes=len(rr),confirmed=sum(r['status']=='CONFIRMED' for r in rr),fixed_interval_confirmed=sum(r['status']=='CONFIRMED' and r['fixed_interval_overlap'] for r in rr)))
 pd.DataFrame(records).to_parquet(out/'full_context_processes.parquet',index=False);pd.DataFrame(summary).to_csv(out/'case_comparison.csv',index=False);pd.concat(pathrows).to_parquet(out/'case_full_weekly_paths.parquet',index=False)
 inputs=[Path(__file__),EP/'src/v2_path_probe03_symmetric_calendar_corrected.py',EP/'protocols/v2_s11/plan.md',EP/'protocols/v2_s11/confirmation_guard_addendum.md',casefile,rawfile,statefile,calpath]
 (out/'receipt.json').write_text(json.dumps({'inputs':{str(p):sha(p) for p in inputs},'synthetic_pass':len(checks),'fixed_cases':len(cases),'artifacts':{p.name:sha(p) for p in out.iterdir() if p.is_file()}},ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'synthetic_pass':len(checks),'fixed_cases':len(cases)}));print(pd.DataFrame(summary).to_string(index=False))

if __name__=='__main__':main()
