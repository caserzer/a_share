"""EP36 A1: frozen score decomposition, label-free score construction, paired inference.

Never train a return model. The full-capitalization specification remains blocked.
All source inputs are sealed before calculation; outputs use a new run directory.
"""
from datetime import datetime, timezone
import json
import sys
import numpy as np
import pandas as pd
from scipy.stats import rankdata
from common import EP, OUT, PRIVATE, sha, save_json
from evaluate_ranking import predictions

RUN = 'alpha_falsification_20261117'
DEST = OUT / 'diagnostics' / RUN
LOCAL = PRIVATE / RUN
CONFIG = EP / 'configs' / (RUN + '.json')
PRICE = ['mom1', 'mom5', 'mom20', 'mom60', 'vol20', 'vol60']
EXTRA = ['beta60', 'idio60', 'log_money20', 'turnover20', 'log_amihud20']
LAYERS = {'price': PRICE, 'price_industry': PRICE, 'available_style': PRICE + EXTRA}


def freeze():
    if CONFIG.exists():
        raise RuntimeError('Already frozen: do not overwrite this registration')
    DEST.mkdir(parents=True, exist_ok=True)
    LOCAL.mkdir(parents=True, exist_ok=True)
    _, consumption = predictions('expanding')
    snapshot = json.loads((OUT / 'manifests/data_snapshot.json').read_text())
    for name in ['features', 'labels']:
        assert sha(PRIVATE / (name + '.parquet')) == snapshot[name + '_sha256']
    cfg = dict(
        run=RUN, created_at=datetime.now(timezone.utc).isoformat(),
        authorization='User approved the proposed first delivery: data audit, A1, and frozen A2/B1/B2 protocol; progress dependent work only within identified data boundaries',
        evidence='historical_simulated_oos_post_selection_exploration', forward='FORWARD_PENDING',
        scheme='expanding', models=['E1', 'E2'], seeds=['fixed', 'equal_seed_ensemble'],
        prediction_policy='Original sealed scores only; E1/E2 unchanged; no E3; no return-model fitting',
        primary_start='2021-01-08', primary_end='2025-03-03',
        primary_sample='signal >= start and horizon mature <= end; no endpoint extrapolation',
        extended_sample='original available calendar; mature labels only; common model sample',
        layers=LAYERS, industry_layers=['price_industry', 'available_style'],
        common_sample='Per signal use finite E1/E2 scores and all 11 available numerical styles, across all layers; labels never determine score fitting/selection',
        transforms='Numerical columns standardized cross-section mean/population sd; no clipping; constant columns omitted; intercept plus L1 dummies dropping first category; unknown industry is explicit UNKNOWN dummy',
        regression='OLS SVD rcond=1e-12; minimum 100 rows and 50 residual df; no regularization search',
        formulas=dict(beta60='cov(stock return, CSI300 price return)/var(market); 60 complete paired sessions, ddof0',
                      idio60='sqrt(max(var(stock)-cov^2/var(market),0)); same 60 paired sessions',
                      log_money20='log(20-session mean positive RMB turnover amount), 20 observations',
                      turnover20='20-session mean turnover_rate, 20 nonnegative observations',
                      log_amihud20='log(20-session mean abs(qfq close return)/positive RMB turnover amount), 20 observations'),
        market_cap='BLOCKED_DATA: no verified total/free-float capitalization input in sealed EP36 panel; never estimate via volume/turnover or current share count',
        vintage='All existing bars and historical L1 intervals Historical-proxy; known_at not certified; no strict PIT claim',
        missing='No zero/median/backward fill of missing styles or labels; all date/stock exclusions disclosed',
        rank_ic='Spearman of score and raw fixed-horizon return on common known label rows; residual IC is not named partial IC',
        partial_ic='Rank original score and return within common labeled rows; regress both ranks on same standardized raw styles and industry dummies, then Pearson residuals; this is the explicitly defined partial-rank statistic',
        conditional_slope='FWL return on standardized original score and same styles on common labeled rows; coefficient in return per one original-score SD; future returns used only for evaluation',
        reconstruction='In-sample adjusted/unadjusted R2, score rank correlation, and cross-sectional leave-one-stock-out PRESS Q2; PRESS is reconstruction diagnostic, not future-return OOS',
        primary_metrics=['partial_rank_ic', 'residual_ic'],
        primary_test_family='6 E1 H10 tests = 3 layers x 2 primary metrics; Holm two-sided p; E2, slopes, horizons and full interval exploratory',
        statistics=dict(block_weeks=13, replicates=2000, seed=20261117,
                        method='Circular calendar-week block bootstrap, shared resampling for all metrics; gaps retained as NaN; percentile CI; centered bootstrap two-sided p with +1 correction; minimum 26 known weeks',
                        significance=.05),
        selection='No economic equivalence bound chosen: no claim that null results prove replication',
        downstream=dict(S0='Available-style projection of original score; called style-copy, not independent return-trained strong baseline',
                        S1='Original score restricted to same signal-available sample', S2='Available-style residual score',
                        primary_phase=[1, 2], horizon=10, auxiliary_horizons=[5, 20],
                        costs_bps=dict(zero=[0,0], main=[10,20], stress=[30,80]),
                        A2='Same dates, universe, cardinality and execution engine; primary paired net S1-S0 and S2-S0; risk-matched construction must be feasibility-audited before economic run; no tolerance search',
                        B1='Monthly paired (S1-S0)_phase1-(S1-S0)_phase2 at H10; only phase1/2 jointly valid months; random industry/style controls require audited capitalization for full design',
                        B2='Fixed event basket from next open to open t+1+h; marginal 0-5,5-10,10-20 contributions share initial capital and one entry fee; independent H5/H10/H20 liquidation fees; no future tradeability filtering; continuous accounts separate from overlapping events',
                        prerequisite='Full style-matched A2/B1/B2 requires audited capitalization and fixed feasible portfolio matching contract. Do not call unconstrained Q5 a risk-matched portfolio',
                        no_auto_advance='First delivery completes A1 and protocol; full economic adjudication BLOCKED_DATA until full-style contract executable; no automated forward task'))
    save_json(CONFIG, cfg)
    names = ['features','labels','qfq_close','qfq_open','market','money','turnover_rate','industry','daily_members']
    files = [PRIVATE / (x + '.parquet') for x in names]
    files += [OUT / 'manifests/data_snapshot.json', EP / 'configs/protocol.json']
    sources = [EP / 'src' / x for x in ['alpha_falsification.py','common.py','evaluate_ranking.py']]
    save_json(DEST / 'freeze.json', dict(config_sha256=sha(CONFIG), predictions=consumption,
        inputs=[dict(path=str(p),sha256=sha(p)) for p in files],
        sources=[dict(path=str(p),sha256=sha(p)) for p in sources],
        outcomes_seen=False, prior_EP36_outcomes_seen=True))
    print('frozen', CONFIG, flush=True)


