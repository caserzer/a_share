from common import *
import pandas as pd
from regime_reversal_actions_r220 import IDS
out=ROOT/'outputs/r227';h=pd.read_parquet(out/'event_matches.parquet');rows=[]
for key,g in h.groupby([x for x in IDS if x!='variant']):
 for v in ['state','interaction']:
  q=g[g.variant.eq(v)].merge(g[g.variant.eq('base')],on='event_id',suffixes=('_v','_b'),validate='one_to_one');assert q.status_v.eq(q.status_b).all();q=q[q.status_v.eq('evaluable')];both=q[q.hit_v&q.hit_b];rows.append(dict(zip([x for x in IDS if x!='variant'],key),comparison=v+'-base',events=len(q),gained=int((q.hit_v&~q.hit_b).sum()),lost=int((~q.hit_v&q.hit_b).sum()),both_hit=len(both),same_event_signal_lead_delta=(both.signal_lead_v-both.signal_lead_b).median(),same_event_executable_lead_delta=(both.executable_lead_v-both.executable_lead_b).median()))
pd.DataFrame(rows).to_csv(out/'paired_event_changes.csv',index=False);js(out/'paired_event_receipt.json',dict(status='PASS',comparisons=len(rows),source_sha256=sha(out/'event_matches.parquet'),output_sha256=sha(out/'paired_event_changes.csv'),code_sha256=sha(__file__),scope='Both-hit event timing separated from gained/lost coverage; no timing inference from different event medians'))
print(pd.DataFrame(rows).groupby('comparison')[['gained','lost','same_event_executable_lead_delta']].median().to_string())
