import pandas as pd
from common import *
from train_r02 import F

def run():
 out=ROOT/'outputs/r52';out.mkdir(exist_ok=True)
 source=ROOT/'outputs/r51/frozen_monthly_series.json';features=json.loads(source.read_text())
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
 inputs=[source,ROOT/'protocols/r52.json',ROOT/'data/monthly_panel.parquet',ROOT/'data/r30_size_control.parquet',Path(__file__)]
 js(out/'coverage_summary.json',dict(months=len(features),yoy_months=sum(x['log_yoy'] is not None for x in features),coverage=summary,outcomes_read=False,inputs={str(p):sha(p) for p in inputs}))
 old={tuple(x[k] for k in KEY+['date']):x for x in json.loads((ROOT/'outputs/r40/signal_coverage.json').read_text())}
 changes=[dict(before=old[tuple(x[k] for k in KEY+['date'])],after=x) for x in observations if x!=old[tuple(x[k] for k in KEY+['date'])]]
 js(out/'selection_changes.json',changes)
 print('R52 changed selections',len(changes), 'matched',[(x['level'],x['matched_rows']) for x in summary])
if __name__=='__main__':run()
