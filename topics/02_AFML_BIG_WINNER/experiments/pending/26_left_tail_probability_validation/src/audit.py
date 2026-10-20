"""Audit inherited tail labels, stale reports and preservation without repairs."""
import importlib.metadata
import platform
import numpy as np
import pandas as pd
from core import *


def protected_files():
    result=[]
    for root in [OLD,PREV]:
        result += [p for p in root.rglob('*') if p.is_file() and not any(s in p.parts for s in ['local_cache','__pycache__','.pytest_cache']) and p.suffix in {'.py','.md','.json','.csv','.txt','.png'}]
    return sorted(result)


def main():
    OUT.mkdir(exist_ok=True)
    preservation={str(p.relative_to(EP.parent)):digest(p) for p in protected_files()}
    write_json(OUT/'prior_episodes_preservation.json',preservation)
    p=load_panel();raw=pd.read_parquet(OLD/'outputs/local_cache/four_horizon_panel.parquet')
    source=[OLD/'outputs/local_cache/four_horizon_panel.parquet',OLD/'outputs/local_cache/historical_industry_panel.parquet',PREV/'config.json',PREV/'outputs/data_audit.json',PREV/'outputs/preregistration.json',PREV/'outputs/controls.json',PREV/'src/core.py',OLD/'outputs/enrichment_semantics.json']
    calendar_path=TOPIC/'data/qlib/cn_data_pit_largecap/calendars/day.txt'
    source.append(calendar_path)
    calendar=pd.DatetimeIndex(pd.to_datetime(pd.read_csv(calendar_path,header=None)[0]))
    assert str(calendar[-1].date())==C['data_cutoff']
    for instrument,g in raw.groupby('instrument'):
        path=TOPIC/f'data/raw/akshare/day/qfq/{instrument}.csv';source.append(path)
        close=pd.read_csv(path,parse_dates=['date']).set_index('date').close
        assert not close.index.duplicated().any()
        targets=pd.DatetimeIndex([d+pd.DateOffset(months=6) for d in g.date]);idx=calendar.searchsorted(targets)
        ends=np.full(len(g),np.datetime64('NaT'),dtype='datetime64[ns]');ok=idx<len(calendar);ends[ok]=calendar[idx[ok]]
        np.testing.assert_array_equal(g.end_6.isna(),pd.isna(ends))
        np.testing.assert_array_equal(g.end_6.dropna().to_numpy(),ends[~pd.isna(ends)])
        observed=close.reindex(pd.DatetimeIndex(ends)).to_numpy()/close.reindex(g.date).to_numpy()-1
        np.testing.assert_allclose(observed,g.y_6,rtol=0,atol=1e-12,equal_nan=True)
        np.testing.assert_array_equal(event_labels(observed,-.2),event_labels(g.y_6,-.2))
    for quarter in pd.period_range('2021Q1','2026Q2',freq='Q'):
        receipt=PREV/f'outputs/checkpoints/6_{quarter}.json';source.append(receipt)
        r=json.loads(receipt.read_text())
        for key in ['atoms','predictions']:
            f=PREV/r[key]['path'];assert digest(f)==r[key]['sha256'];source.append(f)
    pd.DataFrame([dict(path=str(s.relative_to(TOPIC)),sha256=digest(s),bytes=s.stat().st_size) for s in source]).to_csv(OUT/'source_receipts.csv',index=False)
    evaluation=p[p.date>=C['prediction_start']].copy();known=evaluation[evaluation.end_6.notna()&evaluation.y_6.notna()]
    coverage=[]
    for date,g in evaluation.groupby('date'):
        mature=g.end_6.notna();observed=mature&g.y_6.notna();missing=mature&g.y_6.isna();events=int((g.y_6<-.2).sum());n=int(mature.sum())
        coverage.append(dict(date=str(date.date()),predicted=len(g),mature=n,observed=int(observed.sum()),events=events,missing=int(missing.sum()),immature=int((~mature).sum()),
            event_rate_lower=events/n if n else np.nan,event_rate_upper=(events+missing.sum())/n if n else np.nan))
    pd.DataFrame(coverage).to_csv(OUT/'outcome_coverage.csv',index=False)
    age=evaluation.groupby('age_group',observed=True).agg(rows=('date','size'),months=('date','nunique'),age_median=('financial_age_days','median'),known=('y_6','count'))
    age['known_events']=known.groupby('age_group').y_6.apply(lambda x:(x<-.2).sum());age.to_csv(OUT/'financial_age_audit.csv')
    known.assign(year=known.date.dt.year).groupby('year').agg(rows=('y_6','size'),events=('y_6',lambda x:(x<-.2).sum()),median_age=('financial_age_days','median')).to_csv(OUT/'annual_event_audit.csv')
    raw.groupby('status_source').agg(rows=('date','size'),instruments=('instrument','nunique')).to_csv(OUT/'universe_status_audit.csv')
    ep25=json.loads((PREV/'outputs/data_audit.json').read_text())
    write_json(OUT/'data_audit.json',dict(raw_rows=len(raw),eligible_rows=len(p),prediction_rows=len(evaluation),scorable_rows=len(known),events=int((known.y_6<-.2).sum()),months=known.date.nunique(),
        ep25_threshold_matches=True,all_56000_6m_labels_recomputed=True,financial_age_median=float(evaluation.financial_age_days.median()),
        mature_missing=int(pd.DataFrame(coverage).missing.sum()),financial_vintage='strictly after max(notice,update), not certified original vintage',
        industry_known_fraction=float(evaluation.industry_sector.ne('UNKNOWN').mean()),industry_stale_fraction=float(evaluation.industry_stale.fillna(1).mean()),
        unresolved=ep25['unresolved'],left_tail_direction='survivor/ST selection and missing delisting endpoints may undercount losses; magnitude outside observed pool unidentified',
        prospective=False,repairs='none; unchanged original universe and labels',prior_files_preserved=len(preservation)))
    write_json(OUT/'runtime_versions.json',dict(python=platform.python_version(),packages={k:importlib.metadata.version(k) for k in ['numpy','pandas','scipy','scikit-learn','catboost','pyarrow','pytest','matplotlib']}))
    print(json.loads((OUT/'data_audit.json').read_text()),flush=True)

if __name__=='__main__':main()
