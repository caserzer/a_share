import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r86';out.mkdir(exist_ok=True);rp=ROOT/'outputs/r85/report_roster.parquet';bp=ROOT/'outputs/r85/broker_snapshots.json';fp=ROOT/'data/r24_source_exclusion_overlay.parquet';ap=ROOT/'outputs/r84/annual_actual_candidates.json'
 reports=pd.read_parquet(rp);groups={k:g for k,g in reports.groupby(['stock_code','broker'])};f=pd.read_parquet(fp);lookup=f[f.basis.eq('profit_cny')].set_index(['infoCode','fiscal_year']);ends=json.loads(bp.read_text());rows=[]
 for end in ends:
  code,year,broker=end['stock_code'],end['fiscal_year'],end['broker'];cutoff=pd.Timestamp(year,6,30);g=groups.get((code,broker),pd.DataFrame(columns=reports.columns));q=g[g.publication_proxy_date<cutoff];status='no_report_before_cutoff';value=None;ids=[];age=None;last=None
  if len(q):
   last=q.publication_proxy_date.max();age=(cutoff-last).days;ids=sorted(q[q.publication_proxy_date.eq(last)].infoCode);vv=[float(lookup.loc[(i,year),'value']) if (i,year) in lookup.index else np.nan for i in ids]
   if age>180:status='stale'
   elif not all(np.isfinite(vv)):status='latest_report_unknown'
   elif len(set(vv))!=1:status='same_day_conflict'
   else:status='valid';value=vv[0]
  rows.append(dict(stock_code=code,fiscal_year=year,broker=broker,june_status=status,december_status=end['status'],june_forecast=value,december_forecast=end['forecast_profit_cny'],june_latest_report_ids=ids,june_latest_publication=last,june_age_days=age,paired=status=='valid' and end['status']=='valid'))
 js(out/'broker_pairs.json',rows);b=pd.DataFrame(rows);companies=[]
 for a in json.loads(ap.read_text()):
  g=b[b.stock_code.eq(a['stock_code'])&b.fiscal_year.eq(a['fiscal_year'])];p=g[g.paired];real=a['actual_profit_cny'];early=float(p.june_forecast.median()) if len(p) else None;late=float(p.december_forecast.median()) if len(p) else None
  def error(v):return (v-real)/(abs(v)+abs(real)) if v is not None and real is not None and abs(v)+abs(real)>0 else None
  e0,e1=error(early),error(late);delta=abs(e1)-abs(e0) if e0 is not None and e1 is not None else None
  companies.append(dict(stock_code=a['stock_code'],fiscal_year=a['fiscal_year'],brokers=len(g),june_valid=int(g.june_status.eq('valid').sum()),december_valid=int(g.december_status.eq('valid').sum()),paired_brokers=len(p),paired_broker_ids=sorted(p.broker),june_forecast=early,december_forecast=late,actual_profit_cny=real,june_error=e0,december_error=e1,absolute_error_change=delta,revision_direction='up' if late is not None and late>early else 'down' if late is not None and late<early else 'unchanged' if late is not None else None,actual_updated_after_notice=a['update_after_notice']))
 js(out/'company_pairs.json',companies);c=pd.DataFrame(companies);summary=[]
 for year,g in c.groupby('fiscal_year'):
  valid=g[g.absolute_error_change.notna()]
  for label,q in [('all',valid),('up',valid[valid.revision_direction.eq('up')]),('down',valid[valid.revision_direction.eq('down')]),('unchanged',valid[valid.revision_direction.eq('unchanged')])]:
   summary.append(dict(fiscal_year=int(year),stratum=label,company_years=len(q),june_mean_absolute_error=float(q.june_error.abs().mean()) if len(q) else None,december_mean_absolute_error=float(q.december_error.abs().mean()) if len(q) else None,mean_absolute_error_change=float(q.absolute_error_change.mean()) if len(q) else None,improved=int(q.absolute_error_change.lt(-1e-12).sum()),worsened=int(q.absolute_error_change.gt(1e-12).sum()),unchanged_error=int(q.absolute_error_change.abs().le(1e-12).sum())))
 js(out/'summary.json',summary);matrix=b.groupby(['june_status','december_status']).size().rename('rows').reset_index();js(out/'coverage_matrix.json',matrix.to_dict('records'));js(out/'coverage.json',dict(broker_rows=len(b),paired_brokers=int(b.paired.sum()),company_years=len(c),paired_company_years=int(c.paired_brokers.gt(0).sum()),evaluable_company_years=int(c.absolute_error_change.notna().sum()),june_known_lost_by_december=int((b.june_status.eq('valid')&~b.december_status.eq('valid')).sum()),december_known_without_june=int((~b.june_status.eq('valid')&b.december_status.eq('valid')).sum())))
 inputs=[rp,bp,fp,ap,ROOT/'outputs/r85/verification.json',ROOT/'protocols/r86.json',Path(__file__)];js(out/'receipt.json',dict(reads={str(p):sha(p) for p in inputs},paired_sample_is_retrospective=True,strict_PIT=False));print((out/'coverage.json').read_text());print(json.dumps([x for x in summary if x['stratum']=='all'],ensure_ascii=False))
if __name__=='__main__':run()
