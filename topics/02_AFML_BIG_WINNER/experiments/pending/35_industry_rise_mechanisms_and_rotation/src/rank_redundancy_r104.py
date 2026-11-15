"""Audit structural duplicate ranks without selecting a new predictive model."""
import pandas as pd
from scipy.special import expit
from common import *
from train_r02 import F
from versioned_observations import digest_json

PAIRS=[('mom20','past_excess20'),('mom60','past_excess60')]

def compress(x,m):
    cols=m['columns'];coef=np.asarray(m['coefficient']).ravel();keep=[c for c in cols if c not in ['past_excess20','past_excess60']]
    xc=x[:,[cols.index(c) for c in keep]].copy();bc=coef[[cols.index(c) for c in keep]].copy()
    for a,b in PAIRS:
        j=keep.index(a);xc[:,j]*=np.sqrt(2);bc[j]=(coef[cols.index(a)]+coef[cols.index(b)])/np.sqrt(2)
    return xc,bc,keep

def run():
    out=ROOT/'outputs/r104';out.mkdir(exist_ok=True);rows=[];folds=[];reads={}
    for rnd,panelname in [('r02','monthly_panel'),('r16','l1_monthly_panel')]:
        paths=[ROOT/f'data/{panelname}.parquet',ROOT/f'outputs/{rnd}/model_parameters.json',ROOT/f'outputs/{rnd}/predictions.parquet']
        reads.update({str(p):sha(p) for p in paths});panel=pd.read_parquet(paths[0]);panel['log_members']=np.log(panel.members)
        models=json.loads(paths[1].read_text());pred=pd.read_parquet(paths[2])
        for (era,level),base in panel[panel.price_ready].groupby(['era','level']):
          for method in ['F','FD']:
            cols=F+(['breadth21','breadth63'] if method=='FD' else [])
            g=base.dropna(subset=cols).copy();rank=g.groupby('date')[cols].transform(centered_rank)
            diag=g[KEY+['date']].copy();diag['cohort']=method
            for a,b in PAIRS:
                diag[a+'_rank']=rank[a];diag[b+'_rank']=rank[b];diag[a+'_difference']=rank[a]-rank[b]
            rows.append(diag)
            selected=[m for m in models if m['era']==era and m['level']==level and m['method']==method and m['cohort']==method]
            for m in selected:
                c=np.asarray(m['coefficient']).ravel();mu=np.asarray(m['scaler_mean']);sd=np.asarray(m['scaler_scale'])
                exact=all((rank[a]==rank[b]).all() and mu[cols.index(a)]==mu[cols.index(b)] and sd[cols.index(a)]==sd[cols.index(b)] for a,b in PAIRS)
                rec={k:m[k] for k in ['era','level','cohort','method','task','horizon','year']};rec.update(model_sha256=digest_json(m),rank_rows=len(g),compression_status='exact_duplicate_columns' if exact else 'not_exact_do_not_compress')
                if exact:
                    x=(rank.to_numpy()-mu)/sd;xc,bc,keep=compress(x,m)
                    intercept=np.asarray(m['intercept']).item();original=x@c+intercept;merged=xc@bc+intercept
                    asym=sum((c[cols.index(a)]-c[cols.index(b)])**2/2 for a,b in PAIRS)
                    rec.update(max_decision_error=float(abs(original-merged).max()),old_l2_squared=float(c@c),compressed_l2_squared=float(bc@bc),asymmetry_penalty=float(asym),max_pair_coefficient_difference=max(abs(c[cols.index(a)]-c[cols.index(b)]) for a,b in PAIRS),compressed_columns=','.join(keep))
                    p=pred[pred.era.eq(era)&pred.level.eq(level)&pred.cohort.eq(method)&pred.method.eq(method)&pred.task.eq(m['task'])&pred.horizon.eq(m['horizon'])&pred.year.eq(m['year'])]
                    lookup=g[KEY+['date']].copy();lookup['merged_decision']=merged
                    joined=p.merge(lookup,on=KEY+['date'],validate='one_to_one',how='left');assert joined.merged_decision.notna().all()
                    value=joined.merged_decision.to_numpy()
                    if m['task']!='return':value=expit(value*np.asarray(m['calibration_coefficient']).item()+np.asarray(m['calibration_intercept']).item())
                    rec.update(test_rows=len(joined),max_prediction_error=float(abs(value-joined.prediction).max()))
                folds.append(rec)
    d=pd.concat(rows,ignore_index=True);d.to_parquet(out/'rank_pairs.parquet',index=False)
    f=pd.DataFrame(folds);f.to_csv(out/'model_compression.csv',index=False)
    summaries=[]
    for key,g in d.groupby(['era','level','cohort']):
        for a,b in PAIRS:summaries.append(dict(zip(['era','level','cohort'],key),pair=a+' / '+b,rows=len(g),dates=g.date.nunique(),exact_equal=int(g[a+'_difference'].eq(0).sum()),within_tolerance=int(g[a+'_difference'].abs().le(1e-14).sum()),max_difference=float(g[a+'_difference'].abs().max())))
    js(out/'summary.json',dict(rank_comparisons=summaries,models=len(f),compressible=int(f.compression_status.eq('exact_duplicate_columns').sum()),formal_test_rows=int(f.test_rows.sum()) if 'test_rows' in f else 0))
    for p in [Path(__file__),ROOT/'protocols/r104.json',ROOT/'src/common.py']:reads[str(p)]=sha(p)
    js(out/'receipt.json',dict(reads=reads,outputs={n:sha(out/n) for n in ['rank_pairs.parquet','model_compression.csv','summary.json']},refitted_models=0))
    print((out/'summary.json').read_text())

if __name__=='__main__':run()
