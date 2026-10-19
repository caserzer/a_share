"""Same-broker, same-fiscal-year forecast-growth revisions, known as of each row.

History is restricted to previously observed monthly latest reports, not a claim
of full broker consensus coverage. Outcomes are never used to select reports.
"""
import hashlib
import json
import numpy as np
import pandas as pd
from prepare_panel import OUT
from build_eps_panel import PANEL as SOURCE_PANEL, pair_for_year
from fetch_eps_reports import DEST as SOURCE

DEST = OUT/'r20_earnings_revisions'
PANEL = OUT/'local_cache/earnings_revision_panel.parquet'
EMPTY = dict(revision_available=False, growth_revision=np.nan, revision_gap_days=np.nan,
             previous_report=None, previous_available_date=pd.NaT, previous_observed_date=pd.NaT)
REVISION_SOURCE_EXCLUSIONS = {
    'AP202504281663751625': dict(year='2027', value=78.,
        sha256='70d0346322863dfeb89079fc3e181f928ac573270c938a8c5567597d28834077',
        reason='Original EPS token 078 is ambiguous and inconsistent with the stated PE sequence. Exclude that year; never guess its decimal point.')
}


def revision_for_row(row, current, history):
    if not row['earnings_positive'] or current is None:
        return EMPTY.copy()
    date = row['date']; published = current['available_date']
    if not published < date or (date-published).days > 180:
        return EMPTY.copy()
    basis = 'profit_forecasts' if row['forecast_basis_profit'] == 1 else 'forecasts'
    this_pair = pair_for_year(current[basis], date.year)
    if this_pair is None or not (this_pair > 0).all():
        return EMPTY.copy()
    eligible = [r for r in history if r['infoCode'] != current['infoCode']
        and r['stockCode'] == current['stockCode'] and r['orgCode'] == current['orgCode']
        and r['first_observed_at'] < date and r['available_date'] < published
        and (published-r['available_date']).days <= 365]
    if not eligible:
        return EMPTY.copy()
    # Latest *usable* previously observed report in the same broker's series.
    for prior in sorted(eligible, key=lambda r: (r['available_date'], r['infoCode']), reverse=True):
        old_pair = pair_for_year(prior[basis], date.year)
        if old_pair is None or not (old_pair > 0).all():
            continue
        revision = np.log(this_pair[1]/this_pair[0])-np.log(old_pair[1]/old_pair[0])
        return dict(revision_available=True, growth_revision=float(revision),
            revision_gap_days=float((published-prior['available_date']).days), previous_report=prior['infoCode'],
            previous_available_date=prior['available_date'], previous_observed_date=prior['first_observed_at'])
    return EMPTY.copy()


def build():
    DEST.mkdir(exist_ok=True)
    panel = pd.read_parquet(SOURCE_PANEL)
    original_audit = json.loads((SOURCE/'research_integrity_audit.json').read_text())
    assert hashlib.sha256(SOURCE_PANEL.read_bytes()).hexdigest() == original_audit['feature_sha256']
    raw = pd.read_parquet(SOURCE/'validated_extractions.parquet')
    for code, exclusion in REVISION_SOURCE_EXCLUSIONS.items():
        selected = raw.infoCode.eq(code)
        assert selected.sum() == 1 and raw.loc[selected, 'raw_sha256'].iloc[0] == exclusion['sha256']
        values = json.loads(raw.loc[selected, 'forecasts'].iloc[0])
        assert values[exclusion['year']] == exclusion['value']
        # This third-year field was not used in the frozen R19 current-year pair.
        affected = panel.infoCode.eq(code) & panel.earnings_pair_available & panel.forecast_basis_profit.eq(0)
        assert not panel.loc[affected, 'date'].dt.year.isin([int(exclusion['year'])-1, int(exclusion['year'])]).any()
        del values[exclusion['year']]
        raw.loc[selected, 'forecasts'] = json.dumps(values)
    metadata = pd.read_parquet(SOURCE/'selected_reports.parquet')[['infoCode', 'orgCode']]
    observed = pd.read_parquet(SOURCE/'decision_report_map.parquet').dropna(subset=['infoCode'])
    first = observed.groupby('infoCode').date.min().rename('first_observed_at')
    raw = raw.merge(metadata, on='infoCode', validate='one_to_one').merge(first, on='infoCode', validate='one_to_one')
    raw['available_date'] = pd.to_datetime(raw.available_date)
    conflicts = raw.eps_conflict.fillna(False).astype(bool) | raw.profit_conflict.fillna(False).astype(bool)
    raw = raw[raw.status.isin(['parsed', 'profit_only']) & ~conflicts & raw.orgCode.notna()].copy()
    histories = {k: g.to_dict('records') for k, g in raw.groupby(['stockCode', 'orgCode'])}
    current_reports = {r['infoCode']: r for r in raw.to_dict('records')}
    rows = []
    for row in panel.to_dict('records'):
        current = current_reports.get(row['infoCode'])
        history = histories.get((current['stockCode'], current['orgCode']), []) if current else []
        rows.append(revision_for_row(row, current, history))
    result = pd.concat([panel.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    active = result.revision_available
    assert (result.loc[active, 'previous_available_date'] < pd.to_datetime(result.loc[active, 'available_date'])).all()
    assert (result.loc[active, 'previous_observed_date'] < result.loc[active, 'date']).all()
    assert result.loc[active, 'revision_gap_days'].between(1, 365).all()
    result.to_parquet(PANEL, index=False)
    test = result[result.common_eligible & (result.date >= '2021-01-01')]
    assert len(test) == 27600
    test.groupby(test.date.dt.year).agg(rows=('instrument', 'size'), earnings=('earnings_pair_available', 'sum'),
        revisions=('revision_available', 'sum')).to_csv(DEST/'feature_coverage.csv')
    audit = dict(prediction_rows=len(test), revision_rows=int(test.revision_available.sum()),
        revision_quantiles=test.loc[test.revision_available, 'growth_revision'].quantile([0, .1, .5, .9, 1]).to_dict(),
        feature_sha256=hashlib.sha256(PANEL.read_bytes()).hexdigest(),
        source_panel_sha256=original_audit['feature_sha256'],
        source_exclusions=REVISION_SOURCE_EXCLUSIONS,
        revision='change in log forecast growth, same broker and explicit fiscal-year pair, not absolute EPS revision',
        invariance='common share-unit rescaling of both fiscal-year EPS values within a report cancels in growth',
        limitations='Only previously observed monthly-latest reports; not all broker reports or full consensus. Raw level revisions are excluded because share units may change.')
    (DEST/'feature_audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    build()