def verify():
    rec = json.loads((DEST / 'freeze.json').read_text())
    assert sha(CONFIG) == rec['config_sha256']
    for r in rec['inputs'] + rec['sources'] + rec['predictions']:
        assert sha(r['path']) == r['sha256'], r['path']
    return json.loads(CONFIG.read_text()), rec


def style_panel(features):
    close = pd.read_parquet(PRIVATE / 'qfq_close.parquet')
    ret = close.pct_change(fill_method=None)
    market = pd.read_parquet(PRIVATE / 'market.parquet').close.pct_change(fill_method=None)
    money = pd.read_parquet(PRIVATE / 'money.parquet').where(lambda x:x>0)
    turn = pd.read_parquet(PRIVATE / 'turnover_rate.parquet').where(lambda x:x>=0)
    # Pairwise complete windows, including market moments on each stock's valid rows.
    m = pd.DataFrame(np.broadcast_to(market.to_numpy()[:,None], ret.shape), index=ret.index, columns=ret.columns).where(ret.notna())
    r = ret.where(m.notna())
    cov = (r*m).rolling(60).mean() - r.rolling(60).mean()*m.rolling(60).mean()
    mv = m.rolling(60).var(ddof=0).where(lambda x:x>1e-16)
    arrays = dict(beta60=cov/mv, idio60=np.sqrt((r.rolling(60).var(ddof=0)-cov**2/mv).clip(lower=0)),
                  log_money20=np.log(money.rolling(20).mean()), turnover20=turn.rolling(20).mean(),
                  log_amihud20=np.log((ret.abs()/money).rolling(20).mean().where(lambda x:x>0)))
    out = features[['signal_date','instrument'] + PRICE].copy()
    index = pd.MultiIndex.from_frame(out[['signal_date','instrument']])
    for name, mat in arrays.items():
        out[name] = mat.rename_axis(index='signal_date',columns='instrument').stack().reindex(index).to_numpy()
    ind = pd.read_parquet(PRIVATE / 'industry.parquet')
    ind['instrument'] = ind.ts_code.str[-2:]+ind.ts_code.str[:6]
    ind['start'] = pd.to_datetime(ind.in_date)
    ind['end'] = pd.to_datetime(ind.out_date).fillna(pd.Timestamp('2100-01-01'))
    out['industry'] = 'UNKNOWN'
    for date, ix in out.groupby('signal_date').groups.items():
        active = ind.loc[(ind.start<=date)&(ind.end>date)]
        groups = active.groupby('instrument').l1_code.agg(lambda v: v.iloc[0] if v.notna().all() and v.nunique()==1 else 'UNKNOWN')
        out.loc[ix,'industry'] = out.loc[ix,'instrument'].map(groups).fillna('UNKNOWN')
    return out.replace([np.inf,-np.inf],np.nan)


