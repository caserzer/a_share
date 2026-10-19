"""R29 past-only global-risk features and explicit source availability assumptions."""
import hashlib
import io
import json
import re
import warnings
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from prepare_panel import EP,OUT
from build_margin_information import digest
from download_global_risk import CACHE,URLS

DEST=OUT/'r29_global_risk'
SOURCE=OUT/'local_cache/historical_peer_panel.parquet'
PANEL=OUT/'local_cache/global_risk_panel.parquet'
MONTHLY=CACHE/'monthly_features.parquet'
RISK=['global_log_vix','global_vix_change21','global_vix_term','global_nasdaq_mom21',
      'global_nasdaq_mom63','global_nasdaq_mom126','global_nasdaq_vol63']
MACRO=['global_us10y','global_us10y_change63','global_us_slope','global_usdcny_mom21','global_usdcny_mom63']
LAGS={'vix':3,'nasdaq':3,'yields':7,'fx':14}


def clean(frame,positive=True):
    frame=frame.copy();frame.index=pd.DatetimeIndex(frame.index).astype('datetime64[ns]')
    assert not frame.index.duplicated().any()
    frame=frame.sort_index().loc['2016-01-01':'2026-04-30']
    assert not np.isinf(frame.to_numpy(dtype=float)).any()
    if positive:assert (frame.dropna()>0).all().all()
    return frame


def read_sources():
    receipts=[]
    for name in URLS:
        path=CACHE/name;rp=path.with_suffix('.receipt.json');r=json.loads(rp.read_text())
        assert r['status']==200 and digest(path)==r['sha256']
        receipts.append(dict(path=str(path),receipt_path=str(rp),receipt_sha256=digest(rp),**r))
    vix=[]
    for name,ext in [('VIX','csv'),('VIX3M','body')]:
        x=pd.read_csv(CACHE/f'{name}.{ext}')
        assert set(['DATE','OPEN','HIGH','LOW','CLOSE']).issubset(x.columns)
        frame=pd.DataFrame({name:x.CLOSE.to_numpy()},index=pd.to_datetime(x.DATE,format='%m/%d/%Y'))
        vix.append(clean(frame))
    volatility=vix[0].join(vix[1],how='inner').dropna()
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore',message='pkg_resources is deprecated')
        from py_mini_racer import py_mini_racer
        from akshare.stock.cons import zh_js_decode
    raw=(CACHE/'NASDAQ_SINA.body').read_text()
    match=re.fullmatch(r'\s*var KLC_K2_\$IXIC="([^\"]+)";?\s*',raw)
    assert match
    js=py_mini_racer.MiniRacer();js.eval(zh_js_decode)
    x=pd.DataFrame(js.call('d',match.group(1)))
    dates=pd.to_datetime(x.date,utc=True).dt.tz_localize(None).dt.normalize()
    nasdaq=clean(pd.DataFrame({'NASDAQ':x.close.to_numpy()},index=dates))
    fx_table=pd.read_html(io.StringIO((CACHE/'FX_FED_HTML.body').read_text()))[0]
    assert list(fx_table.columns)==['Date','Rate']
    numeric=pd.to_numeric(fx_table.Rate,errors='coerce')
    assert fx_table.loc[numeric.isna(),'Rate'].eq('ND').all()
    fx=clean(pd.DataFrame({'USDCNY':numeric.to_numpy()},index=pd.to_datetime(fx_table.Date,format='%d-%b-%y'))).dropna()
    assert fx.USDCNY.between(4,10).all()
    years=[];coverage=[]
    for year in range(2016,2027):
        root=ET.fromstring((CACHE/f'TREASURY_{year}.body').read_bytes())
        props=root.findall('.//{http://schemas.microsoft.com/ado/2007/08/dataservices/metadata}properties')
        records=[{e.tag.split('}')[-1]:e.text for e in node} for node in props]
        x=pd.DataFrame(records);date=pd.to_datetime(x.NEW_DATE)
        assert date.dt.year.eq(year).all() and not date.duplicated().any()
        assert (240<=len(x)<=270) if year<2026 else (80<=len(x)<=270)
        frame=pd.DataFrame({'US2Y':pd.to_numeric(x.BC_2YEAR).to_numpy()/100,
                            'US10Y':pd.to_numeric(x.BC_10YEAR).to_numpy()/100},index=date)
        assert frame.notna().all().all() and frame.ge(0).all().all() and frame.le(.2).all().all()
        years.append(frame);coverage.append(dict(year=year,rows=len(frame)))
    yields=clean(pd.concat(years),positive=False)
    sources=dict(vix=volatility,nasdaq=nasdaq,yields=yields,fx=fx)
    return sources,receipts,coverage,hashlib.sha256(zh_js_decode.encode()).hexdigest()


