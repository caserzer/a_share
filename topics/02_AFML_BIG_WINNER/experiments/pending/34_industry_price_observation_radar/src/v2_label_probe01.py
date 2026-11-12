"""Single preregistered structural-label feasibility scan; no signal inputs."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP, PRIOR, sha


def segment(x):
    """Return (start, detect, peak, end, confirmation, scale, type) tuples."""
    x = np.asarray(x, dtype=float)
    if len(x) <= 60:
        return []
    sigma = pd.Series(np.r_[np.nan, np.diff(x)]).rolling(60).std().to_numpy()
    scale = np.maximum(np.log(1.03), 2 * sigma * np.sqrt(5))
    low, peak, detect, confirmation = 60, None, None, None
    result = []
    for i in range(61, len(x)):
        if detect is None:
            if x[i] < x[low]:
                low = i
            if x[i] - x[low] < scale[low]:
                continue
            detect, peak = i, i
        if x[i] > x[peak]:
            peak = i
        # A crossing day that already ends the segment cannot confirm persistence.
        ended = x[peak] - x[i] >= scale[low]
        if not ended and confirmation is None and i - detect >= 9:
            above = x[i-9:i+1] >= x[low] + scale[low] / 2
            if above[-1] and above.sum() >= 7:
                confirmation = i
        if ended or i == len(x)-1:
            weak = (x[low] <= x[low-60] or
                    x[low-60:low+1].max() - x[low] >= scale[low])
            result.append((low, detect, peak, i if ended else None,
                           confirmation, scale[low], 'WARMING' if weak else 'HEATING'))
            low, peak, detect, confirmation = i, None, None, None
    return result


def main():
    out = EP / 'outputs/r00_v2_label_probe01'
    if out.exists():
        raise FileExistsError('Preserve first registered result; do not overwrite')
    out.mkdir()
    source = PRIOR / 'daily_industries.parquet'
    catalog_source = EP / 'outputs/r01/weekly_catalog.parquet'
    plan = EP / 'protocols/r00_v2/label_probe01/plan.md'
    inputs = {str(f): sha(f) for f in [source, catalog_source, plan, Path(__file__)]}
    (out / 'started.json').write_text(json.dumps(inputs, indent=2))
    columns = ['date', 'day_i', 'era', 'industry_code', 'industry_name', 'nav',
               'relative_nav', 'block', 'stale_members', 'boundary_proxy']
    raw = pd.read_parquet(source, columns=columns)
    cat = pd.read_parquet(catalog_source, columns=['era', 'industry_code', 'industry_name'])
    cat = cat.drop_duplicates(['era', 'industry_code'])
    valid = raw.nav.notna() & raw.nav.gt(0) & raw.block.notna()
    records, block_audit = [], []
    era_last = raw.groupby('era').day_i.max().to_dict()
    global_last = raw.day_i.max()
    for (era, code, block), g in raw[valid].groupby(['era', 'industry_code', 'block']):
        g = g.sort_values('day_i').reset_index(drop=True)
        assert np.all(np.diff(g.day_i) == 1), (era, code, block)
        x = np.log(g.nav.to_numpy())
        spans = segment(x)
        block_audit.append(dict(era=era, industry_code=code, block=int(block),
                                valid_rows=len(g), left_history_rows=min(60, len(g)),
                                candidate_scan_rows=max(0, len(g)-60), candidates=len(spans)))
        for start, detect, peak, end, confirm, scale, kind in spans:
            last = end if end is not None else len(g)-1
            if end is not None:
                censor = 'CLOSED'
            elif g.day_i.iloc[-1] == global_last:
                censor = 'RIGHT_CENSORED'
            elif g.day_i.iloc[-1] == era_last[era]:
                censor = 'CLASSIFICATION_BOUNDARY'
            else:
                censor = 'DATA_BOUNDARY'
            status = ('PERSISTENCE_OBSERVED' if confirm is not None else
                      'TRANSIENT_OR_NOT_RETAINED' if end is not None else 'UNKNOWN')
            def date(j):
                return g.date.iloc[j].strftime('%Y-%m-%d') if j is not None else None
            rel = g.relative_nav.iloc[[start, peak]].to_numpy()
            records.append(dict(candidate_id=f'L01-{len(records)+1:06d}', era=era,
                industry_code=code, industry_name=g.industry_name.iloc[0], block=int(block),
                kind=kind, status=status, boundary=censor, start=date(start),
                detected=date(detect), peak=date(peak), ended=date(end), confirmed=date(confirm),
                observed_until=date(last), start_day=int(g.day_i.iloc[start]),
                detect_day=int(g.day_i.iloc[detect]), last_day=int(g.day_i.iloc[last]),
                scale_return=float(np.expm1(scale)), peak_gain=float(np.expm1(x[peak]-x[start])),
                relative_peak_gain=float(rel[1]/rel[0]-1) if np.isfinite(rel).all() and (rel>0).all() else None,
                days_to_detection=detect-start, days_to_confirmation=confirm-start if confirm is not None else None,
                observed_duration=last-start,
                proxy_rows=int((g.stale_members.iloc[start:last+1].gt(0) |
                                g.boundary_proxy.iloc[start:last+1]).sum())))
    result = pd.DataFrame(records)
    result.to_parquet(out / 'candidates.parquet', index=False)
    blocks = pd.DataFrame(block_audit)
    blocks.to_parquet(out / 'blocks.parquet', index=False)
    directory = cat.merge(raw.groupby(['era','industry_code']).agg(
        raw_rows=('nav','size'), valid_rows=('nav','count')).reset_index(), how='left')
    directory = directory.merge(result.groupby(['era','industry_code']).size().rename('candidates').reset_index(), how='left')
    directory[['raw_rows','valid_rows','candidates']] = directory[['raw_rows','valid_rows','candidates']].fillna(0).astype(int)
    directory.to_parquet(out / 'directory.parquet', index=False)
    result.assign(year=result.start.str[:4]).groupby(['era','year','kind','status']).size().rename('count').reset_index().to_csv(out/'strata.csv',index=False)
    summary = dict(scope='Label feasibility only; not final process denominator or method evaluation',
        directory=len(directory), no_local_rows=int(directory.raw_rows.eq(0).sum()),
        no_valid_price=int(directory.valid_rows.eq(0).sum()), no_candidate=int(directory.candidates.eq(0).sum()),
        raw_rows=len(raw), valid_rows=int(valid.sum()), invalid_rows=int((~valid).sum()),
        left_history_rows=int(blocks.left_history_rows.sum()), scan_rows=int(blocks.candidate_scan_rows.sum()),
        candidates=len(result), status=result.status.value_counts().to_dict(),
        kind=result.kind.value_counts().to_dict(), boundaries=result.boundary.value_counts().to_dict(),
        scale_quantiles=result.scale_return.quantile([0,.1,.5,.9,1]).to_dict(),
        gain_quantiles=result.peak_gain.quantile([0,.1,.5,.9,1]).to_dict())
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    (out/'receipt.json').write_text(json.dumps(dict(inputs=inputs, artifacts={f.name:sha(f) for f in out.iterdir() if f.is_file()}),indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
