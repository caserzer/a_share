"""Fixed unique-direction penalty comparison; preserves original population and splits."""
import pandas as pd
from sklearn.linear_model import Ridge,LogisticRegression
from sklearn.preprocessing import StandardScaler
from scipy.special import expit
from common import *
from train_r02 import F,target,train_masks,sample_weights
from versioned_observations import digest_json

K=KEY+['date','cohort','method','task','horizon','year']

def run():
    out=ROOT/'outputs/r105';out.mkdir(exist_ok=True);reads={};results=[];parameters=[];ledgers=[]
    for rnd,panelname in [('r02','monthly_panel'),('r16','l1_monthly_panel')]:
        paths=[ROOT/f'data/{panelname}.parquet',ROOT/f'outputs/{rnd}/model_parameters.json',ROOT/f'outputs/{rnd}/predictions.parquet',ROOT/f'outputs/{rnd}/fold_ledger.csv']
        reads.update({str(p):sha(p) for p in paths});panel=pd.read_parquet(paths[0]);panel['log_members']=np.log(panel.members)
        models=[m for m in json.loads(paths[1].read_text()) if m['method']==m['cohort'] and m['method'] in ['F','FD']]
        predictions=pd.read_parquet(paths[2]);ledger=pd.read_csv(paths[3]);ledgers.append(ledger[ledger.cohort.isin(['F','FD'])])
        cached={}
        for m in models:
            cachekey=(m['era'],m['level'],m['cohort'])
            if cachekey not in cached:
                fullcols=F+(['breadth21','breadth63'] if m['cohort']=='FD' else [])
                g=panel[panel.era.eq(m['era'])&panel.level.eq(m['level'])&panel.price_ready].dropna(subset=fullcols).copy()
                rank=g.groupby('date')[fullcols].transform(centered_rank);cached[cachekey]=(g,rank)
            g,rank=cached[cachekey];cols=[c for c in m['columns'] if c not in ['past_excess20','past_excess60']]
            y,eligible=target(g,m['task'],m['horizon']);q=g[eligible].copy();q['y']=y[eligible]
            fit,cal,test=train_masks(q,m['year'],m['horizon'],m['task']);tr=q[fit];ca=q[cal];te=q[test]
            assert (len(tr),len(ca),len(te))==(m['n_fit'],m['n_cal'],m['n_test'])
            scaler=StandardScaler().fit(rank.loc[tr.index,cols]);x=scaler.transform(rank.loc[tr.index,cols]);xt=scaler.transform(rank.loc[te.index,cols]);w=sample_weights(tr)
            if m['task']=='return':
                model=Ridge(alpha=10).fit(x,tr.y,sample_weight=w);prediction=model.predict(xt);decision=prediction;frozen=prediction;platt=None
            else:
                model=LogisticRegression(C=1,max_iter=2000,random_state=3502).fit(x,tr.y,sample_weight=w)
                xc=scaler.transform(rank.loc[ca.index,cols]);ds=model.decision_function(xc).reshape(-1,1)
                platt=LogisticRegression(C=1,max_iter=2000,random_state=3502).fit(ds,ca.y,sample_weight=sample_weights(ca))
                decision=model.decision_function(xt);prediction=platt.predict_proba(decision.reshape(-1,1))[:,1]
                frozen=expit(decision*np.asarray(m['calibration_coefficient']).item()+np.asarray(m['calibration_intercept']).item())
            p=predictions
            for k in ['era','level','cohort','method','task','horizon','year']:p=p[p[k].eq(m[k])]
            fresh=te[KEY+['date']].copy();fresh['unique_prediction']=prediction;fresh['unique_decision']=decision;fresh['unique_frozen_calibration_prediction']=frozen
            paired=p.merge(fresh,on=KEY+['date'],validate='one_to_one',how='outer',indicator=True);assert paired._merge.eq('both').all();paired=paired.drop(columns='_merge');results.append(paired)
            rec={k:m[k] for k in ['era','level','cohort','method','task','horizon','year','n_fit','n_cal','n_test','train_months','cal_months','fit_max_maturity','cal_max_maturity']}
            rec.update(columns=cols,baseline_model_sha256=digest_json(m),scaler_mean=scaler.mean_.tolist(),scaler_scale=scaler.scale_.tolist(),coefficient=model.coef_.tolist(),intercept=np.asarray(model.intercept_).tolist(),calibration_coefficient=platt.coef_.tolist() if platt is not None else None,calibration_intercept=platt.intercept_.tolist() if platt is not None else None,fit_identity_sha256=digest_json(tr[KEY+['date']].astype(str).to_dict('records')),cal_identity_sha256=digest_json(ca[KEY+['date']].astype(str).to_dict('records')))
            parameters.append(rec)
        print(rnd,'complete',len(models),flush=True)
    pd.concat(results,ignore_index=True).to_parquet(out/'paired_predictions.parquet',index=False);pd.concat(ledgers,ignore_index=True).to_csv(out/'original_fold_ledger.csv',index=False);js(out/'model_parameters.json',parameters)
    for p in [Path(__file__),ROOT/'src/train_r02.py',ROOT/'protocols/r105.json',ROOT/'src/common.py']:reads[str(p)]=sha(p)
    js(out/'receipt.json',dict(reads=reads,models=len(parameters),outputs={n:sha(out/n) for n in ['paired_predictions.parquet','model_parameters.json','original_fold_ledger.csv']},adopted=False))

if __name__=='__main__':run()