def observed_features(sources):
    v=sources['vix'];n=sources['nasdaq'].NASDAQ;r=sources['yields'];f=sources['fx'].USDCNY
    return dict(vix=pd.DataFrame({'global_log_vix':np.log(v.VIX),'global_vix_change21':np.log(v.VIX/v.VIX.shift(21)),
                                 'global_vix_term':np.log(v.VIX/v.VIX3M)}),
        nasdaq=pd.DataFrame({**{f'global_nasdaq_mom{k}':n/n.shift(k)-1 for k in [21,63,126]},
                            'global_nasdaq_vol63':n.pct_change(fill_method=None).rolling(63).std()*np.sqrt(252)}),
        yields=pd.DataFrame({'global_us10y':r.US10Y,'global_us10y_change63':r.US10Y-r.US10Y.shift(63),
                             'global_us_slope':r.US10Y-r.US2Y}),
        fx=pd.DataFrame({f'global_usdcny_mom{k}':f/f.shift(k)-1 for k in [21,63]}))


def align_available(features,origins,lag,group):
    valid=features.dropna().sort_index().copy()
    valid[f'{group}_observation_date']=valid.index
    valid[f'{group}_available_date']=valid.index+pd.Timedelta(days=lag)
    valid=valid.reset_index(drop=True)
    dates=pd.DataFrame({'date':pd.DatetimeIndex(origins).astype('datetime64[ns]')}).sort_values('date')
    joined=pd.merge_asof(dates,valid,left_on='date',right_on=f'{group}_available_date',direction='backward',tolerance=pd.Timedelta(days=7))
    if joined[list(features.columns)].isna().any().any():raise ValueError(f'Missing or stale {group} observations')
    assert joined[f'{group}_available_date'].le(joined.date).all()
    assert joined[f'{group}_observation_date'].le(joined.date-pd.Timedelta(days=lag)).all()
    return joined.set_index('date')


def monthly_features(sources,origins):
    return pd.concat([align_available(frame,origins,LAGS[name],name) for name,frame in observed_features(sources).items()],axis=1)


def build():
    DEST.mkdir(exist_ok=True)
    sources,receipts,coverage,decoder_hash=read_sources()
    source_audit=json.loads((OUT/'r25_historical_peers/feature_audit.json').read_text())
    assert digest(SOURCE)==source_audit['feature_sha256']
    panel=pd.read_parquet(SOURCE);origins=sorted(panel.date.unique());monthly=monthly_features(sources,origins)
    prefixes=[]
    for date in [pd.Timestamp('2019-01-31'),pd.Timestamp('2021-01-29'),pd.Timestamp('2026-04-30')]:
        truncated={k:v.loc[:date-pd.Timedelta(days=LAGS[k])] for k,v in sources.items()}
        actual=monthly_features(truncated,[date])
        pd.testing.assert_frame_equal(actual,monthly.loc[[date]],check_freq=False)
        prefixes.append(str(date.date()))
    for name,frame in sources.items():frame.to_parquet(CACHE/f'normalized_{name}.parquet')
    monthly.to_parquet(MONTHLY)
    result=panel.join(monthly,on='date',validate='many_to_one')
    pd.testing.assert_frame_equal(result[panel.columns],panel)
    assert np.isfinite(result[RISK+MACRO]).all().all()
    result.to_parquet(PANEL,index=False)
    audit=dict(technical_feature_integrity_passed=True,source_sha256=digest(SOURCE),feature_sha256=digest(PANEL),
        plan_sha256=digest(EP/'notes/r29_global_risk.md'),monthly_sha256=digest(MONTHLY),decoder_sha256=decoder_hash,
        rows=len(panel),months=len(monthly),evaluation_rows=int(panel.date.ge('2021-01-01').sum()),
        all_new_features_available=True,lags_calendar_days=LAGS,max_extra_age_days=7,prefix_dates=prefixes,
        source_receipts=receipts,treasury_year_coverage=coverage,
        normalized_receipts=[dict(path=str(CACHE/f'normalized_{n}.parquet'),sha256=digest(CACHE/f'normalized_{n}.parquet')) for n in sources],
        limitation='Conservative calendar lags, not original-vintage certification; Nasdaq uses Sina redistributed history; FRED downloads timed out.')
    (DEST/'feature_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    monthly.reset_index().to_csv(DEST/'monthly_feature_audit.csv',index=False)
    print(json.dumps({k:audit[k] for k in ['rows','months','evaluation_rows','all_new_features_available','prefix_dates']},indent=2))


if __name__=='__main__':build()
