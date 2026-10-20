"""Audit source semantics, every inherited label and preservation of EP24."""
import importlib.metadata
import platform
import numpy as np
import pandas as pd
from core import EP, OLD, OUT, TOPIC, CONFIG, digest, write_json, load_panel


def preserved_files():
    return sorted(p for p in OLD.rglob('*') if p.is_file() and 'local_cache' not in p.parts and '__pycache__' not in p.parts and p.suffix in {'.py','.md','.json','.csv','.txt'})


def main():
    OUT.mkdir(exist_ok=True)
    paths = preserved_files()
    before = {str(p.relative_to(OLD)): digest(p) for p in paths}
    write_json(OUT/'ep24_preservation_before.json', before)
    raw = pd.read_parquet(OLD/CONFIG['panel'])
    panel = load_panel()
    calpath = TOPIC/'data/qlib/cn_data_pit_largecap/calendars/day.txt'
    calendar = pd.DatetimeIndex(pd.to_datetime(pd.read_csv(calpath, header=None)[0]))
    assert str(calendar[-1].date()) == CONFIG['cutoff']
    errors = []; checked = {h:0 for h in CONFIG['horizons']}; source_receipts = []
    for instrument, g in raw.groupby('instrument'):
        path = TOPIC/f'data/raw/akshare/day/qfq/{instrument}.csv'
        bars = pd.read_csv(path, parse_dates=['date']).set_index('date')
        assert not bars.index.duplicated().any()
        close = bars.close.where(bars.close>0)
        start = close.reindex(g.date).to_numpy()
        source_receipts.append(dict(path=str(path.relative_to(TOPIC)),sha256=digest(path)))
        for h in CONFIG['horizons']:
            target = pd.DatetimeIndex([d+pd.DateOffset(months=h) for d in g.date])
            idx = calendar.searchsorted(target)
            ends = np.full(len(g),np.datetime64('NaT'), dtype='datetime64[ns]')
            ok=idx<len(calendar); ends[ok]=calendar[idx[ok]].to_numpy()
            assert np.array_equal(g[f'end_{h}'].isna(),pd.isna(ends))
            assert np.array_equal(g[f'end_{h}'].dropna().to_numpy(),ends[~pd.isna(ends)])
            y = close.reindex(pd.DatetimeIndex(ends)).to_numpy()/start-1
            np.testing.assert_allclose(g[f'y_{h}'],y,rtol=0,atol=1e-12,equal_nan=True)
            checked[h]+=int(np.isfinite(y).sum())
    finance=panel.financial_available_date.notna()
    assert (panel.loc[finance,'financial_available_date']<panel.loc[finance,'date']).all()
    assert (panel.loc[finance,'financial_report_date']<=panel.loc[finance,'financial_available_date']).all()
    assert all((panel[f'y_{h}'].dropna() >= -1).all() for h in CONFIG['horizons'])
    frows=frevised=0
    for p in (OLD/'outputs/local_cache/public_financials').glob('*.parquet'):
        f=pd.read_parquet(p,columns=['NOTICE_DATE','UPDATE_DATE'])
        frows+=len(f); frevised+=int((pd.to_datetime(f.UPDATE_DATE,errors='coerce')>pd.to_datetime(f.NOTICE_DATE,errors='coerce')).sum())
    age=(panel.date-panel.financial_report_date).dt.days
    coverage=[]
    for h in CONFIG['horizons']:
        for date,g in panel[panel.date>=CONFIG['prediction_start']].groupby('date'):
            mature=g[f'end_{h}'].notna() & (g[f'end_{h}']<=pd.Timestamp(CONFIG['cutoff']))
            coverage.append(dict(horizon=h,date=str(date.date()),predicted=len(g),mature=int(mature.sum()),observed=int((mature&g[f'y_{h}'].notna()).sum()),mature_missing=int((mature&g[f'y_{h}'].isna()).sum()),immature=int((~mature).sum())))
    pd.DataFrame(coverage).to_csv(OUT/'outcome_coverage.csv',index=False)
    byyear=raw.assign(year=raw.date.dt.year,eligible=raw.index.isin(panel.index)).groupby('year').agg(all_rows=('date','size'),eligible=('eligible','sum'))
    byyear.to_csv(OUT/'eligibility_by_year.csv')
    artifacts=[OLD/CONFIG['panel'],calpath,OLD/'outputs/data_audit.json',OLD/'outputs/enrichment_semantics.json',OLD/'notes/publication_scope.md',OLD/'notes/r14_walk_forward.md']
    artifacts += [OLD/f'outputs/r10_four_horizons/predictions_{h}m.parquet' for h in CONFIG['horizons']]
    write_json(OUT/'input_receipts.json',[dict(path=str(p.relative_to(TOPIC)),sha256=digest(p),bytes=p.stat().st_size) for p in artifacts]+source_receipts)
    audit=dict(raw_rows=len(raw),eligible_rows=len(panel),instruments=raw.instrument.nunique(),eligible_instruments=panel.instrument.nunique(),all_inherited_labels_recomputed=True,observed_labels_checked=checked,
        financial_rows=frows,revised_after_notice=frevised,financial_strictly_prior=True,financial_age_days_quantiles={str(k):float(v) for k,v in age.quantile([.1,.5,.9]).items()},
        independent_holdout=False,evidence='retrospective exploration',data_cutoff=CONFIG['cutoff'],ep24_files_preserved=len(before),
        unresolved=['Shanghai lifetime ST universe selection','valuation vendor historical vintages unverified','financial conservative max(notice,update) is not original as-published vintage','full dividends/delisting/rights/restructuring total return unresolved','missing endpoints can be informative','all EP24 old history and R14 new maturities already inspected','short overlapping periods and nonstationarity limit inference'],
        repairs='none; source evidence does not justify replacing inherited labels or universe',r14_extension='already viewed, cross-source; not merged into frozen R10 labels')
    write_json(OUT/'data_audit.json',audit)
    write_json(OUT/'runtime_versions.json',dict(python=platform.python_version(),packages={n:importlib.metadata.version(n) for n in ['numpy','pandas','scipy','scikit-learn','catboost','pyarrow','pytest','matplotlib']}))
    print(audit,flush=True)

if __name__=='__main__':main()
