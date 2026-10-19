"""Conservatively lagged monthly activity, inflation and broad financing proxies."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from prepare_panel import OUT,EP
from download_domestic_macro import DEST,CACHE,SOURCES
from build_margin_information import digest
SOURCE=OUT/'local_cache/historical_peer_panel.parquet'
PANEL=OUT/'local_cache/domestic_macro_panel.parquet'
MONTHLY=CACHE/'monthly_features.parquet'
LAG_DAYS=45
ACTIVITY=['macro_pmi','macro_pmi_change3','macro_nonmanufacturing','macro_nonmanufacturing_change3',
          'macro_cpi','macro_cpi_change3','macro_ppi','macro_ppi_change3','macro_ppi_cpi_gap']
CREDIT=['macro_m2_yoy','macro_m2_change3','macro_tsf_to_m2','macro_tsf_to_m2_change3','macro_tsf_ttm_growth']
GROUPS={'activity':ACTIVITY,'credit':CREDIT,'both':ACTIVITY+CREDIT}
FIELDS={'RPT_ECONOMY_PMI':{'MAKE_INDEX':'pmi','NMAKE_INDEX':'nonmanufacturing'},
        'RPT_ECONOMY_CURRENCY_SUPPLY':{'BASIC_CURRENCY':'m2_stock','BASIC_CURRENCY_SAME':'m2_yoy'},
        'RPT_ECONOMY_CPI':{'NATIONAL_SAME':'cpi'},'RPT_ECONOMY_PPI':{'BASE_SAME':'ppi'}}

def read_sources():
    manifest=json.loads((DEST/'source_manifest.json').read_text());parts=[];coverage=[]
    for item in manifest['series']:
        path=Path(item['path']);assert digest(path)==item['sha256']
        data=json.loads(path.read_text());f=pd.DataFrame(data if item['name']=='tsf' else data['result']['data'])
        if item['name']=='tsf':
            f.index=pd.to_datetime(f['date'],format='%Y%m').dt.to_period('M');columns={'tiosfs':'tsf','rmblaon':'tsf_rmb_loan'}
        else:
            f.index=pd.to_datetime(f.REPORT_DATE).dt.to_period('M');columns=FIELDS[item['name']]
        f=f[list(columns)].rename(columns=columns).apply(pd.to_numeric,errors='raise').sort_index();f.index.name='period'
        assert f.index.is_unique and f.index.equals(pd.period_range(f.index.min(),f.index.max(),freq='M',name='period'))
        assert f.notna().all().all() and np.isfinite(f).all().all()
        coverage.append(dict(series=item['name'],first=str(f.index.min()),last=str(f.index.max()),months=len(f)))
        parts.append(f)
    raw=pd.concat(parts,axis=1).sort_index();raw.index.name='period';return raw,coverage

def transform(raw):
    # Explicit monthly index prevents diff/rolling from silently skipping missing months.
    raw=raw.reindex(pd.period_range(raw.index.min(),raw.index.max(),freq='M',name='period'))
    out=pd.DataFrame(index=raw.index)
    for name in ['pmi','nonmanufacturing','cpi','ppi','m2_yoy']:
        v=raw[name]/100
        if name in ['pmi','nonmanufacturing']:v=v-.5
        out['macro_'+name]=v
        target='m2_change3' if name=='m2_yoy' else name+'_change3'
        out['macro_'+target]=v.diff(3)
    out['macro_ppi_cpi_gap']=(raw.ppi-raw.cpi)/100
    flow=raw.tsf.rolling(12,min_periods=12).sum()
    out['macro_tsf_to_m2']=flow/raw.m2_stock.where(raw.m2_stock.gt(0))
    out['macro_tsf_to_m2_change3']=out.macro_tsf_to_m2.diff(3)
    out['macro_tsf_ttm_growth']=flow/flow.shift(12).where(flow.shift(12).gt(0))-1
    out['macro_observation_end']=out.index.to_timestamp(how='end').normalize()
    out['macro_assumed_available_date']=out.macro_observation_end+pd.Timedelta(days=LAG_DAYS)
    return out

def align(raw,dates):
    features=transform(raw).reset_index(drop=True).sort_values('macro_assumed_available_date')
    query=pd.DataFrame({'date':pd.to_datetime(sorted(dates))})
    result=pd.merge_asof(query,features,left_on='date',right_on='macro_assumed_available_date',allow_exact_matches=False)
    return result.set_index('date')

def source_checks(raw):
    checks=[]
    cases=[('2020-12','pmi',51.9,'pmi2020'),('2020-12','nonmanufacturing',55.7,'pmi2020'),
           ('2025-12','pmi',50.1,'pmi2025'),('2025-12','nonmanufacturing',50.2,'pmi2025'),
           ('2025-12','cpi',.8,'cpi2025'),('2025-12','ppi',-1.9,'ppi2025'),
           ('2020-12','m2_yoy',10.1,'money2020'),('2025-08','m2_yoy',8.8,'money2025')]
    for period,col,expected,source in cases:
        actual=float(raw.loc[pd.Period(period),'{}'.format(col)]);assert abs(actual-expected)<1e-9
        checks.append(dict(period=period,field=col,value=actual,official=expected,tolerance=1e-9,url=SOURCES[source]))
    for year,total,loan in [(2020,348600,200300),(2021,313500,199400)]:
        annual=raw[raw.index.year==year];assert len(annual)==12
        for col,expected in [('tsf',total),('tsf_rmb_loan',loan)]:
            actual=float(annual[col].sum());assert abs(actual-expected)<=50
            checks.append(dict(period=str(year),field=col,value=actual,official=expected,tolerance=50,url=SOURCES[f'tsf{year}']))
    return checks

def build():
    DEST.mkdir(exist_ok=True);raw,coverage=read_sources();checks=source_checks(raw)
    original_audit=json.loads((OUT/'r25_historical_peers/feature_audit.json').read_text());assert digest(SOURCE)==original_audit['feature_sha256']
    panel=pd.read_parquet(SOURCE);dates=sorted(panel.date.unique());monthly=align(raw,dates)
    assert monthly[ACTIVITY+CREDIT].notna().all().all() and np.isfinite(monthly[ACTIVITY+CREDIT]).all().all()
    assert monthly.macro_assumed_available_date.lt(monthly.index).all()
    age=(pd.Series(monthly.index,index=monthly.index)-monthly.macro_observation_end).dt.days
    assert age.gt(45).all() and age.le(80).all()
    prefixes=[]
    for stamp in ['2019-01-31','2021-01-29','2024-01-31','2026-04-30']:
        date=pd.Timestamp(stamp);cut=raw[(raw.index.to_timestamp(how='end').normalize()+pd.Timedelta(days=LAG_DAYS))<date]
        got=align(cut,[date]);pd.testing.assert_frame_equal(got,monthly.loc[[date]],check_freq=False);prefixes.append(stamp)
    result=panel.join(monthly,on='date',validate='many_to_one');pd.testing.assert_frame_equal(result[panel.columns],panel)
    monthly.to_parquet(MONTHLY);result.to_parquet(PANEL,index=False)
    pd.DataFrame(coverage).to_csv(DEST/'source_coverage.csv',index=False)
    monthly[['macro_observation_end','macro_assumed_available_date']].assign(age_days=age).to_csv(DEST/'availability_by_month.csv')
    (DEST/'official_crosschecks.json').write_text(json.dumps(checks,indent=2)+'\n')
    audit=dict(technical_feature_integrity_passed=True,feature_sha256=digest(PANEL),source_sha256=digest(SOURCE),monthly_sha256=digest(MONTHLY),
        plan_sha256=digest(EP/'notes/r33_domestic_macro.md'),source_manifest_sha256=digest(DEST/'source_manifest.json'),
        crosschecks_sha256=digest(DEST/'official_crosschecks.json'),rows=len(result),origin_months=len(monthly),evaluation_rows=int(result.date.ge('2021-01-01').sum()),
        all_features_coverage=1.,min_observation_age=int(age.min()),max_observation_age=int(age.max()),prefix_checks=prefixes,source_coverage=coverage,
        lag_days=LAG_DAYS,limitation='45-day availability is conservative assumption, not individually verified release dates; current historical series may contain revisions and TSF scope changes.')
    (DEST/'feature_audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit,indent=2))

if __name__=='__main__':build()