def design(frame, layer):
    raw = frame[LAYERS[layer]].to_numpy(float)
    sd = raw.std(axis=0)
    z = (raw[:,sd>1e-12]-raw[:,sd>1e-12].mean(axis=0))/sd[sd>1e-12]
    if layer != 'price':
        dummy = pd.get_dummies(frame.industry, drop_first=True).to_numpy(float)
        z = np.column_stack([z, dummy])
    return np.column_stack([np.ones(len(frame)), z])


def project(x, y):
    u,s,_ = np.linalg.svd(x,full_matrices=False)
    keep = s > (s[0]*1e-12)
    q = u[:,keep]
    fitted = q@(q.T@y)
    return fitted, y-fitted, q, int(keep.sum())


def corr(x,y):
    x=np.asarray(x,float); y=np.asarray(y,float)
    if len(x)<3 or np.std(x)<1e-12 or np.std(y)<1e-12:return np.nan
    return float(np.corrcoef(x,y)[0,1])


def rankcorr(x,y):
    if np.std(x)<1e-12 or np.std(y)<1e-12:return np.nan
    return corr(rankdata(x),rankdata(y))


def score_decomposition(frame, layer):
    x=design(frame,layer); y=frame.score.to_numpy(float)
    fitted,res,q,rank=project(x,y)
    n=len(y); tss=np.sum((y-y.mean())**2); sse=res@res
    leverage=np.sum(q*q,axis=1)
    loo=res/(1-leverage) if np.max(leverage)<1-1e-8 else np.full(n,np.nan)
    r2=1-sse/tss if tss>1e-20 else np.nan
    info=dict(n=n,rank=rank,df=n-rank,r2=r2,adjusted_r2=1-(1-r2)*(n-1)/(n-rank),
              loo_q2=1-np.sum(loo**2)/tss if np.isfinite(loo).all() and tss>1e-20 else np.nan,
              reconstruction_rank_ic=rankcorr(y,fitted), max_leverage=float(leverage.max()),
              residual_orthogonality=float(np.max(np.abs(x.T@res))),
              unknown_industry=int(frame.industry.eq('UNKNOWN').sum()))
    return fitted,res,info


def evaluate(frame,layer,h):
    x=design(frame,layer); s=frame.score.to_numpy(float); y=frame[h].to_numpy(float)
    standardized=(s-s.mean())/s.std(ddof=0) if s.std()>1e-12 else np.zeros(len(s))
    _,sr,_,_=project(x,standardized); _,yr,_,_=project(x,y)
    # Ranks are computed within the exact common-label evaluation sample.
    _,rs,_,_=project(x,rankdata(s)); _,ry,_,_=project(x,rankdata(y))
    slope=(sr@yr)/(sr@sr) if sr@sr>1e-16 else np.nan
    return dict(original_ic=rankcorr(s,y), explained_ic=rankcorr(frame.explained,y),
                residual_ic=rankcorr(frame.residual,y),partial_rank_ic=corr(rs,ry),
                conditional_slope=slope)


