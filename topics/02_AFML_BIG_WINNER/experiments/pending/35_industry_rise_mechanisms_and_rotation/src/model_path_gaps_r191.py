from common import *
import pandas as pd

def run():
 out=ROOT/'outputs/r191';out.mkdir(exist_ok=True)
 ip=ROOT/'outputs/r189/intervals.csv';dp=ROOT/'outputs/r129/daily_2026-10-21.parquet';ap=CACHE/'extension_v2/products/assignments.parquet';bp=CACHE/'forecast_v5/CSI_ALL.parquet'
 i=pd.read_csv(ip,parse_dates=['origin','entry','exit']);bad=i[i.status.ne('valid')];assert bad.status.eq('missing_selected_path').all()
 d=pd.read_parquet(dp);a=pd.read_parquet(ap,columns=KEY+['month','security_id','unresolved']);assert not a.duplicated(KEY+['month','security_id']).any()
 counts=a.groupby(KEY+['month']).security_id.nunique();cal=pd.DatetimeIndex(pd.read_parquet(bp).index);lookup={k:v.set_index('date') for k,v in d.groupby(KEY)}
 exposures=[]
 for row in bad.to_dict('records'):
  for code in row['missing_codes'].split(';'):exposures.append({k:row[k] for k in ['era','level','cohort','horizon','method','origin','entry','exit']}|{'industry_code':code})
 exposure=pd.DataFrame(exposures);exposure.to_csv(out/'failed_exposures.csv',index=False)
 windows=exposure[KEY+['entry','exit']].drop_duplicates();records=[];details=[]
 for row in windows.to_dict('records'):
  key=tuple(row[k] for k in KEY);g=lookup.get(key);dates=cal[(cal>=row['entry'])&(cal<=row['exit'])];z=g.reindex(dates) if g is not None else pd.DataFrame(index=dates,columns=['nav','block','source_kind'])
  missing=z.nav.isna();assert missing.any() or z.block.nunique()!=1
  rec=dict(row,expected_dates=len(dates),missing_dates=int(missing.sum()),blocks=int(z.block.nunique()),anchors=int(z.source_kind.eq('anchor').sum()))
  for date in dates:
   if pd.isna(z.loc[date,'nav']):
    mo=date.to_period('M')-1;n=counts.get(key+(mo,),None)
    reason='prior_month_members_below5' if n is not None and n<5 else 'missing_membership' if n is None else 'missing_price_or_coverage_unresolved'
    details.append(dict(row,date=date,membership_month=str(mo),members=n,reason=reason))
   elif z.loc[date,'source_kind']=='anchor':details.append(dict(row,date=date,membership_month=None,members=z.loc[date].get('members',None),reason='anchor_not_observed_price'))
  records.append(rec)
 pd.DataFrame(records).to_csv(out/'windows.csv',index=False);dd=pd.DataFrame(details);dd.to_csv(out/'date_details.csv',index=False)
 unique=dd.drop_duplicates(KEY+['date','reason']);unique.to_csv(out/'unique_date_details.csv',index=False)
 summary=dict(failed_method_intervals=len(bad),failed_industry_exposures=len(exposure),unique_windows=len(windows),unique_industries=len(windows[KEY].drop_duplicates()),unique_date_reasons=unique.reason.value_counts().to_dict(),no_repair=True,adoption=False)
 js(out/'summary.json',summary)
 reads=[ip,dp,ap,bp,ROOT/'src/basket_repair_r129.py',ROOT/'protocols/r191.json',Path(__file__)]
 files=['failed_exposures.csv','windows.csv','date_details.csv','unique_date_details.csv','summary.json']
 js(out/'verification.json',dict(status='PASS',scope='All reported failed windows actually missing dates or crossing blocks; member count gate from independent assignment count; no missing-return imputation',inputs={str(x):sha(x) for x in reads},outputs={x:sha(out/x) for x in files}))
 print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':run()
