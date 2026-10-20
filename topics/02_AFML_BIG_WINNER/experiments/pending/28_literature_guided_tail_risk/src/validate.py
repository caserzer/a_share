"""Post-registration independent reconstruction; no fitting or candidate selection."""
from catboost import CatBoostRegressor
from scipy.special import expit,logit
from core import *
from run import freeze
from controls import permute_conditionally
from calibrate import history_rows,offset_fit
from portfolio import selections
from conditional import make_pairs


def main():
    freeze();panel=load_panel();full=pd.read_parquet(CACHE/'all_predictions.parquet');fit_count=0;negative_count=0;shape_count=0
    for quarter in pd.period_range('2021Q1','2026Q2',freq='Q'):
        tr,te=split(panel,6,quarter);r=json.loads((EP/f'outputs/audits/fit_{quarter}.json').read_text())
        assert keys_hash(tr)==r['train_keys_sha256'] and keys_hash(te)==r['test_keys_sha256']
        assert tr.end_6.max()<quarter.start_time
        saved=pd.read_parquet(EP/r['path']);assert digest(EP/r['path'])==r['sha256']
        oldpath=EP27/f'outputs/local_cache/P2_6_{quarter}_predictions.parquet';assert digest(oldpath)==r['source_baseline_sha256']
        old=pd.read_parquet(oldpath)
        for name in ['B0','B1','M_R','M_RMI']:
            a=saved[saved.model.eq(name)].reset_index(drop=True);b=old[old.model.eq(name)].reset_index(drop=True)
            pd.testing.assert_frame_equal(a,b)
        for name in C['fitted_candidates']:
            model=CatBoostClassifier();model.load_model(str(CACHE/f'{quarter}_{name}.cbm'))
            p=predict(model,te,name);np.testing.assert_allclose(p,saved[saved.model.eq(name)].probability,rtol=0,atol=1e-14);fit_count+=1
        negative=pd.read_parquet(CACHE/f'negative_{quarter}.parquet');permuted=permute_conditionally(te)
        for name in ['M_R','L1','L2','L4']:
            model=CatBoostClassifier();model.load_model(str(CACHE/f'negative_{quarter}_{name}.cbm'))
            g=negative[negative.model.eq(name)]
            np.testing.assert_allclose(predict(model,permuted,name),g.probability,rtol=0,atol=1e-14)
            np.testing.assert_allclose(permuted.y_6,g.actual,rtol=0,atol=0,equal_nan=True);negative_count+=1
        shape=pd.read_parquet(CACHE/f'shape_{quarter}.parquet')
        for target,lag in [('future_ncskew6','past_ncskew6'),('future_duvol6','past_duvol6')]:
            for name,cols in [('shape_base',C['risk_features']+[lag]),('shape_disagreement',list(dict.fromkeys(C['risk_features']+[lag]+C['disagreement_features'])))]:
                model=CatBoostRegressor();model.load_model(str(CACHE/f'shape_{quarter}_{target}_{name}.cbm'))
                z=shape[(shape.model==name)&(shape.target==target)]
                np.testing.assert_allclose(model.predict(te[cols]),z.prediction,rtol=0,atol=1e-13)
                np.testing.assert_allclose(te[target],z.actual,equal_nan=True,rtol=0,atol=0);shape_count+=1
    assert (fit_count,negative_count,shape_count)==(198,88,88)
    monthly=pd.read_csv(OUT/'monthly_scores.csv',parse_dates=['date']).set_index(['model','date'])
    rebuilt=0
    for (name,date),g in full.groupby(['model','date']):
        known=g.actual.notna()
        if not known.any():continue
        p=g.loc[known,'probability'].to_numpy();y=(g.loc[known,'actual'].to_numpy()<-.2).astype(float)
        r=monthly.loc[(name,date)]
        assert np.isclose(np.average((p-y)**2),r.brier,atol=1e-14)
        assert len(y)==r.rows and int(y.sum())==r.events
        for fraction in [.05,.1,.2]:
            flagged=warning(g.probability,g.instrument,fraction);r2=metrics(g.probability,g.actual,{str(int(fraction*100)):flagged})
            for col in ['recall','enrichment','precision','fpr']:
                key=col+str(int(fraction*100))
                np.testing.assert_allclose(r2[key],r[key],atol=1e-14,equal_nan=True)
        rebuilt+=1
    intervals=pd.read_csv(OUT/'paired_intervals.csv')
    for row in intervals[intervals.metric.eq('brier')].itertuples():
        a=monthly.loc[row.candidate].sort_index();b=monthly.loc[row.baseline].sort_index()
        expected=ci(a.brier-b.brier,row.block)
        for key in ['estimate','low95','high95','low_family','high_family']:assert abs(getattr(row,key)-expected[key])<1e-14
    cal=pd.read_parquet(CACHE/'calibrated_predictions.parquet');audit=json.loads((EP/'outputs/audits/calibration_fits.json').read_text());cal_count=0
    for row in audit:
        date=pd.Timestamp(row['date']);raw=full[full.model.eq(row['model'])];history=history_rows(raw,date)
        assert keys_hash(history)==row['keys_sha256']
        if row['fitted']:
            assert history.label_end.max()<date
            assert abs(offset_fit(history.probability,labels(history.actual),history.date)-row['shift'])<1e-12
        g=raw[raw.date==date];saved=cal[(cal.model==row['model']+'__offset')&(cal.date==date)]
        p=expit(logit(np.clip(g.probability,1e-8,1-1e-8))+row['shift']) if row['fitted'] else g.probability.to_numpy()
        np.testing.assert_allclose(p,saved.probability,atol=1e-14,rtol=0)
        for f in [.05,.1,.2]:np.testing.assert_array_equal(warning(g.probability,g.instrument,f),warning(saved.probability,saved.instrument,f))
        cal_count+=1
    for name in ['L1','L2','L4','RMI_L1','RMI_L2','RMI_L4']:
        base='M_RMI' if name.startswith('RMI') else 'M_R'
        joint=full[full.model.eq(base)].rename(columns={'probability':'p_base'}).merge(full[full.model.eq(name)][['date','instrument','probability']].rename(columns={'probability':'p_full'}),on=['date','instrument'])
        saved=pd.read_csv(OUT/'matched_pairs.csv',parse_dates=['date'])
        for date,g in joint.groupby('date'):
            pairs=make_pairs(g);z=saved[(saved.model==name)&(saved.date==date)]
            assert list(zip(pairs.high,pairs.low))==list(zip(z.high,z.low))
            inverted=g.copy();inverted['actual']=1-g.actual
            pd.testing.assert_frame_equal(pairs,make_pairs(inverted))
    base=full[full.model.eq('M_R')].rename(columns={'probability':'M_R'}).merge(full[full.model.eq('L4')][['date','instrument','probability']].rename(columns={'probability':'L4'}),on=['date','instrument'])
    held=pd.read_parquet(CACHE/'filter_target_holdings.parquet')
    for date,g in base.groupby('date'):
        f,sel=selections(g)
        for name,mask in sel.items():
            z=held[(held.date==date)&(held.strategy==name)]
            assert set(z.instrument)==set(f.loc[mask,'instrument']) and np.isclose(z.weight.sum(),1)
        pd.testing.assert_series_equal(f[sel['S1']].risk_cell.value_counts().sort_index(),f[sel['S2_matched']].risk_cell.value_counts().sort_index())
    preservation=json.loads((EP/'outputs/manifests/prior_preservation.json').read_text())
    # Format is inspected rather than relying on a count in a report.
    entries=preservation['files'] if isinstance(preservation,dict) and 'files' in preservation else preservation
    count=0
    if isinstance(entries,dict):
        iterator=[dict(path=k,sha256=v) for k,v in entries.items()]
    else:iterator=entries
    for r in iterator:
        p=Path(r['path'])
        if not p.is_absolute():p=EP.parent/r['path']
        assert digest(p)==r['sha256'],str(p);count+=1
    assert json.loads((EP/'outputs/audits/pit_truncation.json').read_text())['passed']
    assert json.loads((EP/'outputs/audits/controls.json').read_text())['all_passed']
    result=dict(passed=True,classification_model_replays=fit_count,negative_model_replays=negative_count,shape_model_replays=shape_count,
        monthly_score_reconstructions=rebuilt,calibration_origin_replays=cal_count,prior_files_verified=count,
        paired_bootstrap_reconstructed=True,matching_outcome_independent=True,matched_filter_cell_counts_equal=True,
        historical_only=True,executable_portfolio_not_validated=True)
    write_json(EP/'outputs/audits/validation.json',result);print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
