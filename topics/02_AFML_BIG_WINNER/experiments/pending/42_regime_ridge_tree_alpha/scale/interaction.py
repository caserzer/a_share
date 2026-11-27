"""Fold-specific linear interactions and the pre-2021 nested daily challenger scores."""
from scale_common import *

def early_history(frame):
    blocks=sorted(Path('/tmp/ep42_regime_r1_inputs').glob('block_*.parquet'))
    early=pd.concat([pd.read_parquet(f,columns=KEY+['entry_idx']+STOCK,filters=[('signal_date','>=',pd.Timestamp('2019-01-01')),('signal_date','<',pd.Timestamp('2021-01-01'))]) for f in blocks]).sort_values(KEY)
    out=[];audits=[]
    for q,t in early.groupby(early.signal_date.dt.to_period('Q')):
        tr=frame.loc[frame.weekly & frame.m10.lt(q.start_time) & frame.y10.notna()]
        n,record=early_rounds(tr,STOCK,q,3)
        med=tr[STOCK].median().fillna(0.)
        mod=mse_tree(tr[STOCK].fillna(med),tr.y10,n,3)
        z=t[KEY+['entry_idx']].copy()
        z['shallow_early']=mod.predict(t[STOCK].fillna(med),num_threads=1)
        out.append(z);audits.append(record)
    atomic_parquet(pd.concat(out),RES/'shallow_early_history.parquet')
    pd.DataFrame(audits,columns='fold depth train_n max_inner_maturity valid_n first_valid_signal rounds mse'.split()).to_csv(RES/'early_history_folds.csv',index=False)

def main():
    frame=data(COLS+['R'])
    early_history(frame)
    z=pd.read_parquet(EP42/'state/results/states.parquet').set_index('signal_date').Z1
    frame['Z1']=frame.signal_date.map(z)
    xcols=[];icols=[]
    for col,sign in [('mom5',-1),('mom20',1),('money_rel20',1)]:
        f='pct_'+col;ix='int_'+col
        g=frame[col].groupby(frame.signal_date)
        frame[f]=(sign*(g.rank()/(g.transform('count')+1)-.5)).fillna(0.)
        frame[ix]=frame[f]*(frame.Z1*2-1).fillna(0.)
        xcols.append(f);icols.append(ix)
    preds=[];coef=[]
    for q,tr,te in outer_folds(frame):
        out=te[KEY+['entry_idx']].copy()
        for name,cc in [('main',COLS+xcols),('interaction',COLS+xcols+icols)]:
            model=ep.ridge(tr,cc,'y10')
            out['G3_'+name]=ep.predict(te[cc],model)
            for col,beta in zip(cc,model['coef']):
                if col in xcols+icols:coef.append((str(q),name,col,beta,len(tr),tr.Z1.notna().mean()))
        preds.append(out)
    atomic_parquet(pd.concat(preds),RES/'G3_scores.parquet')
    pd.DataFrame(coef,columns='quarter arm feature standardized_coefficient train_rows known_state_share'.split()).to_csv(RES/'G3_coefficients.csv',index=False)
if __name__=='__main__':main()
