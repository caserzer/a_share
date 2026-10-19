"""R31 reported financial quality, conservative availability and exact-year deltas."""
import json
import re
import numpy as np
import pandas as pd
from prepare_panel import EP,OUT
from build_margin_information import digest

DEST=OUT/'r31_financial_quality'
CACHE=OUT/'local_cache/r31_financial_quality'
SOURCE=OUT/'local_cache/historical_peer_panel.parquet'
PANEL=OUT/'local_cache/financial_quality_panel.parquet'
META=['fq_quarter','fq_age_days']
BASIC=['fq_roe','fq_profit_growth','fq_revenue_growth','fq_debt_ratio','fq_ocf_eps']
QUALITY=['fq_core_roe','fq_gross_margin','fq_core_margin','fq_nonrecurring_margin','fq_ocf_book',
         'fq_cash_earnings_gap_book','fq_current_ratio','fq_quick_ratio','fq_core_growth']
DELTA_SOURCES=['fq_core_roe','fq_gross_margin','fq_nonrecurring_margin','fq_cash_earnings_gap_book','fq_core_growth']
CHANGES=[c+'_annual_change' for c in DELTA_SOURCES]+['fq_prior_available']
GROUPS={'basic':META+BASIC,'levels':META+BASIC+QUALITY,'changes':META+BASIC+QUALITY+CHANGES}
FIELDS=['ROEJQ','PARENTNETPROFITTZ','TOTALOPERATEREVETZ','ZCFZL','EPSJB','MGJYXJJE','BPS','ROEKCJQ','XSMLL',
        'KCFJCXSYJLR','PARENTNETPROFIT','TOTALOPERATEREVE','LD','SD','KCFJCXSYJLRTZ']


def prepare_reports(frame):
    f=frame.copy()
    for c in ['REPORT_DATE','NOTICE_DATE','UPDATE_DATE']:f[c]=pd.to_datetime(f[c],errors='coerce')
    f=f.dropna(subset=['REPORT_DATE','NOTICE_DATE','UPDATE_DATE'])
    f=f[f.REPORT_DATE.le(f.NOTICE_DATE)&f.CURRENCY.eq('CNY')].copy()
    f['available_date']=f[['NOTICE_DATE','UPDATE_DATE']].max(axis=1)
    assert not f.duplicated(['REPORT_DATE','available_date']).any()
    for c in FIELDS:f[c]=pd.to_numeric(f[c],errors='coerce').replace([np.inf,-np.inf],np.nan)
    return f.sort_values(['REPORT_DATE','available_date'],kind='stable').reset_index(drop=True)


def ratios(row):
    def value(c):return float(row[c]) if pd.notna(row[c]) else np.nan
    def divide(a,b,minimum=0.):return a/b if np.isfinite(a) and np.isfinite(b) and b>minimum else np.nan
    eps=value('EPSJB');ocf=value('MGJYXJJE');book=value('BPS');revenue=value('TOTALOPERATEREVE')
    parent=value('PARENTNETPROFIT');core=value('KCFJCXSYJLR')
    result={new:value(old)/100 for old,new in [('ROEJQ','fq_roe'),('PARENTNETPROFITTZ','fq_profit_growth'),
        ('TOTALOPERATEREVETZ','fq_revenue_growth'),('ZCFZL','fq_debt_ratio'),('ROEKCJQ','fq_core_roe'),
        ('XSMLL','fq_gross_margin'),('KCFJCXSYJLRTZ','fq_core_growth')]}
    result.update(fq_ocf_eps=ocf/eps if np.isfinite(ocf) and np.isfinite(eps) and abs(eps)>.01 else np.nan,
        fq_core_margin=divide(core,revenue),fq_nonrecurring_margin=divide(parent-core,revenue),
        fq_ocf_book=divide(ocf,book,.01),fq_cash_earnings_gap_book=divide(ocf-eps,book,.01),
        fq_current_ratio=value('LD'),fq_quick_ratio=value('SD'))
    return result


def select_features(reports,date):
    result={c:np.nan for c in META+BASIC+QUALITY+CHANGES}
    result['fq_prior_available']=0.
    result.update(fq_report_date=pd.NaT,fq_available_date=pd.NaT,fq_prior_report_date=pd.NaT,fq_prior_available_date=pd.NaT)
    eligible=reports[reports.available_date<date]
    if eligible.empty:return result
    current=eligible.iloc[-1];age=(date-current.REPORT_DATE).days
    if age>456:return result
    assert age>=0
    result.update(ratios(current));result.update(fq_quarter=float(current.REPORT_DATE.quarter),fq_age_days=float(age),
        fq_report_date=current.REPORT_DATE,fq_available_date=current.available_date)
    previous_date=current.REPORT_DATE-pd.DateOffset(years=1)
    previous=eligible[eligible.REPORT_DATE.eq(previous_date)]
    if not previous.empty:
        prior=previous.iloc[-1];values=ratios(prior)
        result.update(fq_prior_available=1.,fq_prior_report_date=prior.REPORT_DATE,fq_prior_available_date=prior.available_date)
        for c in DELTA_SOURCES:result[c+'_annual_change']=result[c]-values[c]
    return result