def calendar_bootstrap(series, B=2000, L=13):
    # Reindex missing calendar weeks BEFORE sampling, never compress gaps.
    s=series.copy();s.index=pd.DatetimeIndex(s.index).to_period('W-FRI')
    assert not s.index.duplicated().any()
    grid=pd.period_range(s.index.min(),s.index.max(),freq='W-FRI')
    a=s.reindex(grid).to_numpy(float); known=np.isfinite(a).sum()
    result=dict(n=int(known),calendar_weeks=len(a),mean=float(np.nanmean(a)) if known else np.nan)
    if known<2*L:return result|dict(ci_low=np.nan,ci_high=np.nan,p=np.nan)
    rng=np.random.default_rng(20261117);n=len(a)
    starts=rng.integers(0,n,(B,int(np.ceil(n/L))))
    idx=((starts[:,:,None]+np.arange(L))%n).reshape(B,-1)[:,:n]
    means=np.nanmean(a[idx],axis=1)
    lo,hi=np.nanquantile(means,[.025,.975]);mu=result['mean']
    p=(1+np.sum(np.abs(means-mu)>=abs(mu)))/(1+np.isfinite(means).sum())
    return result|dict(ci_low=float(lo),ci_high=float(hi),p=float(p))


def holm(pvalues):
    p=np.asarray(pvalues,float); valid=np.isfinite(p); result=np.full(len(p),np.nan)
    order=np.argsort(np.where(valid,p,np.inf));m=len(p);prev=0.
    # Missing tests remain in family size and cannot be significant.
    for k,i in enumerate(order):
        if valid[i]:prev=max(prev,(m-k)*p[i]);result[i]=min(1.,prev)
    return result


