import pandas as pd
from common import *
FEATURES=['past_excess20','past_excess60','mom20','mom60','vol20','dd60','breadth21','members']
METRICS=['excess20','return20','continuation_excess20_60']+FEATURES
def run():
 out=ROOT/'outputs/r96';out.mkdir(exist_ok=True);ap=ROOT/'outputs/r95/alerts.parquet';pp=ROOT/'data/monthly_panel.parquet';a=pd.read_parquet(ap);a=a[a.strategy.eq('monthly')].copy();panel=pd.read_parquet(pp);d=a.merge(panel[KEY+['date']+FEATURES],on=KEY+['date'],how='left',validate='one_to_one');d.to_parquet(out/'monthly_alerts.parquet',index=False);ledger=[];contrasts=[]
 for key,g in d.groupby(['era','level','date']):
  pos=g[g.accounting_group.eq('positive')];neg=g[g.accounting_group.eq('negative')];paired=len(pos)>0 and len(neg)>0;ledger.append(dict(zip(['era','level','date'],key),alerts=len(g),positive=len(pos),negative=len(neg),zero=int(g.accounting_group.eq('zero').sum()),unknown=int(g.accounting_group.eq('unknown').sum()),paired=paired))
  if not paired:continue
  for metric in METRICS:
   valid=pos[metric].notna().all() and neg[metric].notna().all();contrasts.append(dict(zip(['era','level','date'],key),metric=metric,positive=len(pos),negative=len(neg),positive_known=int(pos[metric].notna().sum()),negative_known=int(neg[metric].notna().sum()),status='complete' if valid else 'incomplete_group',positive_mean=pos[metric].mean() if valid else None,negative_mean=neg[metric].mean() if valid else None,difference=pos[metric].mean()-neg[metric].mean() if valid else None))
 js(out/'date_ledger.json',ledger);js(out/'contrasts.json',contrasts);c=pd.DataFrame(contrasts);summary=[]
 for key,g in c.groupby(['era','level','metric']):
  q=g[g.status.eq('complete')];summary.append(dict(zip(['era','level','metric'],key),paired_dates=len(g),complete_dates=len(q),unknown_dates=len(g)-len(q),positive_rows=int(q.positive.sum()),negative_rows=int(q.negative.sum()),date_equal_difference=q.difference.mean(),positive_dates=int(q.difference.gt(0).sum()),negative_dates=int(q.difference.lt(0).sum())))
 js(out/'summary.json',summary);paths=[ap,pp,ROOT/'outputs/r95/verification.json',ROOT/'protocols/r96.json',Path(__file__)];js(out/'receipt.json',dict(reads={str(p):sha(p) for p in paths},monthly_alerts=len(d),date_groups=len(ledger),paired_date_groups=sum(x['paired'] for x in ledger),no_new_model=True));print((out/'receipt.json').read_text());print(json.dumps([x for x in summary if x['metric'] in ['excess20','past_excess20','past_excess60']],default=str))
if __name__=='__main__':run()
