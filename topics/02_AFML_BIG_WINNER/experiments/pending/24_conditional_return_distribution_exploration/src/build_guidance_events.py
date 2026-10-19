"""Outcome-independent dated announcement/title events, with explicit query scope."""
import json
import re
from pathlib import Path
import numpy as np
import pandas as pd
from prepare_panel import EP,OUT
from build_joint_information import SOURCE
from build_margin_information import digest
from audit_exchange_guidance_catalog import load_catalog
from download_exchange_guidance_catalog import DEST as CATALOG

DEST=OUT/'r37_guidance_events'
PANEL=OUT/'local_cache/guidance_event_panel.parquet'
TIMING=['gd_age_days','gd_count30','gd_count90','gd_count365','gd_revision90','gd_revision365']
TITLE=['gd_up90','gd_down90','gd_loss90','gd_profit90']
FEATURES=TIMING+TITLE
GROUPS={'timing':TIMING,'timing_title':FEATURES}
PATTERNS={'gd_up90':'业绩预增','gd_down90':'业绩预减','gd_loss90':'业绩预亏','gd_profit90':'业绩预盈'}


def available_date(record):
    dates=[pd.Timestamp(record['publish_date'])]
    dates.extend(pd.Timestamp(value) for value in re.findall(r'/([12]\d{3}-\d{2}-\d{2})/',record['url']))
    assert len(dates)>=2,'Missing explicit archive-path date'
    return max(dates)


def read_sources():
    records,manifests=load_catalog();rows=[]
    for record in records:
        for code in record['stocks']:
            rows.append(dict(instrument=record['exchange']+code,available=available_date(record),title=record['title'],
                             announcement_id=record['announcement_id'],url=record['url']))
    raw=pd.DataFrame(rows)
    assert not raw.duplicated(['instrument','announcement_id','url']).any()
    raw['revision']=raw.title.str.contains('修正|更正',regex=True)
    for feature,pattern in PATTERNS.items():raw[feature]=raw.title.str.contains(pattern,regex=False)
    raw.attrs['source_manifests']=manifests
    return raw


def at_date(history,date):
    result={c:0.0 for c in FEATURES};result['gd_age_days']=np.nan;result['gd_latest_notice']=pd.NaT
    known=history[history.available.lt(date)&history.available.ge(date-pd.Timedelta(days=365))]
    if known.empty:return result
    latest=known.available.max();result.update(gd_age_days=float((date-latest).days),gd_latest_notice=latest)
    for window in (30,90,365):
        recent=known[known.available.ge(date-pd.Timedelta(days=window))]
        result[f'gd_count{window}']=float(len(recent))
        if window in (90,365):result[f'gd_revision{window}']=float(recent.revision.sum())
        if window==90:
            for feature in TITLE:result[feature]=float(recent[feature].sum())
    return result


def feature_frame(original,raw):
    rows=[]
    for instrument,group in original.groupby('instrument',sort=True):
        history=raw[raw.instrument.eq(instrument)]
        for date in group.date:rows.append(dict(date=date,instrument=instrument,**at_date(history,date)))
    result=original.merge(pd.DataFrame(rows),on=['date','instrument'],how='left',sort=False,validate='one_to_one')
    pd.testing.assert_frame_equal(result[original.columns],original)
    return result


def build():
    DEST.mkdir(exist_ok=True)
    coverage=json.loads((CATALOG/'coverage_audit.json').read_text())
    assert coverage['original_stocks']==1242 and coverage['cninfo_title_eligible_missing']==0
    original=pd.read_parquet(SOURCE);raw=read_sources()
    assert coverage['source_manifests']==raw.attrs['source_manifests']
    result=feature_frame(original,raw)
    assert (result.gd_latest_notice.isna()|result.gd_latest_notice.lt(result.date)).all()
    assert result.gd_age_days.dropna().between(1,365).all()
    assert result[FEATURES[1:]].notna().all().all() and (result[FEATURES[1:]]>=0).all().all()
    assert not np.isinf(result[FEATURES]).any().any()
    prefixes=['2021-01-29','2022-06-30','2024-01-31','2026-04-30']
    for stamp in prefixes:
        date=pd.Timestamp(stamp);base=original[original.date.eq(date)].reset_index(drop=True)
        rebuilt=feature_frame(base,raw[raw.available.lt(date)])
        pd.testing.assert_frame_equal(rebuilt,result[result.date.eq(date)].reset_index(drop=True))
    result.to_parquet(PANEL,index=False);raw.to_parquet(DEST/'dated_events.parquet',index=False)
    test=result[result.date.ge('2021-01-01')];assert len(test)==27600
    test.groupby(test.date.dt.year)[FEATURES].mean().to_csv(DEST/'feature_means.csv')
    audit=dict(technical_feature_integrity_passed=True,source_sha256=digest(SOURCE),feature_sha256=digest(PANEL),
        plan_sha256=digest(EP/'notes/r37_guidance_events.md'),source_manifests=raw.attrs['source_manifests'],
        coverage_audit_sha256=digest(CATALOG/'coverage_audit.json'),dated_events_sha256=digest(DEST/'dated_events.parquet'),
        original_rows=len(result),evaluation_rows=len(test),features=FEATURES,groups=GROUPS,prefix_checks=prefixes,
        recent365_test_coverage=float(test.gd_age_days.notna().mean()),recent90_test_coverage=float(test.gd_count90.gt(0).mean()),
        limitation='Title-scoped original announcement events, not numeric earnings or a complete inventory of all corporate forecasts. Zero means no matching archived record only.')
    (DEST/'feature_audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit,indent=2))


if __name__=='__main__':build()