def run():
    cfg,freeze_receipt=verify()
    if (DEST/'complete.json').exists():raise RuntimeError('Completed run immutable; use verify or new run')
    p,consumption=predictions('expanding')
    p=p.loc[p.model_id.isin(cfg['models'])&p.seed_or_ensemble.isin(cfg['seeds'])].copy()
    assert not p.duplicated(['model_id','signal_date','instrument']).any()
    f=pd.read_parquet(PRIVATE/'features.parquet')
    styles=style_panel(f)
    styles.to_parquet(LOCAL/'styles.parquet',index=False)
    wide=p.pivot(index=['signal_date','instrument'],columns='model_id',values='score').reset_index()
    shared=styles.merge(wide,on=['signal_date','instrument'],how='inner',validate='one_to_one')
    rows=[]
    for date,g in shared.groupby('signal_date'):
        row=dict(signal_date=date,union_rows=len(g),common_scores=int(g[cfg['models']].notna().all(axis=1).sum()),
                 common_styles=int(g[PRICE+EXTRA].notna().all(axis=1).sum()),
                 common_sample=int(g[PRICE+EXTRA+cfg['models']].notna().all(axis=1).sum()),unknown_industry=int(g.industry.eq('UNKNOWN').sum()))
        for c in PRICE+EXTRA:row[c+'_missing']=int(g[c].isna().sum())
        rows.append(row)
    coverage=pd.DataFrame(rows);coverage.to_csv(DEST/'coverage_weekly.csv',index=False)
    common=shared.dropna(subset=PRICE+EXTRA+cfg['models']).copy()
    score_rows=[];recon=[]
    for model in cfg['models']:
        for date,g in common.groupby('signal_date'):
            g=g.copy();g['score']=g[model]
            if len(g)<100:continue
            for layer in LAYERS:
                fitted,res,info=score_decomposition(g,layer)
                if info['df']<50:continue
                recon.append(dict(model=model,signal_date=date,layer=layer,**info))
                z=g[['signal_date','instrument','industry']+PRICE+EXTRA+['score']].copy()
                z['explained']=fitted;z['residual']=res;z['model']=model;z['layer']=layer
                score_rows.append(z)
    scores=pd.concat(score_rows,ignore_index=True)
    scores.to_parquet(LOCAL/'decomposed_scores.parquet',index=False)
    reconstruction=pd.DataFrame(recon);reconstruction.to_csv(DEST/'reconstruction_weekly.csv',index=False)
    # Labels are opened only AFTER every score has been constructed and persisted.
    labels=pd.read_parquet(PRIVATE/'labels.parquet')
    joined=scores.merge(labels,on=['signal_date','instrument'],validate='many_to_one')
    results=[]
    for (model,layer,date),g in joined.groupby(['model','layer','signal_date']):
        for h in ['h5','h10','h20']:
            valid=g.loc[g[h].notna()&g[h+'_mature'].notna()]
            row=dict(model=model,layer=layer,signal_date=date,horizon=h,scored=len(g),labeled=len(valid),unknown_labels=len(g)-len(valid),mature=valid[h+'_mature'].max())
            if len(valid)>=100 and len(valid)-np.linalg.matrix_rank(design(valid,layer))>=50:row.update(evaluate(valid,layer,h))
            results.append(row)
    detail=pd.DataFrame(results)
    detail['residual_minus_original_ic']=detail.residual_ic-detail.original_ic
    detail['original_minus_explained_ic']=detail.original_ic-detail.explained_ic
    detail.to_csv(DEST/'a1_weekly.csv',index=False)
    metrics=['original_ic','explained_ic','residual_ic','partial_rank_ic','conditional_slope','residual_minus_original_ic','original_minus_explained_ic']
    summaries=[]
    for interval in ['primary','extended']:
        for (model,layer,h),g in detail.groupby(['model','layer','horizon']):
            g=g.copy()
            if interval=='primary':
                g=g.loc[g.signal_date.between(cfg['primary_start'],cfg['primary_end'])]
                g.loc[g.mature>pd.Timestamp(cfg['primary_end']),metrics]=np.nan
            for metric in metrics:
                summaries.append(dict(interval=interval,model=model,layer=layer,horizon=h,metric=metric,**calendar_bootstrap(g.set_index('signal_date')[metric])))
    summary=pd.DataFrame(summaries);summary['holm_p']=np.nan
    ix=summary.index[(summary.interval=='primary')&(summary.model=='E1')&(summary.horizon=='h10')&summary.metric.isin(cfg['primary_metrics'])]
    assert len(ix)==6
    summary.loc[ix,'holm_p']=holm(summary.loc[ix,'p'])
    summary.to_csv(DEST/'a1_summary.csv',index=False)
    # Frozen-year partitions are descriptive, never a strategy switch.
    detail['year']=detail.signal_date.dt.year
    detail.groupby(['model','layer','horizon','year'])[metrics].agg(['mean','count']).to_csv(DEST/'a1_yearly.csv')
    save_json(DEST/'data_audit.json',dict(
        total_score_rows=len(p),common_signal_stock_rows=len(common),
        signal_min=str(common.signal_date.min()),signal_max=str(common.signal_date.max()),
        available_styles=PRICE+EXTRA,industry='historical L1 interval proxy; UNKNOWN preserved',
        unavailable=['total_market_cap','free_float_market_cap','first_vintage_known_at'],
        local_capitalization_probe='EP36 private panel has no capitalization; EP30 backfill vendor_valuations fields are valuation ratios only, known_at NaT; no claim of exhaustive external-source absence',
        complete_style_status='BLOCKED_DATA',available_style_status='HISTORICAL_PROXY_PARTIAL_CONTROL',
        no_missing_zero_fill=True,no_future_label_selection=True))
    verify()
    artifacts=[p for p in DEST.iterdir() if p.is_file()]+[LOCAL/'styles.parquet',LOCAL/'decomposed_scores.parquet']
    save_json(DEST/'complete.json',dict(config_sha256=freeze_receipt['config_sha256'],
        artifacts=[dict(path=str(x),sha256=sha(x)) for x in artifacts],
        raw_predictions_unchanged=True,original_inputs_unchanged=True,
        A1='AVAILABLE_STYLE_COMPLETE',A2='PROTOCOL_ONLY_FULL_STYLE_BLOCKED',B1='PROTOCOL_ONLY_FULL_STYLE_BLOCKED',B2='PROTOCOL_ONLY_FULL_STYLE_BLOCKED',forward='FORWARD_PENDING'))
    print(summary.loc[(summary.interval=='primary')&(summary.horizon=='h10')&summary.metric.isin(['original_ic','residual_ic','partial_rank_ic'])].to_string(index=False),flush=True)


if __name__=='__main__':
    {'freeze':freeze,'run':run,'verify':verify}[sys.argv[1]]()
