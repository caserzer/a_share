"""Freeze partial installation growth and audit eligibility without reading outcomes."""
import pandas as pd
from common import *
from train_r02 import F

def run(round_id='r39'):
 assert round_id in ['r39','r40']
 out=ROOT/f'outputs/{round_id}';out.mkdir(exist_ok=True)
 snapshot=out/'inputs';snapshot.mkdir(exist_ok=True)
 for name in ['extractions.json','reviewed_publication_dates.json']:
  if not (snapshot/name).exists():(snapshot/name).write_bytes((ROOT/'outputs/r38'/name).read_bytes())
 source=snapshot/'extractions.json';dates=snapshot/'reviewed_publication_dates.json'
 extracts=json.loads(source.read_text());reviewed={x['url']:x for x in json.loads(dates.read_text())}
 rows=[]
 for x in extracts:
  if x['value_gwh'] is None:continue
  manual=reviewed.get(x['url']);display=manual['page_display_date'] if manual else x['page_updated']
  if manual:assert manual['raw_sha256']==x['raw_sha256']
  if display is None:continue
  available=pd.Timestamp(display).normalize()+pd.Timedelta(days=1)
  assert available>pd.Period(x['economic_month'],'M').end_time
  rows.append(dict(month=x['economic_month'],value_gwh=x['value_gwh'],page_date=display,available_at=available.isoformat(),url=x['url'],raw_sha256=x['raw_sha256']))
 frame=pd.DataFrame(rows)
 assert frame.groupby('month').value_gwh.nunique().max()==1
 frame=frame.sort_values(['month','available_at','url']).drop_duplicates('month')
 by={r['month']:r for r in frame.to_dict('records')};features=[]
 for m,r in by.items():
  prior=str(pd.Period(m,'M')-12);lag=by.get(prior)
  features.append(dict(**r,prior_month=prior,prior_gwh=lag['value_gwh'] if lag else None,prior_sha256=lag['raw_sha256'] if lag else None,log_yoy=float(np.log(r['value_gwh']/lag['value_gwh'])) if lag else None,growth_available_at=max(r['available_at'],lag['available_at']) if lag else None))
 js(out/'frozen_monthly_series.json',features)
 signal_cols=KEY+['date','price_ready']+F[:-1]+['members']
 panel=pd.read_parquet(ROOT/'data/monthly_panel.parquet',columns=signal_cols)
 panel=panel[panel.era.eq('SW2021')&panel.industry_code.isin(['801737.SI','857371.SI'])].copy();panel['log_members']=np.log(panel.members)
 size=pd.read_parquet(ROOT/'data/r30_size_control.parquet',columns=KEY+['date','size_control'])
 panel=panel.merge(size,on=KEY+['date'],how='left',validate='one_to_one')
 observations=[]
 for _,r in panel.iterrows():
  date=pd.Timestamp(r['date']);eligible=[x for x in features if x['growth_available_at'] and pd.Timestamp(x['growth_available_at'])<=date and 0<=date.to_period('M').ordinal-pd.Period(x['month'],'M').ordinal<=2]
  selected=max(eligible,key=lambda x:x['month']) if eligible else None
  observations.append(dict(**{k:(r[k].isoformat() if k=='date' else r[k]) for k in KEY+['date']},economic_month=selected['month'] if selected else None,log_yoy=selected['log_yoy'] if selected else None,growth_available_at=selected['growth_available_at'] if selected else None,price_complete=bool(r.price_ready and r[F].notna().all()),size_complete=bool(pd.notna(r.size_control))))
 js(out/'signal_coverage.json',observations)
 summary=[]
 for level in ['L2','L3']:
  q=[x for x in observations if x['level']==level];ready=[x for x in q if x['log_yoy'] is not None and x['price_complete'] and x['size_complete']]
  summary.append(dict(level=level,signal_rows=len(q),growth_rows=sum(x['log_yoy'] is not None for x in q),matched_rows=len(ready),matched_dates=[x['date'] for x in ready]))
 inputs=[source,dates,ROOT/f'protocols/{round_id}.json',ROOT/'data/monthly_panel.parquet',ROOT/'data/r30_size_control.parquet',Path(__file__)]
 js(out/'coverage_summary.json',dict(months=len(features),yoy_months=sum(x['log_yoy'] is not None for x in features),coverage=summary,quality='Historical-proxy; no first-release or revision certification',outcomes_read=False,inputs={str(p):sha(p) for p in inputs}))
 print(json.dumps(dict(months=len(features),yoy_months=sum(x['log_yoy'] is not None for x in features),coverage=summary),ensure_ascii=False))

if __name__=='__main__':run()
