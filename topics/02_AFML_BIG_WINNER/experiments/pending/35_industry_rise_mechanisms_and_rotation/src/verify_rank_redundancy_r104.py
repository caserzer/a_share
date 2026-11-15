"""Rebuild all ranks independently and verify every frozen model identity."""
import pandas as pd
from scipy.stats import rankdata
from scipy.special import expit
from common import *
from versioned_observations import digest_json

F=['mom20','mom60','vol20','dd60','past_excess20','past_excess60','log_members']
PAIRS=[('mom20','past_excess20'),('mom60','past_excess60')]

def run():
    out=ROOT/'outputs/r104';receipt=json.loads((out/'receipt.json').read_text())
    for p,h in receipt['reads'].items():assert sha(p)==h
    for p,h in receipt['outputs'].items():assert sha(out/p)==h
    actual=pd.read_parquet(out/'rank_pairs.parquet');folds=pd.read_csv(out/'model_compression.csv');expected=[];models=[];ranks={};preds=[]
    for rnd,panelname in [('r02','monthly_panel'),('r16','l1_monthly_panel')]:
        p=pd.read_parquet(ROOT/f'data/{panelname}.parquet');p['log_members']=np.log(p.members)
        models.extend([m for m in json.loads((ROOT/f'outputs/{rnd}/model_parameters.json').read_text()) if m['cohort'] in ['F','FD'] and m['cohort']==m['method']])
        preds.append(pd.read_parquet(ROOT/f'outputs/{rnd}/predictions.parquet'))
        for (era,level),base in p[p.price_ready].groupby(['era','level']):
          for cohort in ['F','FD']:
            cols=F+(['breadth21','breadth63'] if cohort=='FD' else [])
            g=base.dropna(subset=cols).copy();rank=pd.DataFrame(index=g.index,columns=cols,dtype=float)
            for _,q in g.groupby('date'):
                for col in cols:rank.loc[q.index,col]=(rankdata(q[col],method='average')-.5)/len(q)-.5
            ranks[(era,level,cohort)]=(g,rank)
            d=g[KEY+['date']].copy();d['cohort']=cohort
            for a,b in PAIRS:d[a+'_rank']=rank[a];d[b+'_rank']=rank[b];d[a+'_difference']=rank[a]-rank[b]
            expected.append(d)
    expected=pd.concat(expected,ignore_index=True);pd.testing.assert_frame_equal(actual,expected)
    assert not actual.duplicated(KEY+['date','cohort']).any()
    assert set(folds.model_sha256)=={digest_json(m) for m in models} and not folds.model_sha256.duplicated().any()
    predictions=pd.concat(preds,ignore_index=True);total=0
    for m in models:
        row=folds[folds.model_sha256.eq(digest_json(m))].iloc[0];g,r=ranks[(m['era'],m['level'],m['cohort'])]
        cols=m['columns'];mean=np.array(m['scaler_mean']);scale=np.array(m['scaler_scale']);beta=np.array(m['coefficient']).ravel();intercept=np.asarray(m['intercept']).item()
        exact=all(r[a].equals(r[b]) and mean[cols.index(a)]==mean[cols.index(b)] and scale[cols.index(a)]==scale[cols.index(b)] for a,b in PAIRS)
        assert row.compression_status==('exact_duplicate_columns' if exact else 'not_exact_do_not_compress')
        if not exact:continue
        z=(r[cols].to_numpy()-mean)/scale
        old=z@beta+intercept;merged=np.full(len(z),intercept);squared=0.;asym=0.;diff=[]
        for j,col in enumerate(cols):
            if col in ['past_excess20','past_excess60']:continue
            if col in ['mom20','mom60']:
                k=cols.index('past_excess'+col[3:]);b=beta[j]+beta[k];merged+=z[:,j]*b;squared+=b*b/2;asym+=(beta[j]-beta[k])**2/2;diff.append(abs(beta[j]-beta[k]))
            else:merged+=z[:,j]*beta[j];squared+=beta[j]**2
        assert np.isclose(beta@beta,squared+asym,atol=1e-13)
        for name,value in [('old_l2_squared',beta@beta),('compressed_l2_squared',squared),('asymmetry_penalty',asym),('max_pair_coefficient_difference',max(diff))]:assert np.isclose(row[name],value,atol=1e-13)
        assert np.max(abs(old-merged))<1e-12 and row.max_decision_error<1e-12
        q=predictions
        for k in ['era','level','cohort','method','task','horizon','year']:q=q[q[k].eq(m[k])]
        d=g[KEY+['date']].copy();d['decision']=merged;joined=q.merge(d,on=KEY+['date'],how='left',validate='one_to_one')
        assert joined.decision.notna().all() and len(joined)==row.test_rows
        value=joined.decision.to_numpy()
        if m['task']!='return':value=expit(value*np.asarray(m['calibration_coefficient']).item()+np.asarray(m['calibration_intercept']).item())
        error=max(abs(value-joined.prediction));assert error<1e-10 and row.max_prediction_error<1e-10;total+=len(q)
    summary=json.loads((out/'summary.json').read_text())
    assert summary['models']==len(models) and summary['compressible']==int(folds.compression_status.eq('exact_duplicate_columns').sum()) and summary['formal_test_rows']==total
    for entry in summary['rank_comparisons']:
        g=actual
        for key in ['era','level','cohort']:g=g[g[key].eq(entry[key])]
        a=entry['pair'].split(' / ')[0];v=g[a+'_difference']
        assert entry['rows']==len(g) and entry['dates']==g.date.nunique() and entry['exact_equal']==int(v.eq(0).sum()) and entry['within_tolerance']==int(v.abs().le(1e-14).sum()) and entry['max_difference']==v.abs().max()
    result=dict(status='PASS',source_cohort_rows=len(actual),pair_checks=2*len(actual),models=len(models),formal_test_rows=total,max_prediction_error=float(folds.max_prediction_error.max()),max_coefficient_asymmetry=float(folds.max_pair_coefficient_difference.max()),max_l2_asymmetry_penalty=float(folds.asymmetry_penalty.max()),refitted_models=0)
    js(out/'verification.json',result);print(result)

if __name__=='__main__':run()
