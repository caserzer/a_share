import pandas as pd
from common import *
from train_r02 import F,target,train_masks

def run():
    out=ROOT/'outputs/r16';panel=pd.read_parquet(ROOT/'data/l1_monthly_panel.parquet');panel['log_members']=np.log(panel.members)
    assert sha(ROOT/'data/l1_monthly_panel.parquet')==json.loads((ROOT/'protocols/r16.json').read_text())['panel_sha256']
    count=0;error=0.
    for mode,predfile,paramfile in [('strict','predictions.parquet','model_parameters.json'),('raw','raw_predictions.parquet','raw_parameters.json')]:
        predictions=pd.read_parquet(out/predfile);parameters=json.loads((out/paramfile).read_text());replayed=0
        for m in parameters:
            ext=[] if m['cohort']=='F' else ['breadth21','breadth63'];g=panel[panel.price_ready].dropna(subset=F+ext)
            ranks=g.groupby('date')[F+ext].transform(centered_rank)
            y,eligible=target(g,m['task'],m['horizon']);q=g[eligible].copy();q['y']=y[eligible]
            fit,cal,test=train_masks(q,m['year'],m['horizon'],m['task']);tr=q[fit];ca=q[cal]
            assert len(tr)>=300 and tr.date.nunique()>=18
            if m['task']!='return':
                assert tr.y.value_counts().reindex([0.,1.],fill_value=0).min()>=30
                assert tr[f"maturity{m['horizon']}"].max()<pd.Timestamp(m['year']-1,7,1)
                if mode=='strict':
                    assert len(ca)>=100 and ca.date.nunique()>=4 and ca.y.value_counts().reindex([0.,1.],fill_value=0).min()>=10
            else:assert tr[f"maturity{m['horizon']}"].max()<pd.Timestamp(m['year'],1,1)
            p=predictions[(predictions.cohort==m['cohort'])&(predictions.method==m['method'])&(predictions.task==m['task'])&(predictions.horizon==m['horizon'])&(predictions.year==m['year'])]
            assert set(p.row_id)==set(q.index[test])
            z=(ranks.loc[p.row_id,m['columns']].to_numpy()-np.array(m['scaler_mean']))/np.array(m['scaler_scale'])
            coefficient=np.array(m['coefficient'] if mode=='strict' else m['coef']).ravel();intercept=float(np.array(m['intercept']).ravel()[0]);score=z@coefficient+intercept
            if m['task']!='return':
                if mode=='strict':score=score*float(np.array(m['calibration_coefficient']).ravel()[0])+float(np.array(m['calibration_intercept']).ravel()[0])
                score=1/(1+np.exp(-score))
            actual=p.prediction if mode=='strict' else p.raw_score
            error=max(error,float(np.max(np.abs(score-actual))));replayed+=len(p)
            assert np.allclose(p.y,q.loc[p.row_id,'y'],equal_nan=True)
        assert replayed==len(predictions);count+=replayed
        for _,g in predictions.groupby(['cohort','task','horizon','year']):
            if g.cohort.iloc[0]!='FD':continue
            f=g[g.method=='F'].sort_values('row_id');fd=g[g.method=='FD'].sort_values('row_id')
            assert f.row_id.tolist()==fd.row_id.tolist() and np.allclose(f.y,fd.y,equal_nan=True)
    assert error<1e-12
    strict=pd.read_parquet(out/'predictions.parquet');raw=pd.read_parquet(out/'raw_predictions.parquet')
    assert strict.level.eq('L1').all() and raw.level.eq('L1').all()
    assert not strict.task.isin(['onset','reversal']).any()
    assert raw.score_type.eq('uncalibrated_logit').all()
    js(out/'verification.json',dict(status='PASS',replayed_predictions=count,max_error=error,
        checks=['L1 only, no cross-level training','original maturity and size gates','identical paired cohorts and labels','raw diagnostics never fill calibrated output','independent coefficient replay']))
    print('R16 VERIFIED',count,'predictions; error',error)
if __name__=='__main__':run()
