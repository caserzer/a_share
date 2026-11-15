from common import *
import re,math,gzip
from bs4 import BeautifulSoup
import pandas as pd

def run():
 out=ROOT/'outputs/r275';out.mkdir(exist_ok=True);sources=json.loads((ROOT/'outputs/r60/frozen_monthly_series.json').read_text());records=[]
 for x in sources:
  month=x['month'];m=int(month[-2:]);body=(ROOT/f'outputs/r274/bodies/{month}.txt').read_text();
  if 'www.aqsiqauto.com' in x['url']:
   raw=(ROOT/'data/r38_battery_originals'/f"{x['raw_sha256']}.html").read_bytes();assert sha(ROOT/'data/r38_battery_originals'/f"{x['raw_sha256']}.html")==x['raw_sha256'];soup=BeautifulSoup(gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw,'html.parser');nodes=soup.select('.News-Content > div:first-child');assert len(nodes)==1;body=nodes[0].get_text(' ',strip=True)
  (out/'bodies').mkdir(exist_ok=True);(out/'bodies'/f'{month}.txt').write_text(body);text=re.sub(r'\s+','',body)
  pattern=rf'(?<![\d至到—–-]){m}月份?[，,]?(?:在新能源汽车市场带动下[，,])?我国(?P<scope>动力电池|动力和储能电池|动力和其他电池)(?:合计)?产量(?:共计|为)(?P<value>\d+(?:\.\d+)?)GWh'
  matches=[dict(scope=a.group('scope'),value=float(a.group('value')),quote=a.group(),start=a.start(),end=a.end()) for a in re.finditer(pattern,text,re.I)]
  unique={(a['scope'],a['value']) for a in matches};valid=len(unique)==1
  scope,value=next(iter(unique)) if valid else (None,None)
  segment=('power_only_pre202308' if scope=='动力电池' and month<'2023-08' else 'power_storage_202308_202311' if scope=='动力和储能电池' and '2023-08'<=month<='2023-11' else 'power_other_202312_202511' if scope=='动力和其他电池' and '2023-12'<=month<='2025-11' else 'power_storage_from202512' if scope=='动力和储能电池' and month>='2025-12' else None)
  records.append(dict(month=month,scope=scope,scope_segment=segment,production_gwh=value,status='direct_disclosure' if valid and segment else 'missing_or_ambiguous',matches=matches,raw_sha256=x['raw_sha256'],page_date=x['page_date'],available_at=x['available_at'],url=x['url'],body_sha256=sha(out/f'bodies/{month}.txt')))
 lookup={r['month']:r for r in records}
 for r in records:
  prior=f"{int(r['month'][:4])-1:04d}{r['month'][4:]}";q=lookup.get(prior);ok=q and r['status']==q['status']=='direct_disclosure' and r['scope_segment']==q['scope_segment'] and min(r['production_gwh'],q['production_gwh'])>0
  r.update(prior_month=prior,production_log_yoy=math.log(r['production_gwh']/q['production_gwh']) if ok else None,production_growth_available_at=max(r['available_at'],q['available_at']) if ok else None,growth_status='same_wording_segment_proxy' if ok else 'no_same_segment_pair')
 js(out/'production_registry.json',records)
 flat=pd.DataFrame([{k:v for k,v in r.items() if k!='matches'} for r in records]);flat.to_csv(out/'production_registry.csv',index=False)
 p=pd.read_parquet(ROOT/'outputs/r140/cohort_new.parquet');supply=flat.rename(columns={'month':'economic_month'});p=p.merge(supply[['economic_month','production_log_yoy','production_growth_available_at','scope_segment']],on='economic_month',how='left',validate='many_to_one');p['supply_available']=p.production_log_yoy.notna()&pd.to_datetime(p.production_growth_available_at).le(p.date)
 p['regime']=p.date.map(pd.read_parquet(ROOT/'outputs/r195/market_regimes.parquet').regime);ledger=[]
 for identity,g in p.groupby(KEY):
  for h in [20,60]:
   for year in sorted(g.date.dt.year.unique()):
    boundary=pd.Timestamp(int(year),1,1);fit=g.date.lt(boundary)&g[f'maturity{h}'].lt(boundary)&g[f'excess{h}'].notna()&g.regime.notna();test=g.date.dt.year.eq(year)&g.regime.notna();tr=g[fit&g.supply_available];te=g[test&g.supply_available]
    ledger.append(dict(zip(KEY,identity),horizon=h,year=int(year),original_train_months=g[fit].date.nunique(),supply_train_months=tr.date.nunique(),original_test_months=g[test].date.nunique(),supply_test_months=te.date.nunique(),eligible=bool(tr.date.nunique()>=24 and len(te)>0)))
 p.to_parquet(out/'qualification_panel.parquet',index=False);js(out/'fold_qualification.json',ledger)
 summary=dict(status='PASS',months=len(records),direct_disclosures=sum(r['status']=='direct_disclosure' for r in records),missing=[r['month'] for r in records if r['status']!='direct_disclosure'],same_segment_yoy=sum(r['production_log_yoy'] is not None for r in records),scope_counts=flat.groupby('scope_segment').size().to_dict(),eligible_return_folds=sum(r['eligible'] for r in ledger),max_training_months=max(r['supply_train_months'] for r in ledger),adoption=False,strict_pit=False)
 js(out/'summary.json',summary);js(out/'receipt.json',dict(inputs={str(f.relative_to(ROOT)):sha(f) for f in [ROOT/'protocols/r275.json',ROOT/'src/battery_production_r275.py',ROOT/'outputs/r60/frozen_monthly_series.json',ROOT/'outputs/r140/cohort_new.parquet',ROOT/'outputs/r195/market_regimes.parquet',*sorted((ROOT/'outputs/r274/bodies').glob('*.txt'))]},outputs={str(f.relative_to(out)):sha(f) for f in [*out.glob('*.json'),*out.glob('*.csv'),*out.glob('*.parquet'),*out.glob('bodies/*.txt')] if f.name!='receipt.json'}));print(summary)
if __name__=='__main__':run()
