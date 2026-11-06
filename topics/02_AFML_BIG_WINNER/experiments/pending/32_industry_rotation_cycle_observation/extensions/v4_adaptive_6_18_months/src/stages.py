"""Enumerate all natural swings before applying the user's 6-18 month condition."""
import pandas as pd
from context import THRESHOLDS, detail, csv
from turns import upswings, duration_class


def discover(paths):
    rows = []
    last_month = paths.month.max()
    for (era, level, code, block), raw in paths.groupby(['era', 'level', 'industry_code', 'block'], sort=True):
        g = raw.sort_values('date').reset_index(drop=True)
        if len(g) < 2:
            continue
        if g.month.iloc[-1] == last_month:
            boundary = 'DATASET_TAIL_PARTIAL_MONTH'
        elif era == 'SW2014' and str(g.month.iloc[-1]) == '2021-11':
            boundary = 'TAXONOMY_BOUNDARY'
        else:
            boundary = 'PRICE_COVERAGE_OR_MEMBERSHIP_GAP'
        for threshold in THRESHOLDS:
            for swing in upswings(g.nav, threshold):
                a, p, z = [g.iloc[swing[k]] for k in ['start_i', 'peak_i', 'evaluation_i']]
                start_confirmation = g.iloc[swing['start_confirm_i']]
                end_confirmation = g.iloc[swing['end_confirm_i']] if swing['end_confirm_i'] is not None else None
                months = z.month.ordinal - a.month.ordinal
                phase_id = f'{era}_{level}_{code}_{block}_{int(threshold*100)}_{a.month}_{p.month}_{swing["status"]}'
                coverage = g.iloc[swing['start_i'] + 1:swing['evaluation_i'] + 1].coverage
                rows.append(dict(phase_id=phase_id, era=era, level=level, industry_code=code,
                    industry_name=a.industry_name, block=block, drawdown_threshold=threshold,
                    start_month=str(a.month), start_date=a.date, peak_month=str(p.month), peak_date=p.date,
                    end_month=str(z.month), end_date=z.date,
                    start_confirmed_at=start_confirmation.date,
                    end_confirmed_at=end_confirmation.date if end_confirmation is not None else pd.NaT,
                    duration_months=months, peak_duration_months=p.month.ordinal - a.month.ordinal,
                    length_class=duration_class(months), status=swing['status'],
                    left_censored=swing['left_censored'], right_censored=swing['right_censored'],
                    end_is_partial=bool(z.is_partial), observation_boundary=boundary,
                    industry_return=float(z.nav/a.nav-1), peak_industry_return=float(p.nav/a.nav-1),
                    minimum_monthly_coverage=float(coverage.min()), average_monthly_coverage=float(coverage.mean()),
                    ex_post_turning_points=True, not_a_forward_signal=True))
    phases = pd.DataFrame(rows)
    detail('all_natural_stages', phases)
    # Full files retain short/long and open stages; this is only an additional index.
    csv('stages/completed_6_18', phases[phases.status.eq('CONFIRMED') & ~phases.left_censored & phases.length_class.eq('IN_RANGE_6_18')])
    csv('stages/over_18_not_split', phases[phases.length_class.eq('LONG_GT18')])
    csv('stages/open_stages', phases[phases.right_censored])
    return phases
