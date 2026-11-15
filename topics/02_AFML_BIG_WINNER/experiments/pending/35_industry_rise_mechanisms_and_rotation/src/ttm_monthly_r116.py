"""Select latest visible report before gating its TTM components."""
import pandas as pd
from common import *
def choose(events,date,clock):
    visible=events[events[clock+'_report_available_at'].le(date)]
    r=dict(report_period=pd.NaT,report_available_at=pd.NaT,component_available_at=pd.NaT,status='no_visible_report',ttm_profit=np.nan,report_age_days=np.nan)
    if visible.empty:return r
    x=visible.loc[visible.report_period.idxmax()];r.update(report_period=x.report_period,report_available_at=x[clock+'_report_available_at'],component_available_at=x[clock+'_available_at'],report_age_days=(date-x.report_period).days)
    if x.status!='valid_components':r['status']='latest_components_invalid'
    elif pd.isna(x[clock+'_available_at']):r['status']='unknown_component_clock'
    elif x[clock+'_available_at']>date:r['status']='latest_components_not_yet_available'
    else:r.update(status='known_ttm',ttm_profit=x.ttm_profit)
    return r

def run():
    out=ROOT/'outputs/r116';out.mkdir(exist_ok=True)
    paths=[ROOT/'outputs/r115/financial_rows.parquet',ROOT/'outputs/r115/ttm_candidates.parquet',CACHE/'forecast_v5/CSI_ALL.parquet']
    raw=pd.read_parquet(paths[0]);c=pd.read_parquet(paths[1]);ix=pd.DatetimeIndex(pd.read_parquet(paths[2]).index).sort_values();ends=pd.Series(ix,index=ix.to_period('M')).groupby(level=0).max();ends=ends[(ends.index.end_time.normalize()<=ix.max())&(ends.index>=pd.Period('2020-01'))]
    r=raw.assign(report_period=pd.to_datetime(raw.REPORT_DATE),notice=pd.to_datetime(raw.NOTICE_DATE,errors='coerce'),update=pd.to_datetime(raw.UPDATE_DATE,errors='coerce'))
    rows=[]
    for (code,period),g in r.groupby(['SECUCODE','report_period']):
        if not 2020<=period.year<=2026:continue
        notice=g.notice.max().normalize() if g.notice.notna().all() and g.notice.ge(period).all() else pd.NaT
        update=max(notice,g['update'].max().normalize()) if pd.notna(notice) and g['update'].notna().all() else pd.NaT
        row=dict(secucode=code,report_period=period,current_row_ids=g.row_id.tolist())
        for clock,d in [('notice',notice),('update',update)]:
            row[clock+'_report_proxy_date']=d;pos=ix.searchsorted(d,side='right') if pd.notna(d) else len(ix);row[clock+'_report_available_at']=ix[pos] if pos<len(ix) else pd.NaT
        rows.append(row)
    e=c.merge(pd.DataFrame(rows),on=['secucode','report_period'],validate='one_to_one');e.to_parquet(out/'report_events.parquet',index=False)
    rows=[]
    for code in sorted(raw.SECUCODE.unique()):
        g=e[e.secucode==code]
        for clock in ['notice','update']:
            for date in ends:rows.append(dict(secucode=code,date=date,clock=clock,**choose(g,date,clock)))
    p=pd.DataFrame(rows);p.to_parquet(out/'monthly_ttm.parquet',index=False)
    p.groupby(['date','clock','status']).size().rename('rows').reset_index().to_csv(out/'monthly_coverage.csv',index=False)
    a=p[p.clock=='notice'].drop(columns='clock');b=p[p.clock=='update'].drop(columns='clock');paired=a.merge(b,on=['secucode','date'],suffixes=('_notice','_update'),validate='one_to_one')
    paired['both_known']=paired.status_notice.eq('known_ttm')&paired.status_update.eq('known_ttm');paired['both_selected']=paired.report_period_notice.notna()&paired.report_period_update.notna();paired['different_period']=paired.both_selected&paired.report_period_notice.ne(paired.report_period_update);paired['different_known_value']=paired.both_known&paired.ttm_profit_notice.ne(paired.ttm_profit_update)
    paired.to_parquet(out/'clock_pairs.parquet',index=False);paired.groupby(['status_notice','status_update']).size().rename('rows').reset_index().to_csv(out/'transitions.csv',index=False)
    summary=dict(companies=raw.SECUCODE.nunique(),months=len(ends),first_date=str(ends.min().date()),last_date=str(ends.max().date()),monthly_rows=len(p),company_month_pairs=len(paired),statuses=p.groupby(['clock','status']).size().to_dict(),both_known=int(paired.both_known.sum()),both_selected=int(paired.both_selected.sum()),different_period=int(paired.different_period.sum()),different_known_value=int(paired.different_known_value.sum()),strict_PIT=False,price_comparison=False)
    js(out/'summary.json',summary)
    paths +=[Path(__file__),ROOT/'protocols/r116.json',ROOT/'src/common.py'];js(out/'receipt.json',dict(reads={str(x):sha(x) for x in paths},outputs={n:sha(out/n) for n in ['report_events.parquet','monthly_ttm.parquet','monthly_coverage.csv','clock_pairs.parquet','transitions.csv','summary.json']}));print(summary)
if __name__=='__main__':run()
