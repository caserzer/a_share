"""R36 announcement-aware holder-count features with independently known comparisons."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from prepare_panel import EP,OUT,DATA
from build_joint_information import SOURCE
from build_margin_information import digest
from download_holder_counts import DEST
PANEL=OUT/'local_cache/holder_count_panel.parquet'
META=['hc_age_days','hc_publication_lag']
LEVEL=['hc_log_count']
CHANGE=['hc_log_change','hc_change_gap','hc_year_change','hc_year_gap']
FEATURES=META+LEVEL+CHANGE
GROUPS={'level':META+LEVEL,'change':META+CHANGE,'both':FEATURES}
BOUNDARIES=DEST/'price_history_boundaries.json'


def build_boundaries():
    if BOUNDARIES.exists():return
    rows=[]
    for stock in sorted(pd.read_parquet(SOURCE).instrument.unique()):
        path=DATA/f'raw/akshare/day/raw/{stock}.csv'
        bars=pd.read_csv(path,usecols=['date','close']);dates=pd.to_datetime(bars.loc[bars.close.gt(0),'date'])
        assert len(dates) and not dates.duplicated().any()
        rows.append(dict(instrument=stock,code=stock[2:],first_price_date=str(dates.min().date()),path=str(path),sha256=digest(path)))
    BOUNDARIES.write_text(json.dumps(dict(source_panel_sha256=digest(SOURCE),receipts=rows,
        meaning='Earliest positive close in existing raw history; conservative coverage boundary, not a certified IPO date.'),indent=2)+'\n')


def restrict_price_history(raw,boundaries):
    result=raw.copy();result['hc_price_history_start']=result.SECURITY_CODE.map(boundaries)
    assert result.hc_price_history_start.notna().all()
    return result[result.END_DATE.ge(result.hc_price_history_start)].copy()


def read_sources():
    manifest=json.loads((DEST/'source_manifest.json').read_text());assert manifest['failed']==0
    assert manifest['source_panel_sha256']==digest(SOURCE)
    rows=[]
    for source in manifest['results']:
        assert source['status'] in ['complete','source_no_records']
        for receipt in source['pages']:
            path=Path(receipt['path']);assert digest(path)==receipt['sha256'];payload=json.loads(path.read_text())
            if source['status']=='source_no_records':
                assert payload['code']==9201 and payload['message']=='返回数据为空' and payload['result'] is None
            else:
                assert payload['success'];rows.extend(payload['result']['data'])
    raw=pd.DataFrame(rows)
    for col in ['END_DATE','HOLD_NOTICE_DATE']:raw[col]=pd.to_datetime(raw[col])
    assert not raw.duplicated(['SECURITY_CODE','END_DATE']).any()
    assert raw[['END_DATE','HOLD_NOTICE_DATE','HOLDER_NUM']].notna().all().all() and raw.HOLDER_NUM.gt(0).all()
    boundary=json.loads(BOUNDARIES.read_text());assert boundary['source_panel_sha256']==digest(SOURCE)
    for r in boundary['receipts']:assert digest(Path(r['path']))==r['sha256']
    starts={r['code']:pd.Timestamp(r['first_price_date']) for r in boundary['receipts']}
    restricted=restrict_price_history(raw,starts).sort_values(['SECURITY_CODE','END_DATE','HOLD_NOTICE_DATE']).reset_index(drop=True)
    restricted.attrs['before_price_history_excluded']=len(raw)-len(restricted)
    return restricted


def at_date(history,date):
    result={c:np.nan for c in FEATURES}
    for prefix in ['current','previous','year']:
        result.update({f'hc_{prefix}_end':pd.NaT,f'hc_{prefix}_notice':pd.NaT,f'hc_{prefix}_count':np.nan})
    known=history[history.HOLD_NOTICE_DATE.lt(date)&history.HOLD_NOTICE_DATE.ge(history.END_DATE)&history.HOLDER_NUM.gt(0)]
    if not len(known):return result
    known=known.sort_values(['END_DATE','HOLD_NOTICE_DATE']);current=known.iloc[-1]
    def record(row,prefix):
        result.update({f'hc_{prefix}_end':row.END_DATE,f'hc_{prefix}_notice':row.HOLD_NOTICE_DATE,f'hc_{prefix}_count':float(row.HOLDER_NUM)})
    record(current,'current');age=(date-current.END_DATE).days
    if not 0<=age<=180:return result
    result.update(hc_age_days=float(age),hc_publication_lag=float((current.HOLD_NOTICE_DATE-current.END_DATE).days),hc_log_count=float(np.log(current.HOLDER_NUM)))
    prior=known[known.END_DATE.lt(current.END_DATE)]
    if len(prior):
        previous=prior.iloc[-1];gap=(current.END_DATE-previous.END_DATE).days
        if 1<=gap<=370:
            record(previous,'previous');result.update(hc_log_change=float(np.log(current.HOLDER_NUM/previous.HOLDER_NUM)),hc_change_gap=float(gap))
        gaps=(current.END_DATE-prior.END_DATE).dt.days
        year=prior[gaps.between(305,425)].copy()
        if len(year):
            year['distance']=((current.END_DATE-year.END_DATE).dt.days-365).abs()
            previous=year.sort_values(['distance','END_DATE'],ascending=[True,False]).iloc[0]
            record(previous,'year');result.update(hc_year_change=float(np.log(current.HOLDER_NUM/previous.HOLDER_NUM)),hc_year_gap=float((current.END_DATE-previous.END_DATE).days))
    return result


def feature_frame(original,raw):
    rows=[]
    for stock,g in original.groupby('instrument',sort=True):
        history=raw[raw.SECURITY_CODE.eq(stock[2:])]
        for date in g.date:rows.append(dict(date=date,instrument=stock,**at_date(history,date)))
    features=pd.DataFrame(rows)
    result=original.merge(features,on=['date','instrument'],how='left',sort=False,validate='one_to_one')
    pd.testing.assert_frame_equal(result[original.columns],original)
    return result


def build():
    DEST.mkdir(exist_ok=True);build_boundaries();original=pd.read_parquet(SOURCE);raw=read_sources()
    coverage=json.loads((DEST/'availability_audit.json').read_text());assert coverage['technical_source_and_availability_checks_passed']
    assert coverage['source_manifest_sha256']==digest(DEST/'source_manifest.json')
    filings=json.loads((DEST/'filing_crosschecks.json').read_text());assert filings['all_four_counts_match']
    for r in filings['checks']:assert digest(Path(r['pdf_path']))==r['pdf_sha256']
    result=feature_frame(original,raw)
    for prefix in ['current','previous','year']:
        assert (result[f'hc_{prefix}_notice'].isna()|result[f'hc_{prefix}_notice'].lt(result.date)).all()
    assert result.hc_age_days.dropna().between(0,180).all()
    assert not np.isinf(result[FEATURES]).any().any()
    available=pd.read_parquet(OUT/'local_cache/holder_count_availability_probe.parquet')
    pd.testing.assert_frame_equal(result[['date','instrument']],available[['date','instrument']])
    boundary=json.loads(BOUNDARIES.read_text());starts={r['instrument']:pd.Timestamp(r['first_price_date']) for r in boundary['receipts']}
    bounds=result.instrument.map(starts);assert bounds.le(result.date).all()
    eligible=available.selected_end.ge(bounds)
    pd.testing.assert_series_equal(result.hc_current_end,available.selected_end.where(eligible),check_names=False)
    pd.testing.assert_series_equal(result.hc_current_notice,available.selected_notice.where(eligible),check_names=False)
    np.testing.assert_allclose(result.hc_current_count,available.selected_count.where(eligible),equal_nan=True)
    np.testing.assert_array_equal(result.hc_log_count.notna(),available.fresh180&eligible)
    for prefix in ['current','previous','year']:
        assert (result[f'hc_{prefix}_end'].isna()|result[f'hc_{prefix}_end'].ge(bounds)).all()
    prefixes=['2021-01-29','2022-06-30','2024-01-31','2026-04-30']
    for stamp in prefixes:
        date=pd.Timestamp(stamp);base=original[original.date.eq(date)].reset_index(drop=True)
        cut=raw[raw.HOLD_NOTICE_DATE.lt(date)]
        rebuilt=feature_frame(base,cut)
        pd.testing.assert_frame_equal(rebuilt,result[result.date.eq(date)].reset_index(drop=True))
    result.to_parquet(PANEL,index=False)
    test=result[result.date.ge('2021-01-01')];assert len(test)==27600
    test.groupby(test.date.dt.year)[FEATURES].agg(lambda x:x.notna().mean()).to_csv(DEST/'feature_coverage.csv')
    audit=dict(technical_feature_integrity_passed=True,source_sha256=digest(SOURCE),feature_sha256=digest(PANEL),
        plan_sha256=digest(EP/'notes/r36_holder_counts.md'),source_manifest_sha256=digest(DEST/'source_manifest.json'),
        availability_audit_sha256=digest(DEST/'availability_audit.json'),filing_checks_sha256=digest(DEST/'filing_crosschecks.json'),
        price_boundaries_sha256=digest(BOUNDARIES),before_price_history_excluded=raw.attrs['before_price_history_excluded'],
        original_rows=len(result),evaluation_rows=len(test),features=FEATURES,groups=GROUPS,prefix_checks=prefixes,
        test_feature_coverage={c:float(test[c].notna().mean()) for c in FEATURES},
        limitation='Vendor shareholder counts and dated historical records, not immutable vintages or a measure of institutional flows. No-record stocks and stale observations stay missing; no outcome filtering.')
    (DEST/'feature_audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit,indent=2))


if __name__=='__main__':build()
