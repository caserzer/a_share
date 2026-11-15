import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r89';out.mkdir(exist_ok=True);cp=ROOT/'outputs/r88/events.parquet';np_=ROOT/'data/r26_mapped_report_events.parquet';rp=ROOT/'outputs/r84/receipt.json';c=pd.read_parquet(cp);n=pd.read_parquet(np_);keys=['stock_code','broker','publication_date'];n=n[keys+['fiscal_year','previous_date','revision']].drop_duplicates();assert not n.duplicated(keys).any();p=c.merge(n,on=keys,how='inner',suffixes=('_current','_next'),validate='one_to_one');assert (p.fiscal_year_next==p.fiscal_year_current+1).all();p['same_previous_date']=p.previous_date_current.eq(p.previous_date_next);p['current_sign']=np.sign(p.revision_current).astype(int);p['next_sign']=np.sign(p.revision_next).astype(int)
 rec=json.loads(rp.read_text());paths={Path(s).stem.split('.')[0]:Path(s) for s in rec['reads'] if '/proxy/financials/' in s};reads={};actual=[]
 targets=set(zip(p.stock_code,p.fiscal_year_current))|set(zip(p.stock_code,p.fiscal_year_next));cache={}
 for code,year in sorted(targets):
  status='not_ended';value=None;refs=[]
  if pd.Timestamp(int(year),12,31)<=pd.Timestamp('2026-10-21'):
   path=paths.get(code)
   if path is None:status='no_partition'
   else:
    if code not in cache:
     assert sha(path)==rec['reads'][str(path)];reads[str(path)]=sha(path);cache[code]=pd.read_parquet(path)
    f=cache[code];q=f[pd.to_datetime(f.REPORT_DATE).eq(pd.Timestamp(int(year),12,31))];status='annual_absent'
    if len(q):
     values=pd.to_numeric(q.PARENTNETPROFIT,errors='coerce');status='candidate' if (q.REPORT_TYPE.eq('年报')&q.CURRENCY.eq('CNY')).all() and np.isfinite(values).all() and values.nunique()==1 else 'unknown_basis_value_or_conflict';value=float(values.iloc[0]) if status=='candidate' else None
     refs=[dict(source_path=str(path),source_row=int(i),notice_date=x.NOTICE_DATE,update_date=x.UPDATE_DATE) for i,x in q.iterrows()]
  actual.append(dict(stock_code=code,fiscal_year=int(year),status=status,profit_cny=value,refs=refs))
 lookup={(x['stock_code'],x['fiscal_year']):x for x in actual}
 for suffix in ['current','next']:p[f'actual_status_{suffix}']=[lookup[code,year]['status'] for code,year in zip(p.stock_code,p[f'fiscal_year_{suffix}'])]
 p.to_parquet(out/'paired_events.parquet',index=False);js(out/'annual_actuals.json',actual);js(out/'direction_matrix.json',p.groupby(['current_sign','next_sign']).size().rename('rows').reset_index().to_dict('records'))
 company=p.groupby(['stock_code','publication_date']).agg(current_revision=('revision_current','median'),next_revision=('revision_next','median'),brokers=('broker','size')).reset_index();company['publication_year']=company.publication_date.dt.year;company['opposite']=company.current_revision*company.next_revision<0;company.to_parquet(out/'company_dates.parquet',index=False)
 summary=dict(paired_events=len(p),same_previous_date=int(p.same_previous_date.sum()),same_direction=int(p.current_sign.eq(p.next_sign).sum()),opposite_nonzero=int((p.current_sign*p.next_sign<0).sum()),one_zero=int(((p.current_sign==0)^(p.next_sign==0)).sum()),both_zero=int((p.current_sign.eq(0)&p.next_sign.eq(0)).sum()),current_actual_status=p.actual_status_current.value_counts().to_dict(),next_actual_status=p.actual_status_next.value_counts().to_dict(),company_dates=len(company),company_dates_opposite=int(company.opposite.sum()),strict_PIT=False);js(out/'summary.json',summary)
 js(out/'by_year.json',company.groupby('publication_year').agg(company_dates=('stock_code','size'),opposite=('opposite','sum'),current_mean=('current_revision','mean'),next_mean=('next_revision','mean')).reset_index().to_dict('records'))
 for path in [cp,np_,rp,ROOT/'protocols/r89.json',Path(__file__)]:reads[str(path)]=sha(path)
 js(out/'receipt.json',dict(reads=reads,as_of='2026-10-21',no_new_price_evaluation=True));print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':run()
