"""Build valuation, conservatively dated financial and lagged yield features."""
import json
import numpy as np
import pandas as pd
from probe_public_data import OUT

VALUATION = ['earnings_yield', 'book_yield', 'sales_yield', 'cashflow_yield', 'pe_percentile']
FINANCIAL = ['roe', 'profit_growth', 'revenue_growth', 'debt_ratio', 'ocf_eps_ratio']
CREDIT = ['gov_3y', 'credit_spread_3y', 'credit_change63', 'yield_slope']


def build():
    panel = pd.read_parquet(OUT / 'local_cache/monthly_panel.parquet')
    parts, audits = [], []
    for instrument, target in panel.groupby('instrument'):
        g = target.sort_values('date').copy()
        for col in VALUATION + FINANCIAL:
            g[col] = np.nan
        vpath = OUT / f'local_cache/public_valuation/{instrument[2:]}.parquet'
        if vpath.exists():
            v = pd.read_parquet(vpath)
            v['date'] = pd.to_datetime(v.TRADE_DATE)
            v = v.sort_values('date').drop_duplicates('date', keep='last')
            for source, dest in [('PE_TTM', 'earnings_yield'), ('PB_MRQ', 'book_yield'),
                                 ('PS_TTM', 'sales_yield'), ('PCF_OCF_TTM', 'cashflow_yield')]:
                value = pd.to_numeric(v[source], errors='coerce')
                v[dest] = 1 / value.where(value.abs() > 1e-6)
            pe = pd.to_numeric(v.PE_TTM, errors='coerce').where(lambda x: x > 0)
            v['pe_percentile'] = pe.expanding(min_periods=252).rank(pct=True)
            g = g.drop(columns=VALUATION).merge(v[['date'] + VALUATION], on='date', how='left', validate='one_to_one')
        fpath = OUT / f'local_cache/public_financials/{instrument[2:]}.{instrument[:2]}.parquet'
        if fpath.exists():
            f = pd.read_parquet(fpath)
            for col in ['REPORT_DATE', 'NOTICE_DATE', 'UPDATE_DATE']:
                f[col] = pd.to_datetime(f[col], errors='coerce')
            f['available_date'] = f[['NOTICE_DATE', 'UPDATE_DATE']].max(axis=1)
            f = f.dropna(subset=['REPORT_DATE', 'NOTICE_DATE', 'UPDATE_DATE'])
            f = f[f.REPORT_DATE <= f.NOTICE_DATE].sort_values(['REPORT_DATE', 'available_date'])
            audits.append({'instrument': instrument, 'reports': len(f),
                           'revised_after_notice': int((f.UPDATE_DATE > f.NOTICE_DATE).sum())})
            for idx, row in g.iterrows():
                eligible = f[f.available_date < row.date]
                if eligible.empty:
                    continue
                report = eligible.iloc[-1]
                g.loc[idx, 'financial_available_date'] = report.available_date
                g.loc[idx, 'financial_report_date'] = report.REPORT_DATE
                for source, dest in [('ROEJQ', 'roe'), ('PARENTNETPROFITTZ', 'profit_growth'),
                                     ('TOTALOPERATEREVETZ', 'revenue_growth'), ('ZCFZL', 'debt_ratio')]:
                    g.loc[idx, dest] = pd.to_numeric(report.get(source), errors='coerce')
                eps = pd.to_numeric(report.get('EPSJB'), errors='coerce')
                ocf = pd.to_numeric(report.get('MGJYXJJE'), errors='coerce')
                if pd.notna(eps) and abs(eps) > .01:
                    g.loc[idx, 'ocf_eps_ratio'] = ocf / eps
        parts.append(g)
    result = pd.concat(parts, ignore_index=True)
    yieldfiles = sorted((OUT / 'local_cache/public_yields').glob('*.parquet'))
    if yieldfiles:
        y = pd.concat([pd.read_parquet(p) for p in yieldfiles], ignore_index=True)
        y['日期'] = pd.to_datetime(y['日期'])
        name = y.columns[0]
        for col in ['1年', '3年', '10年']:
            y[col] = pd.to_numeric(y[col], errors='coerce')
        gov = y[y[name] == '中债国债收益率曲线'].set_index('日期').sort_index()
        corp = y[y[name] == '中债中短期票据收益率曲线(AAA)'].set_index('日期').sort_index()
        macro = pd.DataFrame({'gov_3y': gov['3年'], 'yield_slope': gov['10年'] - gov['1年'],
                              'credit_spread_3y': corp['3年'] - gov['3年']}).sort_index()
        macro['credit_change63'] = macro.credit_spread_3y - macro.credit_spread_3y.shift(63)
        macro.index.name = 'yield_observation_date'
        macro = macro.reset_index()
        # Publication on observation day may be after decision cutoff; use strictly prior day.
        result = pd.merge_asof(result.sort_values('date'), macro, left_on='date', right_on='yield_observation_date',
                               allow_exact_matches=False, tolerance=pd.Timedelta(days=7))
    else:
        for col in CREDIT:
            result[col] = np.nan
    result = result.replace([np.inf, -np.inf], np.nan)
    result.to_parquet(OUT / 'local_cache/enriched_panel.parquet', index=False)
    pd.DataFrame(audits).to_csv(OUT / 'financial_revision_audit.csv', index=False)
    coverage = result.groupby(result.date.dt.year)[VALUATION + FINANCIAL + CREDIT].agg(lambda s: s.notna().mean())
    coverage.to_csv(OUT / 'enriched_coverage_by_year.csv')
    print(coverage.round(3).to_string())
    (OUT / 'enrichment_semantics.json').write_text(json.dumps({
        'valuation': 'historical vendor daily series; original vintage not independently verified',
        'financial': 'available only strictly after max(NOTICE_DATE, UPDATE_DATE); revisions never backdated',
        'financial_limit': 'conservative availability can make financial signals stale; original vintages unavailable',
        'credit': 'AAA medium-short-term note 3y minus government 3y, percentage points; previous available day, <=7 day lag',
        'pe_percentile': 'expanding positive PE history since available source start, minimum 252 values; NOT ten-year percentile',
    }, indent=2) + '\n')


if __name__ == '__main__':
    build()
