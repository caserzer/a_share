"""S2 encodings on identical rows; G2 form/loss/feature controls and frozen tree identity."""
from scale_common import *
from ep41inputs import pct

def reference_codes(raw, codes, tr, te, dates):
    transformed={kind:[np.empty((len(indices),raw.shape[1])) for indices in [tr,te]] for kind in ['C','D']}
    diagnostics=[]
    train_dates=dates[tr]
    for j,col in enumerate(raw.columns):
        values=raw.iloc[tr,j].to_numpy();ok=np.isfinite(values);values=values[ok]
        day_group=pd.Series(train_dates[ok])
        weight=(1/day_group.groupby(day_group).transform('size')).to_numpy()
        order=np.argsort(values,kind='stable');values=values[order];weight=weight[order]
        vals,start=np.unique(values,return_index=True)
        mass=np.add.reduceat(weight,start)
        midpoint=(mass.cumsum()-.5*mass)/mass.sum()
        for k,ix in enumerate([tr,te]):
            xx=raw.iloc[ix,j].to_numpy();rr=codes.iloc[ix,j].to_numpy()
            transformed['C'][k][:,j]=np.interp(rr,midpoint,vals)
            transformed['D'][k][:,j]=np.interp(xx,vals,midpoint,left=0.,right=1.)
        tt=raw.iloc[te,j].to_numpy()
        diagnostics.append((col,len(vals),np.isfinite(tt).sum(),np.sum((tt<vals[0])|(tt>vals[-1]))))
    return transformed,diagnostics

def alias_mask(raw):
    x=raw.copy()
    for i in range(20):
        pair=[f'ret_lag{i}',f'xsret_lag{i}']
        if i==0:pair.append('mom1')
        fail=x[pair].isna().any(axis=1)
        x.loc[fail,pair]=np.nan
    return x

def main():
    frame=data(COLS+['R'])
    raw=frame[STOCK].copy()
    common=alias_mask(raw)
    date=frame.signal_date.to_numpy()
    encs=[]
    for masked,x in [(False,raw),(True,common)]:
        groups=x.groupby(frame.signal_date,sort=False)
        encs.append((masked,x,groups.rank('average')/(groups.transform('count')+1)))
    ref=pd.read_parquet(EP41/'models/results/quarterly_scores.parquet',columns=KEY+['M1_raw','T','R'])
    learned=[];dist=[];stops=[]
    for q,train,test in outer_folds(frame):
        result=test[KEY+['entry_idx','R']].copy()
        tr=train.index.to_numpy();te=test.index.to_numpy();yt=train.y10.to_numpy()
        for masked,x,ranks in encs:
            suffix='_commonmask' if masked else ''
            levels,details=reference_codes(x,ranks,tr,te,date)
            dist.extend([(str(q),masked,*row) for row in details])
            pairs={'A':(x.iloc[tr],x.iloc[te]),'B':(ranks.iloc[tr],ranks.iloc[te]),**levels}
            for arm,(a,b) in pairs.items():
                a=pd.DataFrame(a,columns=STOCK);b=pd.DataFrame(b,columns=STOCK)
                med=a.median().fillna(0.)
                tree=fit_tree(a.fillna(med),yt)
                result['S2_'+arm+suffix]=tree.predict(b.fillna(med),num_threads=1)
                if arm=='A' and not masked:
                    tree.save_model(str(MODELS/f'{q}_raw.txt'))
                    med.to_csv(MODELS/f'{q}_median.csv',header=['median'],index_label='col')
        for size,cc in [(69,STOCK),(78,COLS)]:
            x=train[cc];m=x.median().fillna(0.);x=x.fillna(m);u=test[cc].fillna(m)
            result['ridge'+str(size)]=ep.predict(test[cc],ep.ridge(train,cc,'y10'))
            tree=mse_tree(x,yt)
            result['mse'+str(size)]=tree.predict(u,num_threads=1)
            if size==69:
                shallow=mse_tree(x,yt,depth=3)
                result['shallow']=shallow.predict(u,num_threads=1)
                n,record=early_rounds(train,cc,q,None)
                stops.append(record)
                early=mse_tree(x,yt,rounds=n)
                result['early']=early.predict(u,num_threads=1)
        check=result.merge(ref,on=KEY,validate='1:1',suffixes=('','_ref'))
        assert len(check)==len(result)
        np.testing.assert_allclose(check.S2_A,check.M1_raw,rtol=0,atol=1e-10)
        np.testing.assert_allclose(check.ridge78,check.R,rtol=0,atol=1e-10)
        result['original78tree']=check['T'].to_numpy()
        learned.append(result)
        print(q,'S2/G2',abs(check.S2_A-check.M1_raw).max(),flush=True)
    atomic_parquet(pd.concat(learned),RES/'model_scores.parquet')
    pd.DataFrame(dist,columns='fold common_mask feature reference_unique scored outside_range'.split()).to_csv(RES/'encoding_support.csv',index=False)
    pd.DataFrame(stops,columns='fold depth train_n max_inner_maturity valid_n first_valid_signal rounds mse'.split()).to_csv(RES/'early_folds.csv',index=False)
if __name__=='__main__':main()
