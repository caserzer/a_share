"""R16: learn within-month relative stock effects separately from market risk."""
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from build_improvement_features import FEATURE_PANEL
from diagnose_prediction_target import DEST
from prepare_panel import DATA, OUT
from run_four_horizons import calendar_targets, probability_stats
from run_market_residual_search import Q, combine_components

FOLDER = DEST / 'rank_residual'
GROUPS = {
    'rank_value_residual': ['earnings_yield', 'book_yield', 'pe_percentile', 'forward_log_anchor12',
                            'roe', 'profit_growth', 'revenue_growth', 'debt_ratio', 'ocf_eps_ratio'],
    'rank_technical_residual': ['log_cap', 'vol63', 'relative_mom21', 'relative_mom63',
                                'relative_mom126', 'reversal5', 'turnover21', 'skew63', 'downvol63'],
}
GROUPS['rank_combined_residual'] = list(dict.fromkeys(sum(list(GROUPS.values()), [])))


def cross_sectional_ranks(panel, columns):
    """Known contemporaneous predictor ranks; no cross-date or outcome inputs."""
    return (panel.groupby('date')[columns].rank(pct=True).fillna(.5) - .5) * 2


def fit_effects(train, x, z, residual):
    y = pd.Series(residual, index=train.index)
    # Remove common realized month shocks from training targets, never prediction inputs.
    centered = y - y.groupby(train.date).transform('median')
    count = train.groupby('date').instrument.transform('size').to_numpy()
    sample_weight = 1 / count
    sample_weight *= len(sample_weight) / sample_weight.sum()
    model = Ridge(alpha=1000)
    model.fit(x, centered.clip(-5, 5), sample_weight=sample_weight)
    fitted = model.predict(x).clip(-1, 1)
    query = model.predict(z).clip(-1, 1)
    return fitted, query


def run():
    FOLDER.mkdir(exist_ok=True)
    panel = pd.read_parquet(FEATURE_PANEL)
    panel = panel[panel.common_eligible].copy()
    cols = GROUPS['rank_combined_residual']
    ranks = cross_sectional_ranks(panel, cols)
    features = pd.read_parquet(OUT / 'local_cache/improvement_market_features.parquet')
    calendar = pd.DatetimeIndex(features.index)
    indices = pd.read_csv(DATA / 'processed/index/benchmark_indices_daily.csv', parse_dates=['date'])
    close = indices[indices.index_alias == 'csi300'].set_index('date').close.reindex(calendar)
    audits = []
    for h in [1, 3, 6]:
        _, end = calendar_targets(calendar, h, calendar)
        market = features.copy()
        market['label_end'] = end.to_numpy()
        market['scale'] = market.csi300_vol63.clip(.03, 1) * np.sqrt(h / 12)
        market['standardized'] = np.log(close.reindex(pd.DatetimeIndex(end)).to_numpy() / close.to_numpy()) / market.scale
        # Match R16 market/residual market training population exactly.
        market = market.dropna(subset=['csi300_mom21', 'csi300_mom63', 'csi300_mom126',
                                     'csi300_vol63', 'all_a_mom21', 'all_a_mom63'])
        rows = []
        for date, test in panel[panel.date >= '2021-01-01'].groupby('date', sort=True):
            train = panel[(panel[f'end_{h}'] < date) & panel[f'y_{h}'].notna() & panel[f'market_label_{h}'].notna()]
            mtrain = market[(market.label_end < date) & market.standardized.notna()]
            market_q = np.quantile(mtrain.standardized, Q) * float(market.loc[date, 'scale'])
            beta_train = train.beta252.fillna(1).clip(0, 2).to_numpy()
            beta_test = test.beta252.fillna(1).clip(0, 2).to_numpy()
            scale_train = train.idio_vol63.fillna(train.vol63).clip(.03, 2).to_numpy() * np.sqrt(h / 12)
            scale_test = test.idio_vol63.fillna(test.vol63).clip(.03, 2).to_numpy() * np.sqrt(h / 12)
            residual = (np.log1p(train[f'y_{h}'].to_numpy()) - beta_train * np.log1p(train[f'market_label_{h}'].to_numpy())) / scale_train
            for name, columns in GROUPS.items():
                fitted, query = fit_effects(train, ranks.loc[train.index, columns], ranks.loc[test.index, columns], residual)
                noise = residual - fitted
                # Fixed 50% shrinkage of fitted stock location toward zero.
                residual_q = .5 * query[:, None] + np.quantile(noise, Q)
                atoms = combine_components(market_q, residual_q, beta_test, scale_test)
                r = test[['date', 'instrument', f'end_{h}', f'target_{h}', f'y_{h}']].reset_index(drop=True)
                r = r.rename(columns={f'end_{h}': 'label_end', f'target_{h}': 'target_date', f'y_{h}': 'actual'})
                r = pd.concat([r, probability_stats(atoms, r.actual)], axis=1)
                r['months'], r['model'] = h, name
                rows.append(r)
            assert train[f'end_{h}'].max() < date and mtrain.label_end.max() < date
            audits.append(dict(months=h, date=str(date.date()), training_rows=len(train),
                               last_stock_label=str(train[f'end_{h}'].max()),
                               last_market_label=str(mtrain.label_end.max()), predicted_rows=len(test)))
            print(h, date.date(), len(train), flush=True)
        pd.concat(rows, ignore_index=True).to_parquet(FOLDER / f'predictions_{h}m.parquet', index=False)
    pd.DataFrame(audits).to_csv(FOLDER / 'fit_audit.csv', index=False)
    (FOLDER / 'spec.json').write_text(json.dumps(dict(
        groups=GROUPS, ridge_alpha=1000, target_clip=[-5, 5], prediction_clip=[-1, 1],
        stock_location_shrinkage=.5, train_month_weights='equal',
        within_month='predictor ranks and matured target median centering',
        market='same empirical market component as R16 market_empirical_residual',
        residual_noise='pooled training residual minus fitted stock effect; in-sample approximation',
        evidence='retrospective exploration; parameters fixed before scoring this family'
    ), indent=2) + '\n')


if __name__ == '__main__':
    run()
