"""Isolated EP37 revision. Never writes to EP36 or original EP37 result paths."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS', '4')
os.environ.setdefault('OMP_NUM_THREADS', '4')
import sys
import json
import platform
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from model import ridge, predict, train_rankic

ROOT = Path(__file__).resolve().parent
EP37 = ROOT.parents[1]
EP36 = EP37.parent / '36_csi300_alpha_discovery_and_index_enhancement'
PRIVATE = EP36 / 'private'
CACHE = ROOT / 'local_cache'
OUT = ROOT / 'outputs'
MAN = ROOT / 'manifests'
sys.path.insert(0, str(EP37 / 'code'))
import core
from core import sha, dump, clean, rankcorr, assign_deciles, bootstrap, holm


def config():
    return json.loads((ROOT / 'config.json').read_text())


def columns():
    d = pd.read_csv(EP36 / 'configs/feature_dictionary.csv')
    cols = d.loc[d.group.eq('core'), 'feature'].tolist()
    assert len(cols) == 78
    return cols


def freeze():
    for p in [CACHE, OUT, MAN, CACHE / 'models', CACHE / 'ledgers']:
        p.mkdir(parents=True, exist_ok=True)
    file = MAN / 'freeze.json'
    if file.exists():
        r = json.loads(file.read_text())
        for x in r['files']:
            assert sha(x['path']) == x['sha256'], x['path']
        return r
    original = core.verify_freeze()
    files = [Path(x['path']) for x in original['inputs']]
    files += [PRIVATE / (x + '.parquet') for x in ['features', 'labels', 'qfq_high', 'qfq_low', 'volume']]
    files += [EP36 / 'configs/feature_dictionary.csv', EP36 / 'src/features.py', EP36 / 'src/common.py', EP36 / 'src/train.py']
    files += sorted((EP36 / 'outputs/fold_predictions/expanding').glob('*.parquet'))
    files += sorted((EP36 / 'outputs/manifests').glob('expanding_20*.json'))
    files += [EP37 / 'outputs/local_cache' / (n + '.parquet') for n in ['features', 'labels', 'predictions']]
    files += list((EP37 / 'code').glob('*.py')) + [EP37 / 'config.yaml', ROOT / 'config.json', ROOT / 'model.py', ROOT / 'run.py']
    r = dict(authorization=config()['authorization'], original_results_already_seen=True,
             new_model_outer_results_seen=False, feature_count=78,
             files=[dict(path=str(p), sha256=sha(p)) for p in sorted(set(files))],
             environment=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__, torch=torch.__version__))
    dump(file, r)
    return r


def prepare():
    freeze()
    cols = columns()
    original = pd.read_parquet(PRIVATE / 'features.parquet')
    base = pd.read_parquet(EP37 / 'outputs/local_cache/predictions.parquet')
    base = base.loc[base.scheme.eq('expanding') & base.offset.eq(0)].copy()
    f37 = pd.read_parquet(EP37 / 'outputs/local_cache/features.parquet')
    f37 = f37.loc[f37.offset.eq(0), ['signal_date', 'instrument', 'signal_idx']]
    base = base.merge(f37, on=['signal_date', 'instrument'], validate='one_to_one')
    # Import original pure feature implementation, including its exact zscore helper.
    sys.path.insert(0, str(EP36 / 'src'))
    from features import compute
    sys.path.pop(0)
    mats = {k: pd.read_parquet(PRIVATE / (k + '.parquet')) for k in
            ['qfq_close', 'qfq_open', 'qfq_high', 'qfq_low', 'volume', 'money', 'turnover_rate', 'daily_members', 'market']}
    c = mats['qfq_close']
    daily = compute(*(mats[k] for k in ['qfq_close', 'qfq_open', 'qfq_high', 'qfq_low', 'volume', 'money', 'turnover_rate', 'daily_members']), mats['market'].close)
    original_i = c.index.get_indexer(original.signal_date)
    original_j = c.columns.get_indexer(original.instrument)
    bi = c.index.get_indexer(base.signal_date); bj = c.columns.get_indexer(base.instrument)
    assert min(original_i.min(), original_j.min(), bi.min(), bj.min()) >= 0
    parity = []
    keep = ['signal_date', 'instrument', 'entry_date', 'exit_date', 'entry_idx', 'exit_idx', 'state', 'fold', 'fit_cutoff']
    result = base[keep].copy(); result['JR_11'] = base.J_R
    for col in cols:
        array = daily[col].to_numpy()
        old = original[col].to_numpy(); rebuilt = array[original_i, original_j]
        same_missing = np.array_equal(np.isnan(old), np.isnan(rebuilt))
        err = float(np.nanmax(np.abs(old - rebuilt)))
        assert same_missing and err < 1e-12, (col, same_missing, err)
        parity.append(dict(feature=col, rows=len(old), missing_mask_equal=same_missing, max_abs_error=err))
        result[col] = array[bi, bj]
    eligible = result[cols].notna().mean(axis=1).ge(.8)
    coverage = result.assign(eligible78=eligible).groupby('signal_date').agg(original_EP37=('instrument', 'size'), common_eligible=('eligible78', 'sum'))
    result = result.loc[eligible].copy()
    assert result.groupby('signal_date').size().min() >= 100
    result.to_parquet(CACHE / 'h10_features.parquet', index=False)
    pd.DataFrame(parity).to_csv(OUT / 'feature_parity.csv', index=False)
    coverage.to_csv(OUT / 'coverage.csv')
    pd.read_csv(EP36 / 'configs/feature_dictionary.csv').query("group=='core'").to_csv(OUT / 'original_78_features.csv', index=False)
    dump(MAN / 'data.json', dict(rows=len(result), source_EP37_rows=len(base), excluded_rows=int((~eligible).sum()),
         feature_parity_columns=78, feature_parity_values=len(original)*78, maximum_error=max(x['max_abs_error'] for x in parity),
         eligibility_reads_labels=False, features_sha256=sha(CACHE / 'h10_features.parquet')))
    print('prepared original78', len(result), 'excluded', int((~eligible).sum()), flush=True)


def train():
    freeze(); cfg = config(); cols = columns()
    weekly = pd.read_parquet(PRIVATE / 'features.parquet')
    labels = pd.read_parquet(PRIVATE / 'labels.parquet', columns=['signal_date', 'instrument', 'h10', 'target_z', 'h10_mature', 'entry_date'])
    data = weekly.merge(labels, on=['signal_date', 'instrument'], validate='one_to_one')
    h10 = pd.read_parquet(CACHE / 'h10_features.parquet')
    hpred = []; wpred = []; receipts = []; traces = []; replays = []
    for quarter in sorted(h10.signal_date.dt.to_period('Q').unique()):
        cutoff = quarter.start_time - pd.Timedelta(nanoseconds=1)
        mature = data.loc[data.score_eligible & data.target_z.notna() & (data.h10_mature <= cutoff) & (data.signal_date < quarter.start_time)].copy()
        mature['target_rank'] = mature.groupby('signal_date').h10.transform(lambda y: y.rank(method='average')/(y.count()+1)-.5)
        boundary = cutoff - pd.DateOffset(months=cfg['inner_validation_months'])
        valid = mature.loc[mature.signal_date >= boundary].copy()
        inner = mature.loc[(mature.signal_date < boundary) & (mature.h10_mature < valid.entry_date.min())].copy()
        assert inner.h10_mature.max() < valid.entry_date.min()
        assert mature.h10_mature.max() <= cutoff
        assert valid.signal_date.nunique() >= 12
        _, curve, chosen = train_rankic(inner, cols, cfg['optimizer'], validation=valid)
        ric, final_curve, _ = train_rankic(mature, cols, cfg['optimizer'], steps=chosen)
        models = {'E1_78': ridge(mature, cols), 'RANK_MSE_78': ridge(mature, cols, 'target_rank'), 'RIC_78': ric}
        ht = h10.loc[h10.signal_date.dt.to_period('Q').eq(quarter)].copy()
        wt = weekly.loc[weekly.signal_date.dt.to_period('Q').eq(quarter) & weekly.score_eligible].copy()
        hp = ht[['signal_date', 'instrument', 'entry_date', 'exit_date', 'entry_idx', 'exit_idx', 'state', 'fold', 'fit_cutoff', 'JR_11']].copy()
        wp = wt[['signal_date', 'instrument']].copy(); wp['fold'] = str(quarter)
        for mid, model in models.items():
            hp[mid] = predict(ht, model); wp[mid] = predict(wt, model)
            path = CACHE / 'models' / f'{quarter}_{mid}.json'
            dump(path, model)
            receipts.append(dict(fold=str(quarter), model=mid, train_rows=len(mature), train_dates=mature.signal_date.nunique(),
                train_start=mature.signal_date.min(), train_end=mature.signal_date.max(), max_label_maturity=mature.h10_mature.max(), cutoff=cutoff,
                inner_rows=len(inner), inner_last_exit=inner.h10_mature.max(), validation_rows=len(valid), validation_dates=valid.signal_date.nunique(),
                validation_first_entry=valid.entry_date.min(), chosen_steps=chosen if mid=='RIC_78' else 0,
                model_path=str(path.relative_to(ROOT)), model_sha256=sha(path)))
        for row in curve: traces.append(dict(fold=str(quarter), chosen=row['step']==chosen, **row))
        old = pd.read_parquet(EP36 / 'outputs/fold_predictions/expanding' / f'{quarter}.parquet')
        old = old.loc[old.model_id.eq('E1') & old.score_eligible, ['signal_date', 'instrument', 'score']]
        check = wp.merge(old, on=['signal_date', 'instrument'], validate='one_to_one')
        assert len(check) == len(wp) == len(old)
        error = float(np.max(np.abs(check.E1_78 - check.score)))
        assert error < 1e-10, ('Original E1 baseline mismatch', quarter, error)
        original_receipt = json.loads((EP36 / 'outputs/manifests' / f'expanding_{quarter}.json').read_text())
        assert len(mature) == original_receipt['train_rows']
        replays.append(dict(fold=str(quarter), rows=len(check), train_rows=len(mature), original_train_rows=original_receipt['train_rows'], max_prediction_error=error))
        hpred.append(hp); wpred.append(wp)
        print('trained', quarter, 'rows', len(mature), 'steps', chosen, 'E1 error', error, flush=True)
    pd.concat(hpred, ignore_index=True).to_parquet(CACHE / 'predictions.parquet', index=False)
    pd.concat(wpred, ignore_index=True).to_parquet(CACHE / 'weekly_predictions.parquet', index=False)
    pd.DataFrame(receipts).to_csv(OUT / 'folds.csv', index=False)
    pd.DataFrame(traces).to_csv(OUT / 'validation_checkpoints.csv', index=False)
    pd.DataFrame(replays).to_csv(OUT / 'original_E1_reproduction.csv', index=False)
    dump(MAN / 'training.json', dict(final_models=len(receipts), quarters=len(replays), full_78_features=True,
         objective='negative differentiable Spearman surrogate', selection='exact validation mean RankIC',
         outer_labels_passed_to_prediction=False, original_E1_max_error=max(x['max_prediction_error'] for x in replays),
         predictions_sha256=sha(CACHE / 'predictions.parquet')))


def select():
    freeze()
    pred = pd.read_parquet(CACHE / 'predictions.parquet')
    rankings = []; targets = []
    for date, g in pred.groupby('signal_date'):
        assert g[['E1_78', 'RANK_MSE_78', 'RIC_78', 'JR_11']].notna().all().all()
        for model in ['E1_78', 'RANK_MSE_78', 'RIC_78', 'JR_11']:
            z = g.copy(); z['score'] = z[model]; z['decile'] = assign_deciles(z, 'score'); z['model'] = model
            rankings.append(z.drop(columns=['E1_78', 'RANK_MSE_78', 'RIC_78', 'JR_11']))
            for portfolio, group in [('D'+str(d), z.loc[z.decile.eq(d)]) for d in range(1, 11)] + [('TOP20', z.loc[z.decile.ge(9)])]:
                group = group.copy(); group['portfolio'] = portfolio; group['weight'] = 1./len(group)
                targets.append(group[['signal_date','entry_date','exit_date','entry_idx','exit_idx','instrument','state','model','portfolio','weight','score','decile']])
        ew = g[['signal_date','entry_date','exit_date','entry_idx','exit_idx','instrument','state']].copy()
        ew['model']='EW'; ew['portfolio']='EW'; ew['weight']=1./len(ew); ew['score']=np.nan; ew['decile']=np.nan
        targets.append(ew)
    pd.concat(rankings,ignore_index=True).to_parquet(CACHE / 'rankings.parquet', index=False)
    t = pd.concat(targets,ignore_index=True); t.to_parquet(CACHE / 'targets.parquet', index=False)
    t.to_csv(OUT / 'all_target_holdings.csv.gz',index=False,compression='gzip')
    pd.concat(rankings,ignore_index=True).to_csv(OUT / 'all_rankings.csv.gz',index=False,compression='gzip')
    dump(MAN / 'selection.json', dict(targets_sha256=sha(CACHE / 'targets.parquet'), rankings_sha256=sha(CACHE / 'rankings.parquet'), reads_labels=False))
    print('selection frozen',len(t),flush=True)


def economics():
    freeze()
    import accounts
    accounts.OUT = OUT  # Market's suspension audit must go to this revision only.
    market = accounts.Market()
    t = pd.read_parquet(CACHE / 'targets.parquet')
    events = []; details = []
    for (mid, portfolio, date), g in t.groupby(['model','portfolio','signal_date']):
        if int(g.exit_idx.iloc[0]) >= len(market.days): continue
        for cost, (b, s) in config()['evaluation']['costs_bps'].items():
            e, detail = accounts.event(market, g, b/10000, s/10000)
            meta=dict(model=mid, portfolio=portfolio, signal_date=date, entry_date=g.entry_date.iloc[0], exit_date=g.exit_date.iloc[0], cost=cost)
            events.append(meta|e)
            if cost=='main':
                for k,v in meta.items(): detail[k]=v
                details.append(detail)
    pd.DataFrame(events).to_csv(OUT / 'events.csv',index=False)
    pd.concat(details,ignore_index=True).to_parquet(CACHE / 'event_stock_details.parquet',index=False)
    summary=[]; infos=[]; all_daily=[]
    for (mid,portfolio),g in t.loc[t.portfolio.isin(['D10','TOP20','EW'])].groupby(['model','portfolio']):
        for scope, end in [('primary','2025-03-03'),('extended','2026-10-12')]:
            endpoint=market.days.get_loc(pd.Timestamp(end))
            for cost,(b,s) in config()['evaluation']['costs_bps'].items():
                for mode in ['strict','flat'] + (['haircut20'] if cost=='main' else []):
                    key=f'{mid}_{portfolio}_{scope}_{cost}_{mode}'
                    detail=mode=='flat' and cost=='main'
                    daily,orders,holds,info=accounts.account(market,g,endpoint,mode,b/10000,s/10000,key,detail)
                    meta=dict(account=key,model=mid,portfolio=portfolio,scope=scope,cost=cost,valuation=mode)
                    infos.append(info|meta)
                    d=pd.DataFrame(daily)
                    if d.empty: continue
                    for k,v in meta.items(): d[k]=v
                    all_daily.append(d)
                    nav=d.nav.to_numpy(); dd=nav/np.maximum.accumulate(np.r_[1.,nav])[1:]-1
                    summary.append(meta|dict(valuation_complete=info['valuation_complete'],terminal_liquidated=info['terminal_liquidated'],
                        start=info['start'],end=info['actual_end'],days=len(d),total_return=nav[-1]-1,
                        cagr=nav[-1]**(252/(endpoint-market.days.get_loc(pd.Timestamp(info['start']))))-1 if info['valuation_complete'] else np.nan,
                        max_drawdown=dd.min(),fees=d.fees.sum(),buy_value=d.buy.sum(),sell_value=d.sell.sum(),
                        average_stock_weight=d.stock_weight.mean(),overdue_days=int(d.overdue_count.gt(0).sum()),
                        max_accounting_residual=float(d.accounting_residual.abs().max())))
                    if detail:
                        pd.DataFrame(orders).to_parquet(CACHE/'ledgers'/f'{key}_orders.parquet',index=False)
                        pd.DataFrame(holds,columns=['date','instrument','units','mark','weight','entry_date','planned_exit','age']).to_parquet(CACHE/'ledgers'/f'{key}_holdings.parquet',index=False)
        print('accounts',mid,portfolio,flush=True)
    pd.DataFrame(summary).to_csv(OUT/'accounts.csv',index=False)
    pd.concat(all_daily,ignore_index=True).to_parquet(CACHE/'daily_accounts.parquet',index=False)
    dump(MAN/'accounts.json',clean(infos))


def analyze():
    freeze()
    labels=pd.read_parquet(EP37/'outputs/local_cache/labels.parquet')
    labels=labels.loc[labels.offset.eq(0),['signal_date','instrument','h10']]
    pred=pd.read_parquet(CACHE/'predictions.parquet')
    panel=pred.merge(labels,on=['signal_date','instrument'],validate='one_to_one')
    panel=panel.loc[panel.exit_date.notna() & panel.exit_date.le('2026-10-12')]
    rows=[]
    for date,g in panel.groupby('signal_date'):
        for mid in ['E1_78','RANK_MSE_78','RIC_78','JR_11']:
            rows.append(dict(signal_date=date,exit_date=g.exit_date.iloc[0],model=mid,rankic=rankcorr(g[mid],g.h10),
                eligible=len(g),known_labels=g.h10.notna().sum()))
    ic=pd.DataFrame(rows); ic.to_csv(OUT/'rankic_by_date.csv',index=False)
    # Original weekly calendar is secondary diagnostic coverage, not an extra candidate portfolio.
    wp=pd.read_parquet(CACHE/'weekly_predictions.parquet').merge(pd.read_parquet(PRIVATE/'labels.parquet',columns=['signal_date','instrument','h10','h10_mature']),on=['signal_date','instrument'],validate='one_to_one')
    wr=[]
    for date,g in wp.loc[wp.h10_mature.le('2026-10-12')].groupby('signal_date'):
        for mid in ['E1_78','RANK_MSE_78','RIC_78']:
            wr.append(dict(signal_date=date,exit_date=g.h10_mature.iloc[0],model=mid,rankic=rankcorr(g[mid],g.h10)))
    pd.DataFrame(wr).to_csv(OUT/'weekly_rankic_by_date.csv',index=False)
    stats=[]; tests=[]
    events=pd.read_csv(OUT/'events.csv',parse_dates=['signal_date','exit_date'])
    for scope,limit in [('primary','2025-03-03'),('extended','2026-10-12')]:
        sub=ic.loc[ic.exit_date.le(limit)]
        for mid,g in sub.groupby('model'):
            stats.append(dict(scope=scope,model=mid,**bootstrap(g.rankic.to_numpy())))
        if scope=='primary':
            pivot=sub.pivot(index='signal_date',columns='model',values='rankic').sort_index()
            for base in ['E1_78','JR_11']:
                tests.append(dict(test=f'RIC_78_minus_{base}_RankIC',**bootstrap((pivot.RIC_78-pivot[base]).to_numpy())))
            ev=events.loc[events.cost.eq('main')&events.portfolio.eq('D10')&events.exit_date.le(limit)]
            ep=ev.pivot(index='signal_date',columns='model',values='net_return').reindex(pivot.index)
            tests.append(dict(test='RIC_78_minus_E1_78_D10_net_event',**bootstrap((ep.RIC_78-ep.E1_78).to_numpy())))
    for r,p in zip(tests,holm([r['p'] for r in tests])):r['holm_p']=p
    pd.DataFrame(stats).to_csv(OUT/'rankic_summary.csv',index=False)
    pd.DataFrame(tests).to_csv(OUT/'primary_tests.csv',index=False)
    annual=ic.copy();annual['year']=annual.signal_date.dt.year
    annual.groupby(['year','model']).agg(rankic=('rankic','mean'),dates=('rankic','count')).to_csv(OUT/'yearly_rankic.csv')
    rr=pd.read_parquet(CACHE/'rankings.parquet').merge(labels,on=['signal_date','instrument'],validate='many_to_one')
    rr=rr.loc[rr.exit_date.notna()&rr.exit_date.le('2026-10-12')]
    group=rr.groupby(['signal_date','exit_date','model','decile']).agg(mean_h10=('h10','mean'),known=('h10','count'),selected=('instrument','size')).reset_index()
    group.to_csv(OUT/'deciles_by_date.csv',index=False)
    gs=[]
    for scope,limit in [('primary','2025-03-03'),('extended','2026-10-12')]:
        for (mid,decile),g in group.loc[group.exit_date.le(limit)].groupby(['model','decile']):
            gs.append(dict(scope=scope,model=mid,decile=decile,mean_h10=g.mean_h10.mean(),dates=len(g),known=int(g.known.sum()),selected=int(g.selected.sum())))
    pd.DataFrame(gs).to_csv(OUT/'decile_summary.csv',index=False)
    dump(MAN/'analysis.json',clean(dict(rankic_summary=stats,primary_tests=tests,ranking_intervals_descriptive=True,
         independent_alpha_certified=False,forward_status='FORWARD_PENDING')))
    print('analysis complete',flush=True)


if __name__=='__main__':
    globals()[sys.argv[1]]()
