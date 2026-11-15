"""Fixed higher numerical precision for both model hypotheses."""
import pandas as pd
from sklearn.linear_model import Ridge,LogisticRegression
from sklearn.preprocessing import StandardScaler
from scipy.special import expit
from common import *
from train_r02 import F,target,train_masks,sample_weights
from versioned_observations import digest_json
K=KEY+['date','cohort','method','task','horizon','year']
M=['era','level','cohort','method','task','horizon','year']

def run():
    out=ROOT/'outputs/r106';out.mkdir(exist_ok=True);reads={};params=[];results=[]
    reference=ROOT/'outputs/r105/paired_predictions.parquet';paired=pd.read_parquet(reference);reads[str(reference)]=sha(reference)
    for rnd,panelname in [('r02','monthly_panel'),('r16','l1_monthly_panel')]:
        paths=[ROOT/f'data/{panelname}.parquet',ROOT/f'outputs/{rnd}/model_parameters.json'];reads.update({str(p):sha(p) for p in paths})
        panel=pd.read_parquet(paths[0]);panel['log_members']=np.log(panel.members);cache={}
        for old in json.loads(paths[1].read_text()):
            if old['method']!=old['cohort'] or old['method'] not in ['F','FD']:continue
            key=(old['era'],old['level'],old['cohort'])
            if key not in cache:
                cols=F+(['breadth21','breadth63'] if old['cohort']=='FD' else [])
                g=panel[panel.era.eq(old['era'])&panel.level.eq(old['level'])&panel.price_ready].dropna(subset=cols).copy();rank=g.groupby('date')[cols].transform(centered_rank);cache[key]=(g,rank)
            g,rank=cache[key];y,eligible=target(g,old['task'],old['horizon']);q=g[eligible].copy();q['y']=y[eligible]
            fit,cal,test=train_masks(q,old['year'],old['horizon'],old['task']);tr=q[fit];ca=q[cal];te=q[test]
            p=paired
            for k in M:p=p[p[k].eq(old[k])]
            p=p.copy();p['default_prediction']=p.prediction;p['default_unique_prediction']=p.unique_prediction;p['default_raw_prediction']=p.raw_prediction
            outputs={}
            for variant in ['duplicate','unique']:
                cols=old['columns'] if variant=='duplicate' else [c for c in old['columns'] if c not in ['past_excess20','past_excess60']]
                scaler=StandardScaler().fit(rank.loc[tr.index,cols]);x=scaler.transform(rank.loc[tr.index,cols]);xt=scaler.transform(rank.loc[te.index,cols])
                if old['task']=='return':
                    base=Ridge(alpha=10).fit(x,tr.y,sample_weight=sample_weights(tr));decision=base.predict(xt);value=decision;calibrator=None
                else:
                    base=LogisticRegression(C=1,tol=1e-10,max_iter=10000,random_state=3502).fit(x,tr.y,sample_weight=sample_weights(tr))
                    xc=scaler.transform(rank.loc[ca.index,cols]);ds=base.decision_function(xc).reshape(-1,1)
                    calibrator=LogisticRegression(C=1,tol=1e-10,max_iter=10000,random_state=3502).fit(ds,ca.y,sample_weight=sample_weights(ca))
                    decision=base.decision_function(xt);value=calibrator.predict_proba(decision.reshape(-1,1))[:,1]
                rec={k:old[k] for k in M+['n_fit','n_cal','n_test','train_months','cal_months','fit_max_maturity','cal_max_maturity']}
                rec.update(variant=variant,columns=cols,baseline_model_sha256=digest_json(old),scaler_mean=scaler.mean_.tolist(),scaler_scale=scaler.scale_.tolist(),coefficient=base.coef_.tolist(),intercept=np.asarray(base.intercept_).tolist(),calibration_coefficient=calibrator.coef_.tolist() if calibrator else None,calibration_intercept=calibrator.intercept_.tolist() if calibrator else None,fit_identity_sha256=digest_json(tr[KEY+['date']].astype(str).to_dict('records')),cal_identity_sha256=digest_json(ca[KEY+['date']].astype(str).to_dict('records')))
                params.append(rec);outputs[variant]=(value,decision,rec)
            fresh=te[KEY+['date']].copy();fresh['tight_raw']=outputs['duplicate'][1] if old['task']=='return' else expit(outputs['duplicate'][1]);fresh['tight_duplicate']=outputs['duplicate'][0];fresh['tight_unique']=outputs['unique'][0];fresh['tight_decision']=outputs['unique'][1]
            if old['task']=='return':fresh['tight_frozen']=outputs['unique'][0]
            else:
                basecal=outputs['duplicate'][2];fresh['tight_frozen']=expit(outputs['unique'][1]*np.asarray(basecal['calibration_coefficient']).item()+np.asarray(basecal['calibration_intercept']).item())
            p=p.merge(fresh,on=KEY+['date'],validate='one_to_one',how='outer',indicator=True);assert p._merge.eq('both').all();p=p.drop(columns='_merge')
            p['raw_prediction']=p.pop('tight_raw');p['prediction']=p.pop('tight_duplicate');p['unique_prediction']=p.pop('tight_unique');p['unique_decision']=p.pop('tight_decision');p['unique_frozen_calibration_prediction']=p.pop('tight_frozen');results.append(p)
        print(rnd,'done',flush=True)
    p=pd.concat(results,ignore_index=True);p.to_parquet(out/'paired_predictions.parquet',index=False);js(out/'model_parameters.json',params)
    for path in [Path(__file__),ROOT/'src/train_r02.py',ROOT/'src/common.py',ROOT/'protocols/r106.json']:reads[str(path)]=sha(path)
    js(out/'receipt.json',dict(reads=reads,models=len(params),outputs={n:sha(out/n) for n in ['paired_predictions.parquet','model_parameters.json']},adopted=False))

if __name__=='__main__':run()