def build():
    DEST.mkdir(exist_ok=True);CACHE.mkdir(exist_ok=True)
    source_audit=json.loads((OUT/'r25_historical_peers/feature_audit.json').read_text());assert digest(SOURCE)==source_audit['feature_sha256']
    panel=pd.read_parquet(SOURCE);features=[];receipts=[];prefixes=[];total_reports=0
    for instrument,g in panel.groupby('instrument',sort=True):
        path=OUT/f'local_cache/public_financials/{instrument[2:]}.{instrument[:2]}.parquet'
        assert path.exists();raw=pd.read_parquet(path);f=prepare_reports(raw);total_reports+=len(raw)
        receipts.append(dict(path=str(path),sha256=digest(path),raw_rows=len(raw),eligible_records=len(f)))
        for idx,row in g.iterrows():features.append(dict(source_index=idx,**select_features(f,row.date)))
        if instrument in ['SH600519','SZ000001','SH600000','SZ300001']:
            for date in sorted(g.date.unique())[::max(1,len(g)//3)]:
                date=pd.Timestamp(date);prefix=f[f.available_date<date].copy()
                a=pd.Series(select_features(f,date));b=pd.Series(select_features(prefix,date));pd.testing.assert_series_equal(a,b)
                prefixes.append(dict(instrument=instrument,date=str(date.date()),visible_records=len(prefix)))
    extra=pd.DataFrame(features).set_index('source_index').reindex(panel.index);extra.index.name=None
    for c in ['fq_report_date','fq_available_date','fq_prior_report_date','fq_prior_available_date']:extra[c]=pd.to_datetime(extra[c])
    result=pd.concat([panel,extra],axis=1);pd.testing.assert_frame_equal(result[panel.columns],panel)
    # Old panel retains stale reports; compare only the predeclared <=456-day window.
    fresh=(panel.date-pd.to_datetime(panel.financial_report_date)).dt.days.le(456)
    pd.testing.assert_series_equal(pd.to_datetime(result.fq_report_date).astype('datetime64[ns]'),pd.to_datetime(panel.financial_report_date.where(fresh)).astype('datetime64[ns]'),check_names=False)
    pd.testing.assert_series_equal(pd.to_datetime(result.fq_available_date).astype('datetime64[ns]'),pd.to_datetime(panel.financial_available_date.where(fresh)).astype('datetime64[ns]'),check_names=False)
    for new,old,factor in [('fq_roe','roe',100),('fq_profit_growth','profit_growth',100),('fq_revenue_growth','revenue_growth',100),
                           ('fq_debt_ratio','debt_ratio',100),('fq_ocf_eps','ocf_eps_ratio',1)]:
        np.testing.assert_allclose(result[new]*factor,panel[old].where(fresh),atol=1e-10,rtol=1e-10,equal_nan=True)
    assert result.loc[fresh,'fq_available_date'].lt(result.loc[fresh,'date']).all() and result.loc[fresh,'fq_age_days'].le(456).all()
    assert result.loc[~fresh,META+BASIC+QUALITY].isna().all().all()
    paired=result.fq_prior_available.eq(1)
    assert result.loc[paired,'fq_prior_available_date'].lt(result.loc[paired,'date']).all()
    assert not np.isinf(result[META+BASIC+QUALITY+CHANGES]).any().any()
    result.to_parquet(PANEL,index=False)
    coverage=result.assign(period=np.where(result.date.ge('2021-01-01'),'evaluation','training')).groupby('period')[META+BASIC+QUALITY+CHANGES].agg(lambda x:x.notna().mean())
    coverage.to_csv(DEST/'coverage.csv')
    page=CACHE/'finance_page.html';html=page.read_text();unit_map={}
    for field in ['ROEJQ','ROEKCJQ','KCFJCXSYJLR','EPSJB','MGJYXJJE','BPS','XSMLL','ZCFZL','TOTALOPERATEREVETZ','KCFJCXSYJLRTZ','LD','SD']:
        pos=html.find('value.'+field);assert pos>=0;start=html.rfind('<tr',0,pos);end=html.find('</tr>',pos)
        unit_map[field]=re.sub(r'\s+',' ',re.sub('<[^>]+>',' ',html[start:end])).strip()
    (DEST/'source_units.json').write_text(json.dumps(dict(url='https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?code=SH600519&type=web',
        page_sha256=digest(page),fields=unit_map),ensure_ascii=False,indent=2)+'\n')
    audit=dict(technical_feature_integrity_passed=True,source_sha256=digest(SOURCE),feature_sha256=digest(PANEL),
        plan_sha256=digest(EP/'notes/r31_financial_quality.md'),rows=len(result),stocks=len(receipts),source_report_rows=total_reports,
        evaluation_rows=int(result.date.ge('2021-01-01').sum()),evaluation_prior_report_coverage=float(result.loc[result.date.ge('2021-01-01'),'fq_prior_available'].mean()),
        fresh_basics_and_report_dates_match_original=True,stale_rows_masked=int((~fresh).sum()),fresh_report_coverage=float(fresh.mean()),prefix_checks=prefixes,receipts=receipts,
        units_file_sha256=digest(DEST/'source_units.json'),page_sha256=digest(page),
        limitation='max(notice,update) strictly prior; latest vendor rows not original filing vintages; per-share cash/book ratios are proxies.')
    (DEST/'feature_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps({k:audit[k] for k in ['rows','stocks','source_report_rows','evaluation_rows','evaluation_prior_report_coverage']},indent=2));print(coverage.round(4).to_string())


if __name__=='__main__':build()
