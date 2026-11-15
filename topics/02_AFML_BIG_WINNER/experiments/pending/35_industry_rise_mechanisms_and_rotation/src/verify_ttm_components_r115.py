"""Independent financial-row, TTM ingredient arithmetic and proxy clock audit."""
import pandas as pd
from common import *
def run():
    out=ROOT/'outputs/r115';receipt=json.loads((out/'receipt.json').read_text())
    for p,h in receipt['reads'].items():assert sha(p)==h
    for p,h in receipt['outputs'].items():assert sha(out/p)==h
    raw=pd.read_parquet(out/'financial_rows.parquet');result=pd.read_parquet(out/'ttm_candidates.parquet');assert raw.row_id.is_unique and not result.duplicated(['secucode','report_period']).any()
    cols=['SECUCODE','SECURITY_CODE','REPORT_DATE','REPORT_TYPE','CURRENCY','PARENTNETPROFIT','NOTICE_DATE','UPDATE_DATE'];checked=0
    for path,g in raw.groupby('source_path'):
        f=pd.read_parquet(path,columns=cols);pd.testing.assert_frame_equal(g.sort_values('source_row')[cols].reset_index(drop=True),f.reset_index(drop=True),check_dtype=False,check_exact=True);assert g.source_row.tolist()==list(range(len(f)))
        assert g.SECUCODE.eq(Path(path).stem).all() and g.SECURITY_CODE.astype(str).eq(Path(path).stem.split('.')[0]).all();assert g.row_id.tolist()==[Path(path).name+':'+str(i) for i in range(len(f))];checked+=len(f)
    assert checked==len(raw)
    groups={(code,pd.Timestamp(period)):g for (code,period),g in raw.groupby(['SECUCODE',pd.to_datetime(raw.REPORT_DATE)])}
    wanted={(code,period) for code,period in groups if 2020<=period.year<=2026};assert wanted==set(zip(result.secucode,result.report_period))
    calendar=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index).sort_values();types={(3,31):'一季报',(6,30):'中报',(9,30):'三季报',(12,31):'年报'}
    for row in result.itertuples():
        t=row.report_period;ps=[t] if t.month==12 else [t,pd.Timestamp(t.year-1,12,31),pd.Timestamp(t.year-1,t.month,t.day)];statuses=[];refs=[];values=[];notice=[];updates=[]
        for p in ps:
            g=groups.get((row.secucode,p));st='valid';v=np.nan;nd=ud=pd.NaT;ids=[]
            if g is None:st='missing_period'
            else:
                ids=g.row_id.tolist();vals=pd.to_numeric(g.PARENTNETPROFIT,errors='coerce')
                if (p.month,p.day) not in types or not g.REPORT_TYPE.eq(types.get((p.month,p.day))).all() or not g.CURRENCY.eq('CNY').all():st='basis_mismatch'
                elif not np.isfinite(vals).all():st='missing_value'
                elif len(set(vals))!=1:st='conflicting_values'
                else:v=float(vals.iloc[0])
                ns=pd.to_datetime(g.NOTICE_DATE,errors='coerce');us=pd.to_datetime(g.UPDATE_DATE,errors='coerce')
                if ns.notna().all() and ns.ge(p).all():
                    nd=max(ns).normalize()
                    if us.notna().all():ud=max(nd,max(us).normalize())
            statuses.append(st);refs.append(ids);values.append(v);notice.append(nd);updates.append(ud)
        assert list(row.component_periods)==[str(p.date()) for p in ps] and list(row.component_statuses)==statuses
        assert [list(v) for v in row.component_row_ids]==refs
        valid=all(x=='valid' for x in statuses);assert row.status==('valid_components' if valid else 'invalid_or_missing_component')
        value=(values[0] if len(values)==1 else sum(values[:2])-values[2]) if valid else np.nan
        np.testing.assert_allclose(value,row.ttm_profit,rtol=1e-12,atol=1e-6,equal_nan=True)
        assert row.formula==('annual' if len(ps)==1 else 'current_ytd_plus_prior_annual_minus_prior_ytd')
        for clock,dates in [('notice',notice),('update',updates)]:
            proxy=max(dates) if valid and all(pd.notna(d) for d in dates) else pd.NaT;eligible=calendar[calendar>proxy] if pd.notna(proxy) else [];available=eligible[0] if len(eligible) else pd.NaT
            for suffix,value in [('proxy_date',proxy),('available_at',available)]:
                actual=getattr(row,clock+'_'+suffix);assert (pd.isna(value) and pd.isna(actual)) or actual==value
    c=pd.read_csv(out/'coverage.csv');expected=result.assign(year=result.report_period.dt.year,notice_ready=result.notice_available_at.notna(),update_ready=result.update_available_at.notna()).groupby(['year','formula','status']).agg(periods=('secucode','size'),notice_ready=('notice_ready','sum'),update_ready=('update_ready','sum')).reset_index();pd.testing.assert_frame_equal(c,expected,check_dtype=False)
    s=json.loads((out/'summary.json').read_text());counts=dict(partitions=raw.source_path.nunique(),raw_rows=len(raw),companies=raw.SECUCODE.nunique(),candidate_periods=len(result),valid_components=int(result.ttm_profit.notna().sum()),notice_clock_ready=int(result.notice_available_at.notna().sum()),update_clock_ready=int(result.update_available_at.notna().sum()),update_later_than_notice=int((result.update_proxy_date>result.notice_proxy_date).sum()),negative_ttm=int(result.ttm_profit.lt(0).sum()),zero_ttm=int(result.ttm_profit.eq(0).sum()))
    for k,v in counts.items():assert s[k]==v
    assert s['strict_PIT']==s['price_comparison']==False
    js(out/'verification.json',dict(status='PASS',source_rows=len(raw),candidate_periods=len(result),valid_components=counts['valid_components'],strict_PIT=False,monthly_latest_selection_verified=False));print('PASS',counts)
if __name__=='__main__':run()
