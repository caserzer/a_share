"""Read-only reuse audit of EP24 monthly exchange financing archives."""
import pandas as pd
from common import *

SOURCE=ROOT.parent/'24_conditional_return_distribution_exploration/outputs/local_cache/r27_margin_snapshots'
def run():
 out=ROOT/'outputs/r44';out.mkdir(exist_ok=True);d=pd.read_parquet(SOURCE/'normalized_detail.parquet');market=pd.read_parquet(SOURCE/'normalized_market.parquet')
 assert not d.duplicated(['date','instrument']).any() and not market.date.duplicated().any()
 assert d[['financing','buy','lending_quantity']].ge(0).all().all()
 calendar=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet',columns=[]).index.sort_values().tolist();index={date:i for i,date in enumerate(calendar)}
 lagrows=[]
 for r in market.itertuples():
  lag=index[r.date]-index[r.snapshot_date];assert lag==2
  lagrows.append(dict(date=r.date.isoformat(),snapshot_date=r.snapshot_date.isoformat(),trading_sessions=lag))
 receipts=[];sh_checked=0;sz_checked=0
 for path in sorted(SOURCE.glob('*.receipt.json')):
  rec=json.loads(path.read_text());body=path.with_suffix('').with_suffix('.body');assert body.exists() and body.stat().st_size==rec['bytes'] and sha(body)==rec['sha256'] and rec['status']==200
  receipts.append(dict(path=str(path),body=str(body),receipt_sha256=sha(path),body_sha256=rec['sha256'],bytes=rec['bytes'],fetched_at=rec['fetched_at'],requested_date=rec['requested_date']))
  stamp=pd.Timestamp(rec['requested_date']);q=d[d.snapshot_date.eq(stamp)].set_index('instrument')
  if path.name.startswith('sse_detail'):
   raw=json.loads(body.read_bytes())['result']
   for row in raw:
    assert row['opDate']==rec['requested_date'];x=q.loc['SH'+row['stockCode']]
    assert float(row['rzye'])==x.financing and float(row['rzmre'])==x.buy;sh_checked+=1
  if path.name.startswith('szse_metadata'):
   table=next(t for t in json.loads(body.read_bytes()) if t['metadata']['tabkey']=='tab2')
   assert table['metadata']['subname']==str(stamp.date())
   assert int(table['metadata']['recordcount'])==sum(q.index.str.startswith('SZ'))
   for row in table['data']:
    x=q.loc['SZ'+row['zqdm']]
    for rawfield,col in [('jrrzye','financing'),('jrrzmr','buy')]:assert abs(float(str(row[rawfield]).replace(',',''))*1e8-x[col])<=1000100
    sz_checked+=1
 cols=['month']+KEY+['security_id','instrument'];members=pd.concat([pd.read_parquet(CACHE/'extension_v2/products/assignments.parquet',columns=cols),pd.read_parquet(ROOT/'data/l1_assignments.parquet',columns=cols)],ignore_index=True)
 assert not members.duplicated(['month']+KEY+['security_id']).any()
 identities=members.groupby(['month','instrument']).security_id.nunique();assert identities.max()==1
 signals=pd.concat([pd.read_parquet(ROOT/'data/monthly_panel.parquet',columns=KEY+['date']),pd.read_parquet(ROOT/'data/l1_monthly_panel.parquet',columns=KEY+['date'])]);signals=signals[signals.date.isin(market.date)].copy();signals['month']=signals.date.dt.to_period('M')-1
 joined=signals.merge(members,on=['month']+KEY,how='left',validate='one_to_many').merge(d[['date','instrument','financing','buy']],on=['date','instrument'],how='left',validate='many_to_one')
 coverage=joined.groupby(KEY+['date']).agg(members=('security_id','count'),observed=('financing','count'),disclosed_zero=('financing',lambda x:int(x.eq(0).sum()))).reset_index();coverage['fraction']=coverage.observed/coverage.members;coverage['coverage_ready']=coverage.observed.ge(5)&coverage.fraction.ge(.8);coverage.to_parquet(out/'industry_coverage.parquet',index=False)
 summary=coverage.groupby(['era','level']).agg(industry_dates=('date','size'),coverage_ready=('coverage_ready','sum'),median_fraction=('fraction','median')).reset_index();js(out/'coverage_summary.json',summary.to_dict('records'));js(out/'source_receipts.json',receipts);js(out/'calendar_lags.json',lagrows)
 reads=[CACHE/'forecast_v5/CSI_ALL.parquet',SOURCE/'normalized_detail.parquet',SOURCE/'normalized_market.parquet',CACHE/'extension_v2/products/assignments.parquet',ROOT/'data/l1_assignments.parquet',ROOT/'data/monthly_panel.parquet',ROOT/'data/l1_monthly_panel.parquet',ROOT/'protocols/r44.json',Path(__file__)]
 js(out/'receipt.json',dict(inputs={str(p):sha(p) for p in reads},detail_rows=len(d),months=market.date.nunique(),min_date=str(market.date.min()),max_date=str(market.date.max()),raw_receipts=len(receipts),bytes_checked=sum(x['bytes'] for x in receipts),sh_rows_exact=sh_checked,sz_display_rows=sz_checked,calendar_lags_checked=len(lagrows),industry_dates=len(coverage),coverage_sha256=sha(out/'industry_coverage.parquet'),outcomes_read=False,quality='Historical-proxy; downloaded historical archive not initial-release certification; SZ exact Excel parsing inherited',unmapped_rows=int((~d.set_index(['date','instrument']).index.isin(joined.dropna(subset=['security_id']).set_index(['date','instrument']).index)).sum())))
 print(summary.to_string(index=False));print('R44 RAW CHECKS',sh_checked,sz_checked,len(receipts))

if __name__=='__main__':run()
