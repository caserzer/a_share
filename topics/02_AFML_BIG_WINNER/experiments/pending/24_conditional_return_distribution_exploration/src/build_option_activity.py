"""Two-session-lagged, fixed-underlying option activity levels and monthly changes."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from prepare_panel import EP,OUT
from build_joint_information import SOURCE
from build_margin_information import digest
from download_option_activity import DEST,CACHE,CALENDAR,MONTHS,dates_and_panel,parse

PANEL=OUT/'local_cache/option_activity_panel.parquet'
SUFFIXES=['volume_pcr','oi_pcr','turnover','volume_pcr_change1','oi_pcr_change1','volume_pcr_change3','oi_pcr_change3']
FIFTY=['opt50_'+name for name in SUFFIXES]
THREEHUNDRED=['opt300_'+name for name in SUFFIXES]
FEATURES=FIFTY+THREEHUNDRED
GROUPS={'sse50':FIFTY,'both':FEATURES}
PUBLICATION=OUT/'r38_option_activity_probe/publication_crosscheck.json'


def read_sources():
    manifest=json.loads((DEST/'source_manifest.json').read_text())
    assert manifest['complete'] and manifest['source_panel_sha256']==digest(SOURCE)
    assert manifest['calendar_sha256']==digest(CALENDAR) and manifest['month_panel_sha256']==digest(MONTHS)
    assert manifest['lag_trading_sessions']==2 and manifest['plan_sha256']==digest(EP/'notes/r38_option_activity.md')
    original,snapshots=dates_and_panel();assert len(manifest['results'])==len(snapshots)==manifest['expected_snapshots']
    rows=[]
    for source,(origin,date) in zip(manifest['results'],snapshots.items()):
        assert source['status']=='complete' and pd.Timestamp(source['origin'])==origin and pd.Timestamp(source['snapshot'])==date<origin
        path=Path(source['path']);assert digest(path)==source['sha256']
        rows.extend(dict(date=origin,snapshot_date=date,**row) for row in parse(json.loads(path.read_text()),date))
    frame=pd.DataFrame(rows);path=CACHE/'normalized.parquet';assert digest(path)==manifest['normalized_sha256']
    pd.testing.assert_frame_equal(frame,pd.read_parquet(path))
    publication=json.loads(PUBLICATION.read_text());assert publication['all_four_match_published_precision']
    assert digest(Path(publication['pdf']))==publication['pdf_sha256'] and digest(Path(publication['daily_source']))==publication['daily_source_sha256']
    return frame,snapshots


def feature_series(origins,raw):
    output=pd.DataFrame(index=pd.DatetimeIndex(origins,name='date'))
    for code,prefix in [('510050','opt50_'),('510300','opt300_')]:
        frame=raw[raw.code.eq(code)].set_index('date').reindex(output.index)
        output[prefix+'volume_pcr']=np.log(frame.put_volume/frame.call_volume)
        output[prefix+'oi_pcr']=np.log(frame.put_oi/frame.call_oi)
        output[prefix+'turnover']=np.log((frame.call_volume+frame.put_volume)/(frame.call_oi+frame.put_oi))
        for lag in (1,3):
            for kind in ('volume_pcr','oi_pcr'):
                output[prefix+kind+f'_change{lag}']=output[prefix+kind].diff(lag)
    return output[FEATURES].reset_index()


def merge_features(original,features,snapshots):
    result=original.merge(features,on='date',how='left',sort=False,validate='many_to_one')
    result['oa_snapshot_date']=result.date.map(snapshots)
    pd.testing.assert_frame_equal(result[original.columns],original)
    return result


def build():
    original=pd.read_parquet(SOURCE);raw,snapshots=read_sources()
    features=feature_series(snapshots,raw);result=merge_features(original,features,snapshots)
    assert result[FIFTY].notna().all().all() and not np.isinf(result[FEATURES]).any().any()
    assert result.oa_snapshot_date.lt(result.date).all()
    assert result[result.date.ge('2021-01-01')][FEATURES].notna().all().all()
    prefixes=['2021-01-29','2022-06-30','2024-01-31','2026-04-30']
    for stamp in prefixes:
        date=pd.Timestamp(stamp);dates=[d for d in snapshots if d<=date]
        known=raw[raw.snapshot_date.lt(date)]
        rebuilt=merge_features(original[original.date.eq(date)].reset_index(drop=True),feature_series(dates,known),snapshots)
        pd.testing.assert_frame_equal(rebuilt,result[result.date.eq(date)].reset_index(drop=True))
    result.to_parquet(PANEL,index=False);features.to_csv(DEST/'monthly_features.csv',index=False)
    test=result[result.date.ge('2021-01-01')];assert len(test)==27600
    test[FEATURES].describe().to_csv(DEST/'feature_summary.csv')
    audit=dict(technical_feature_integrity_passed=True,source_sha256=digest(SOURCE),feature_sha256=digest(PANEL),
               plan_sha256=digest(EP/'notes/r38_option_activity.md'),source_manifest_sha256=digest(DEST/'source_manifest.json'),
               publication_crosscheck_sha256=digest(PUBLICATION),monthly_features_sha256=digest(DEST/'monthly_features.csv'),
               original_rows=len(result),evaluation_rows=len(test),snapshots=len(snapshots),asset_date_rows=len(raw),features=FEATURES,
               groups=GROUPS,prefix_checks=prefixes,source_lag_trading_sessions=2,
               all_evaluation_features_available=True,training_300_feature_missing_rows={c:int(result[c].isna().sum()) for c in THREEHUNDRED},
               limitation='Official historical activity snapshots, not immutable vintages, implied volatility or net demand. Two-session availability lag is a conservative assumption; product-specific expiry effects remain.')
    (DEST/'feature_audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit,indent=2))


if __name__=='__main__':build()
