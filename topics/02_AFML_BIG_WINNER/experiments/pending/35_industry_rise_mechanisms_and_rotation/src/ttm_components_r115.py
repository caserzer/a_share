"""Independent financial-cache TTM ingredients, clocks and explicit unknowns."""
import pandas as pd
from common import *
BASE=Path('/home/xiaolv/.cache/a_share/ep30_d2/releases/aca398170eea902b76749609bd0b8147b8f644fcf55a6a457b3005d58e3931bf/proxy/financials')
COLS=['SECUCODE','SECURITY_CODE','REPORT_DATE','REPORT_TYPE','CURRENCY','PARENTNETPROFIT','NOTICE_DATE','UPDATE_DATE']
TYPES={(3,31):'一季报',(6,30):'中报',(9,30):'三季报',(12,31):'年报'}
def component(g,period):
    if g is None or not len(g):return dict(status='missing_period',value=np.nan,notice=pd.NaT,update=pd.NaT,refs=[])
    valid=period.month in [3,6,9,12] and (period.month,period.day) in TYPES
    status='valid';v=pd.to_numeric(g.PARENTNETPROFIT,errors='coerce')
    if not valid or not g.REPORT_TYPE.eq(TYPES.get((period.month,period.day))).all() or not g.CURRENCY.eq('CNY').all():status='basis_mismatch'
    elif not np.isfinite(v).all():status='missing_value'
    elif v.nunique()!=1:status='conflicting_values'
    notices=pd.to_datetime(g.NOTICE_DATE,errors='coerce');updates=pd.to_datetime(g.UPDATE_DATE,errors='coerce')
    notice=notices.max().normalize() if notices.notna().all() and notices.ge(period).all() else pd.NaT
    update=max(notice,updates.max().normalize()) if pd.notna(notice) and updates.notna().all() else pd.NaT
    return dict(status=status,value=float(v.iloc[0]) if status=='valid' else np.nan,notice=notice,update=update,refs=g.row_id.tolist())
def candidate(code,period,groups,calendar):
    periods=[period] if period.month==12 else [period,pd.Timestamp(period.year-1,12,31),period-pd.DateOffset(years=1)]
    parts=[component(groups.get(x),x) for x in periods];good=all(x['status']=='valid' for x in parts)
    result=dict(secucode=code,report_period=period,formula='annual' if len(parts)==1 else 'current_ytd_plus_prior_annual_minus_prior_ytd',status='valid_components' if good else 'invalid_or_missing_component',ttm_profit=(parts[0]['value'] if len(parts)==1 else parts[0]['value']+parts[1]['value']-parts[2]['value']) if good else np.nan,component_periods=[str(x.date()) for x in periods],component_statuses=[x['status'] for x in parts],component_row_ids=[x['refs'] for x in parts])
    for clock in ['notice','update']:
        date=max(x[clock] for x in parts) if good and all(pd.notna(x[clock]) for x in parts) else pd.NaT
        result[clock+'_proxy_date']=date;idx=calendar.searchsorted(date,side='right') if pd.notna(date) else len(calendar)
        result[clock+'_available_at']=calendar[idx] if idx<len(calendar) else pd.NaT
    return result

def run():
    out=ROOT/'outputs/r115';out.mkdir(exist_ok=True);parts=[];reads={}
    for path in sorted(BASE.glob('*.parquet')):
        f=pd.read_parquet(path,columns=COLS);assert f.SECUCODE.eq(path.stem).all() and f.SECURITY_CODE.astype(str).eq(path.stem.split('.')[0]).all()
        f['source_path']=str(path);f['source_row']=np.arange(len(f));f['row_id']=path.name+':'+f.source_row.astype(str);parts.append(f);reads[str(path)]=sha(path)
    raw=pd.concat(parts,ignore_index=True);raw.to_parquet(out/'financial_rows.parquet',index=False)
    calpath=CACHE/'forecast_v5/CSI_ALL.parquet';calendar=pd.DatetimeIndex(pd.read_parquet(calpath).index).sort_values();rows=[]
    for code,g in raw.groupby('SECUCODE'):
        groups={pd.Timestamp(k):v for k,v in g.groupby(pd.to_datetime(g.REPORT_DATE))}
        for period in sorted(groups):
            if 2020<=period.year<=2026:rows.append(candidate(code,period,groups,calendar))
    result=pd.DataFrame(rows);result.to_parquet(out/'ttm_candidates.parquet',index=False)
    coverage=result.assign(year=result.report_period.dt.year,notice_ready=result.notice_available_at.notna(),update_ready=result.update_available_at.notna()).groupby(['year','formula','status']).agg(periods=('secucode','size'),notice_ready=('notice_ready','sum'),update_ready=('update_ready','sum')).reset_index();coverage.to_csv(out/'coverage.csv',index=False)
    summary=dict(partitions=len(parts),raw_rows=len(raw),companies=raw.SECUCODE.nunique(),candidate_periods=len(result),valid_components=int(result.status.eq('valid_components').sum()),notice_clock_ready=int(result.notice_available_at.notna().sum()),update_clock_ready=int(result.update_available_at.notna().sum()),update_later_than_notice=int((result.update_proxy_date>result.notice_proxy_date).sum()),negative_ttm=int(result.ttm_profit.lt(0).sum()),zero_ttm=int(result.ttm_profit.eq(0).sum()),strict_PIT=False,price_comparison=False)
    js(out/'summary.json',summary)
    for path in [calpath,Path(__file__),ROOT/'protocols/r115.json',ROOT/'src/common.py']:reads[str(path)]=sha(path)
    js(out/'receipt.json',dict(reads=reads,outputs={n:sha(out/n) for n in ['financial_rows.parquet','ttm_candidates.parquet','coverage.csv','summary.json']}));print(summary)
if __name__=='__main__':run()
