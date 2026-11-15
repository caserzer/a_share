"""Descriptive EPS/profit denominator audit, no market outcomes."""
import pandas as pd
from common import *


def pairs(values):
 keys=['infoCode','stock_code','broker','fiscal_year','publication_proxy_date','raw_sha256']
 rows=[]
 for key,g in values.groupby(keys,dropna=False):
  r=dict(zip(keys,key))
  for basis,name in [('profit_cny','profit'),('eps_cny_per_share','eps')]:
   x=g.loc[g.basis.eq(basis),'value'];r[name]=x.iloc[0] if len(x) and x.notna().all() and x.nunique()==1 else np.nan
  r['pair_status']='positive_pair' if r['profit']>0 and r['eps']>0 else ('nonpositive_pair' if np.isfinite(r['profit']) and np.isfinite(r['eps']) else 'missing_or_conflicting_basis')
  r['implied_shares']=r['profit']/r['eps'] if r['pair_status']=='positive_pair' else np.nan
  rows.append(r)
 return pd.DataFrame(rows)


def sequences(paired,reports):
 rows=[]
 for (stock,broker),g in reports[reports.broker.notna()].groupby(['stock_code','broker']):
  pp=paired[(paired.stock_code==stock)&(paired.broker==broker)]
  for year in pp.fiscal_year.unique():
   joined=g.merge(pp[pp.fiscal_year.eq(year)][['infoCode','profit','eps']],on='infoCode',how='left',validate='one_to_one')
   dates=[]
   for date,d in joined.groupby('publication_proxy_date'):
    rec=dict(date=date,report_ids=';'.join(sorted(d.infoCode)))
    for col in ['profit','eps']:rec[col]=d[col].iloc[0] if d[col].notna().all() and d[col].nunique()==1 else np.nan
    dates.append(rec)
   dates=sorted(dates,key=lambda x:x['date'])
   for previous,current in zip(dates,dates[1:]):
    if year not in [current['date'].year,current['date'].year+1]:continue
    r=dict(stock_code=stock,broker=broker,fiscal_year=int(year),publication_date=current['date'],previous_date=previous['date'],current_reports=current['report_ids'],previous_reports=previous['report_ids'])
    valid=True
    for col in ['profit','eps']:
     old=previous[col];new=current[col];r[col+'_old']=old;r[col+'_new']=new
     r[col+'_revision']=(new-old)/(abs(new)+abs(old)) if np.isfinite(old) and np.isfinite(new) and abs(new)+abs(old)>0 else np.nan
     valid &= bool(old>0 and new>0)
    r['status']='positive_comparable_candidate' if valid else 'unknown_or_nonpositive_pair'
    if (current['date']-previous['date']).days>365:r['status']='prior_older_than365'
    r['implied_share_ratio']=(r['profit_new']/r['eps_new'])/(r['profit_old']/r['eps_old']) if r['status']=='positive_comparable_candidate' else np.nan
    r['opposite_revision_signs']=bool(r['profit_revision']*r['eps_revision']<0) if r['status']=='positive_comparable_candidate' else None
    rows.append(r)
 return pd.DataFrame(rows)


def run():
 out=ROOT/'outputs/r24';out.mkdir(exist_ok=True)
 ep=ROOT.parent/'24_conditional_return_distribution_exploration/outputs/r19_eps_expectations'
 paths=[ROOT/'data/r11_analyst_forecasts.parquet',ep/'validated_extractions.parquet',ep/'selected_reports.parquet',ROOT/'protocols/r24.json',Path(__file__)]
 receipt=json.loads((ROOT/'outputs/r11/receipt.json').read_text())
 assert sha(paths[1])==receipt['source_extraction_sha256'] and sha(paths[2])==receipt['source_metadata_sha256']
 v=pd.read_parquet(paths[0]);p=pairs(v)
 reports=pd.read_parquet(paths[1],columns=['infoCode','stockCode','publishDate','available_date']).merge(pd.read_parquet(paths[2],columns=['infoCode','orgCode']),on='infoCode',validate='one_to_one').rename(columns={'stockCode':'stock_code','orgCode':'broker'})
 reports['publication_proxy_date']=pd.concat([pd.to_datetime(reports.publishDate),pd.to_datetime(reports.available_date)],axis=1).max(axis=1)
 s=sequences(p,reports[['infoCode','stock_code','broker','publication_proxy_date']]);good=s[s.status.eq('positive_comparable_candidate')]
 p.to_parquet(ROOT/'data/r24_report_pairs.parquet',index=False);s.to_csv(out/'revision_pairs.csv',index=False)
 examples=pd.concat([good.nsmallest(5,'implied_share_ratio'),good.nlargest(5,'implied_share_ratio')]).drop_duplicates();examples.to_csv(out/'extreme_examples.csv',index=False)
 js(out/'receipt.json',dict(reads={str(x):sha(x) for x in paths},report_fy_pairs=len(p),pair_status=p.pair_status.value_counts().to_dict(),sequence_rows=len(s),sequence_status=s.status.value_counts().to_dict(),opposite_revision_signs=int(good.opposite_revision_signs.sum()),share_ratio_quantiles=good.implied_share_ratio.quantile([0,.01,.1,.5,.9,.99,1]).to_dict(),outputs={str(x):sha(x) for x in [ROOT/'data/r24_report_pairs.parquet',out/'revision_pairs.csv',out/'extreme_examples.csv']},limitation='implied denominator diagnostic only; neither actual shares nor split/definition comparability verified'))
 print(json.dumps(json.loads((out/'receipt.json').read_text())['sequence_status']));print('positive',len(good),'opposite',int(good.opposite_revision_signs.sum()));print(good.implied_share_ratio.quantile([0,.01,.5,.99,1]))

if __name__=='__main__':run()
