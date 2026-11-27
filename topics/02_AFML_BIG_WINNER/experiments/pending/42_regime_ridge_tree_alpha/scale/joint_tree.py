"""Fit the registered depth-three early-stopped ordinary MSE tree for D1.3 and G2."""
from scale_common import *

def main():
    frame=data(STOCK)
    frames=[];audit=[]
    for q,train,test in outer_folds(frame):
        rounds,record=early_rounds(train,STOCK,q,3)
        med=train[STOCK].median().fillna(0.)
        model=mse_tree(train[STOCK].fillna(med),train.y10,rounds,3)
        model.save_model(str(MODELS/f'{q}_joint.txt'))
        out=test[KEY+['entry_idx']].copy()
        out['shallow_early']=model.predict(test[STOCK].fillna(med),num_threads=1)
        frames.append(out);audit.append(record)
        print(q,rounds,flush=True)
    atomic_parquet(pd.concat(frames),RES/'shallow_early.parquet')
    pd.DataFrame(audit,columns='fold depth train_n max_inner_maturity valid_n first_valid_signal rounds mse'.split()).to_csv(RES/'shallow_early_folds.csv',index=False)
if __name__=='__main__':main()
