"""Post-R05/R06 diagnostics; no independent-validation claims for new variants."""
import json
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from run_holdout import OUT, GRID, VARIANTS, distribution_stats
from run_price_pilot import TECH
from run_portfolio_probe import targets, load_market, simulate


def matched_exposure(dest, predictions):
    instruments = sorted(predictions.instrument.unique())
    schedules, _ = targets(predictions, instruments)
    calendar, market = load_market(instruments)
    summaries, histories = [], []
    for model in ['peers_risk_size', 'peers_valuation']:
        schedule = {date: weight * schedules[(model, 'distribution_dynamic')][date].sum()
                    for date, weight in schedules[(model, 'all_equal')].items()}
        for fee in [.001, .003]:
            daily, fills, summary = simulate(calendar, market, schedule, fee)
            summary.update(model=model, style='all_equal_matched_dynamic_gross', fee=fee)
            daily['model'], daily['fee'] = model, fee
            summaries.append(summary)
            histories.append(daily)
    pd.DataFrame(summaries).to_csv(dest / 'matched_gross_summary.csv', index=False)
    pd.concat(histories, ignore_index=True).to_parquet(dest / 'matched_gross_nav.parquet', index=False)
    print('Matched exposure:', pd.DataFrame(summaries)[['model','fee','total_return','max_drawdown']].to_string(index=False), flush=True)


def missing_stress(dest, predictions):
    monthly = pd.read_csv(OUT / 'r05_holdout/monthly_scores.csv', parse_dates=['date'])
    summary = []
    for (h, model), g in predictions.groupby(['horizon', 'model']):
        rows = g[g.mature].copy()
        missing = rows[rows.actual.isna()]
        for assumed_return in [-1., 0.]:
            changes = []
            for quarter, m in missing.groupby(missing.date.dt.to_period('Q')):
                keys = pd.read_parquet(OUT / f'local_cache/r05_distributions/{h}_{quarter}_keys.parquet')
                atoms = np.load(OUT / f'local_cache/r05_distributions/{h}_{quarter}_{model}.npz')['atoms']
                positions = {(r.date, r.instrument): i for i, r in enumerate(keys.itertuples())}
                selected = [positions[(r.date, r.instrument)] for r in m.itertuples()]
                stats = distribution_stats(atoms[selected], np.full(len(selected), assumed_return))
                stats['date'] = m.date.to_numpy()
                changes.append(stats[['date', 'crps', 'brier']])
            present = rows[rows.actual.notna()][['date','crps','brier']]
            scenario = pd.concat([present] + changes, ignore_index=True).groupby('date')[['crps','brier']].mean().mean()
            summary.append({'horizon': h, 'model': model, 'missing_return_scenario': assumed_return,
                            'missing_rows': len(missing), **scenario.to_dict()})
    pd.DataFrame(summary).to_csv(dest / 'missing_outcome_scenarios.csv', index=False)


def chinext_only(dest):
    panel = pd.read_parquet(OUT / 'local_cache/enriched_panel.parquet')
    panel = panel[panel.instrument.str.startswith('SZ30')].copy()
    panel['board'] = 1
    predictors = panel.dropna(subset=TECH + ['earnings_yield', 'book_yield'])
    frames = []
    for h in [126, 252]:
        for quarter in pd.period_range('2024Q1','2026Q2',freq='Q'):
            endcol, ycol = f'label_end{h}', f'return{h}'
            train = predictors[(predictors[endcol] < quarter.start_time) & predictors[ycol].notna()]
            test = predictors[predictors.date.dt.to_period('Q') == quarter].reset_index(drop=True)
            if test.empty:
                continue
            y = train[ycol].to_numpy()
            globalq = np.quantile(y, GRID)
            preds = {'expanding_empirical': np.tile(globalq, (len(test),1))}
            for name in ['peers_risk_size','peers_valuation']:
                columns = VARIANTS[name]
                median = train[columns].median().fillna(0)
                scale = (train[columns].quantile(.75)-train[columns].quantile(.25)).replace(0,1).fillna(1)
                x = ((train[columns].fillna(median)-median)/scale).clip(-5,5)
                z = ((test[columns].fillna(median)-median)/scale).clip(-5,5)
                nn = NearestNeighbors(n_neighbors=min(1000,len(train)),n_jobs=4).fit(x).kneighbors(z,return_distance=False)
                preds[name] = .75*np.quantile(y[nn],GRID,axis=1).T+.25*globalq
            for name, atoms in preds.items():
                stats = distribution_stats(atoms,test[ycol])
                stats['date'], stats['instrument'] = test.date, test.instrument
                stats['horizon'], stats['model'] = h,name
                stats['actual'] = test[ycol]
                frames.append(stats)
    predictions = pd.concat(frames,ignore_index=True)
    predictions.to_parquet(dest/'chinext_predictions.parquet',index=False)
    monthly = predictions.dropna(subset=['actual']).groupby(['horizon','model','date'])[['crps','brier','below_q05','coverage90']].mean()
    monthly.to_csv(dest/'chinext_monthly.csv')
    score = monthly.groupby(['horizon','model']).mean()
    score.to_csv(dest/'chinext_summary.csv')
    print('ChiNext only:',score.to_string(),flush=True)


def stratification(dest, predictions):
    scored = predictions[predictions.mature & predictions.actual.notna()].copy()
    scored['financial_age_days'] = (scored.date-scored.financial_report_date).dt.days
    scored['financial_age_group'] = pd.cut(scored.financial_age_days,[-1,270,540,1e6],labels=['<=270','271-540','>540'])
    scored['vol_group'] = scored.groupby(['horizon','model','date']).vol63.transform(
        lambda x: pd.qcut(x.rank(method='first'),3,labels=['low','mid','high']))
    scored['observed_up'] = (scored.actual>0).astype(float)
    scored.groupby(['horizon','model']).agg(months=('date','nunique'),rows=('actual','size'),
        predicted_up=('p_up','mean'),observed_up=('observed_up','mean'),first=('date','min'),last=('date','max')).to_csv(dest/'probability_bias.csv')
    for column in ['financial_age_group','vol_group']:
        scored.groupby(['horizon','model',column,'date'],observed=True)[['crps','brier','below_q05','coverage90']].mean().groupby(
            ['horizon','model',column],observed=True).mean().to_csv(dest/f'{column}_scores.csv')
    scored['pit_bin'] = np.minimum((scored.pit*10).astype(int),9)
    scored.groupby(['horizon','model','pit_bin']).size().rename('rows').to_csv(dest/'pit_histogram.csv')


def run():
    dest=OUT/'r07_sensitivities'
    dest.mkdir(exist_ok=True)
    predictions=pd.read_parquet(OUT/'r05_holdout/predictions.parquet')
    stratification(dest,predictions)
    missing_stress(dest,predictions)
    chinext_only(dest)
    matched_exposure(dest,predictions)
    (dest/'scope.json').write_text(json.dumps({
        'status':'post-holdout exploratory diagnosis, not a new independent test',
        'matched_exposure':'same monthly target gross as dynamic strategy, applied to full eligible universe equal weights',
        'chinext':'train and evaluate only preexisting ChiNext top100 membership; avoids SH lifetime-ST filter, not proof of full-market unbiased coverage',
        'missing_outcomes':'-100% and 0% separate stress scenarios, NOT data replacements or mathematical bounds',
        'action':'do not tune models on these diagnostics and rebrand the same period as untouched'},indent=2)+'\n')


if __name__=='__main__':
    run()
