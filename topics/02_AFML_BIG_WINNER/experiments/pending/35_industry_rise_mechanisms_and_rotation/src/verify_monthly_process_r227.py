from common import *
import pandas as pd
from regime_reversal_actions_r220 import IDS

def run():
 out=ROOT/'outputs/r227';a=pd.read_parquet(out/'signal_inventory.parquet');h=pd.read_parquet(out/'event_matches.parquet');s=pd.read_csv(out/'summary.csv');source=pd.read_parquet(ROOT/'outputs/r221/actions.parquet');event=pd.read_csv(ROOT/'outputs/r155/evaluation/outputs/r09/confirmation_events.csv',parse_dates=['date']);event['event_id']=np.arange(len(event))
 cols=IDS+['industry_code','date','alert'];pd.testing.assert_frame_equal(a[cols].sort_values(cols[:-1]).reset_index(drop=True),source[cols].sort_values(cols[:-1]).reset_index(drop=True))
 signals={k:sorted(z.day_i.tolist()) for k,z in a[a.alert].groupby(IDS+['industry_code','block'])};candidates={k:sorted(z.day_i.tolist()) for k,z in a.groupby(IDS+['industry_code','block'])};schedules={k:sorted(z.day_i.unique().tolist()) for k,z in a.groupby(IDS)};event_lookup=event.set_index('event_id').to_dict('index');checks=0
 for row in h.to_dict('records'):
  ident=tuple(row[c] for c in IDS);key=ident+(row['industry_code'],row['block']);end=row['event_day_i'];days=[x for x in signals.get(key,[]) if end-20<=x<end];candidate=[x for x in candidates.get(key,[]) if end-20<=x<end];scheduled=[x for x in schedules[ident] if end-20<=x<end];ev=event_lookup[row['event_id']]
  assert row['industry_code']==ev['industry_code'] and row['event_date']==ev['date'] and row['block']==ev['block']
  status='left_censored' if not ev['evaluable'] else 'no_scheduled_origin' if not scheduled else 'evaluable';hit=status=='evaluable' and bool(days)
  assert row['status']==status and row['hit']==hit and row['candidate_origins']==len(candidate) and row['matched_alerts']==len(days) and row['scheduled_origins']==len(scheduled)
  if hit:assert row['signal_lead']==end-min(days) and row['executable_lead']==end-min(days)-1
  checks+=1
 lookup={k:z for k,z in h.groupby(IDS)}
 for row in s.to_dict('records'):
  z=lookup[tuple(row[c] for c in IDS)];v=z[z.status.eq('evaluable')];assert len(v)==row['events'] and int(v.hit.sum())==row['hits'];assert np.isclose(v.hit.mean(),row['recall'],equal_nan=True)
 js(out/'independent_verification.json',dict(status='PASS',source_alert_rows=len(a),event_checks=checks,groups=len(s),scope='All source alert identities, independent calendar-window matching and summary recall',code_sha256=sha(__file__)))
 print(len(a),checks,len(s))
if __name__=='__main__':run()
