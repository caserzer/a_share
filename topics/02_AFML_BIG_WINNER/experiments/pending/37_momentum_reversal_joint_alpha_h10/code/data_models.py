"""New EP37 features, mature-only nested time fits and label-free prediction."""
import sys
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from core import *

def grid(days,offset=0):
    anchor=days.get_loc(pd.Timestamp('2021-01-11'))+offset
    entries=np.arange(anchor%10,len(days),10)
    return pd.DataFrame([dict(signal_date=days[e-1],entry_date=days[e],
                              exit_date=days[e+10] if e+10<len(days) else pd.NaT,
                              signal_idx=e-1,entry_idx=e,exit_idx=e+10,offset=offset)
                         for e in entries if e>=61])

def prepare():
    freeze()
    c=pd.read_parquet(PRIVATE/'qfq_close.parquet');o=pd.read_parquet(PRIVATE/'qfq_open.parquet')
    member=pd.read_parquet(PRIVATE/'daily_members.parquet').reindex_like(c).fillna(False).astype(bool)
    raw=dict(T15=c.shift(5)/c.shift(20)-1,T55=c.shift(5)/c.shift(60)-1,
             R1=-(c/c.shift(1)-1),R5=-(c/c.shift(5)-1))
    warm=(c.gt(0)&np.isfinite(c)).rolling(61).sum().eq(61)
    features=[];labels=[];coverage=[];cal=[]
    for offset in [0,5]:
        dates=grid(c.index,offset);cal.append(dates)
        for r in dates.itertuples():
            f=pd.DataFrame({k:v.iloc[r.signal_idx] for k,v in raw.items()})
            f['state']=classify(f.T55,-f.R5)
            elig=member.iloc[r.signal_idx]&warm.iloc[r.signal_idx]&f[BASE].notna().all(axis=1)&f.state.isin(STATES)
            coverage.append(dict(signal_date=r.signal_date,offset=offset,members=int(member.iloc[r.signal_idx].sum()),
                                 eligible=int(elig.sum()),zero=int((member.iloc[r.signal_idx]&f.state.eq('ZERO')).sum()),
                                 unknown=int((member.iloc[r.signal_idx]&f.state.eq('UNKNOWN')).sum())))
            f=f.loc[elig].copy()
            if len(f)<100:continue
            for k in BASE:f['raw_'+k]=f[k];f[k]=centered_rank(f[k])
            for a in BASE[:2]:
                for b in BASE[2:]:f[a+'_x_'+b]=f[a]*f[b]
            for state in STATES[1:]:f[state]=f.state.eq(state).astype(float)
            f.index.name='instrument';f=f.reset_index()
            for k in ['signal_date','entry_date','exit_date','signal_idx','entry_idx','exit_idx','offset']:f[k]=getattr(r,k)
            features.append(f)
            y=o.iloc[r.exit_idx]/o.iloc[r.entry_idx]-1 if r.exit_idx<len(c) else pd.Series(np.nan,index=c.columns)
            lab=f[['signal_date','instrument','offset','exit_date']].copy();lab['h10']=lab.instrument.map(y)
            good=lab.h10.notna();sd=lab.h10.std(ddof=0)
            if good.sum()>=100 and sd>1e-12:
                lab['Z']=(lab.h10-lab.h10.mean())/sd;lab['R']=centered_rank(lab.h10)
            else:lab['Z']=np.nan;lab['R']=np.nan
            labels.append(lab)
    fs=pd.concat(features,ignore_index=True);ls=pd.concat(labels,ignore_index=True)
    fs.to_parquet(CACHE/'features.parquet',index=False);ls.to_parquet(CACHE/'labels.parquet',index=False)
    pd.concat(cal).to_csv(OUT/'calendar.csv',index=False)
    pd.DataFrame(coverage).to_csv(OUT/'data_coverage.csv',index=False)
    record_stage('data_preparation',[CACHE/'features.parquet',CACHE/'labels.parquet',OUT/'calendar.csv',OUT/'data_coverage.csv'],
                 dict(rows=len(fs),label_values_not_used_for_eligibility=True))
    print('prepared',len(fs),'feature rows',flush=True)

def fit_linear(frame,cols,target,alpha,weighted=False):
    x=frame[cols].to_numpy(float);mean=x.mean(0);sd=x.std(0);sd[sd<1e-12]=1.
    weights=state_weights(frame) if weighted else np.ones(len(frame))
    m=Ridge(alpha=alpha).fit((x-mean)/sd,frame[target].to_numpy(float),sample_weight=weights)
    return dict(columns=cols,mean=mean.tolist(),sd=sd.tolist(),coef=m.coef_.tolist(),intercept=float(m.intercept_),alpha=alpha)

def predict(features,model):
    assert not {'h10','Z','R','future_return','target'}.intersection(features.columns)
    x=features[model['columns']].to_numpy(float)
    return ((x-np.array(model['mean']))/np.array(model['sd']))@np.array(model['coef'])+model['intercept']

def split(frame,cutoff,scheme,history_start):
    train=frame.loc[(frame.signal_date<=cutoff)&(frame.exit_date<=cutoff)&frame.Z.notna()&frame.R.notna()].copy()
    start=cutoff-pd.DateOffset(months=36) if scheme=='rolling36' else history_start
    train=train.loc[train.signal_date>=start]
    boundary=cutoff-pd.DateOffset(months=12)
    # Window boundaries, not discrete signal endpoints, define the 24-month minimum.
    if history_start>boundary-pd.DateOffset(months=24) or start>boundary-pd.DateOffset(months=24):
        return train,None,None,'INSUFFICIENT_INNER_HISTORY'
    valid=train.loc[train.signal_date>=boundary].copy()
    if valid.empty:return train,None,None,'NO_MATURE_VALIDATION'
    inner=train.loc[(train.signal_date<boundary)&(train.exit_date<valid.entry_date.min())].copy()
    if inner.empty:return train,None,None,'EMPTY_PURGED_INNER_TRAIN'
    assert inner.exit_date.max()<valid.entry_date.min()
    return train,inner,valid,''

def train():
    verify_freeze()
    f=pd.read_parquet(CACHE/'features.parquet');labels=pd.read_parquet(CACHE/'labels.parquet')
    predictions=[];receipts=[];selection=[];coefficients=[];weight_records=[]
    specifications=[('expanding',0,MODELS),('rolling36',0,['A_R','J_R']),('expanding',5,['A_R','J_R'])]
    model_dir=CACHE/'models';model_dir.mkdir(exist_ok=True)
    for scheme,offset,ids in specifications:
        base=f.loc[f.offset.eq(offset)].copy()
        history_start=base.signal_date.min()
        for quarter in sorted(base.loc[base.signal_date>='2021-01-01','signal_date'].dt.to_period('Q').unique()):
            cutoff=quarter.start_time-pd.Timedelta(nanoseconds=1)
            past=base.loc[base.signal_date<quarter.start_time].merge(
                labels.loc[(labels.offset==offset)&(labels.exit_date<=cutoff),['signal_date','instrument','h10','Z','R']],
                on=['signal_date','instrument'],validate='one_to_one')
            mature,inner,valid,reason=split(past,cutoff,scheme,history_start)
            test=base.loc[base.signal_date.dt.to_period('Q').eq(quarter)].copy()
            p=test[['signal_date','entry_date','exit_date','entry_idx','exit_idx','instrument','state','offset']+BASE].copy()
            p['scheme']=scheme;p['fold']=str(quarter);p['fit_cutoff']=cutoff
            p['MOM']=test[['T15','T55']].mean(axis=1);p['REV']=test[['R1','R5']].mean(axis=1);p['FIX']=(p.MOM+p.REV)/2
            for mid in ids:
                cols=BASE if mid.startswith('A_') else JOINT;target='Z' if mid.endswith('_Z') else 'R';weighted=mid=='J_RW'
                rec=dict(scheme=scheme,offset=offset,fold=str(quarter),model=mid,cutoff=cutoff,status=reason or 'OK',
                         train_rows=len(mature),train_start=mature.signal_date.min(),train_end=mature.signal_date.max(),
                         max_label_maturity=mature.exit_date.max(),inner_train_end=None,inner_last_exit=None,
                         validation_first_entry=None,validation_dates=0,alpha=None)
                if reason:p[mid]=np.nan;receipts.append(rec);continue
                scores={};models={}
                for alpha in [1.,10.,100.]:
                    m=fit_linear(inner,cols,target,alpha,weighted);models[alpha]=m
                    feat=valid.drop(columns=['h10','Z','R']);pred=predict(feat,m)
                    temp=valid[['signal_date','h10']].copy();temp['pred']=pred
                    scores[alpha]=temp.groupby('signal_date').apply(lambda z:rankcorr(z.pred,z.h10),include_groups=False)
                table=pd.DataFrame(scores);common=table.dropna()
                if len(common)<12:
                    rec['status']='INSUFFICIENT_COMMON_VALIDATION';p[mid]=np.nan;receipts.append(rec);continue
                mean=common.mean();best=mean.max();chosen=next(a for a in [10.,100.,1.] if mean[a]>=best-1e-12)
                for a,v in mean.items():selection.append(dict(scheme=scheme,offset=offset,fold=str(quarter),model=mid,alpha=a,validation_ic=v,dates=len(common),chosen=a==chosen))
                model=fit_linear(mature,cols,target,chosen,weighted)
                p[mid]=predict(test,model)
                mp=model_dir/f'{scheme}_o{offset}_{quarter}_{mid}.json';dump(mp,model)
                rec.update(alpha=chosen,inner_train_end=inner.signal_date.max(),inner_last_exit=inner.exit_date.max(),
                           validation_first_entry=valid.entry_date.min(),validation_dates=len(common),model_path=str(mp.relative_to(EP)),model_sha256=sha(mp))
                assert rec['max_label_maturity']<=cutoff
                for col,coef in zip(cols,model['coef']):coefficients.append(dict(scheme=scheme,offset=offset,fold=str(quarter),model=mid,feature=col,coefficient=coef))
                if weighted:
                    wr=mature[['signal_date','state']].copy();wr['weight']=state_weights(mature)
                    for (d,s),g in wr.groupby(['signal_date','state']):weight_records.append(dict(fold=str(quarter),signal_date=d,state=s,rows=len(g),total_weight=g.weight.sum(),effective_n=g.weight.sum()**2/(g.weight**2).sum()))
                receipts.append(rec)
            predictions.append(p)
            print('trained',scheme,offset,str(quarter),len(mature),flush=True)
    pred=pd.concat(predictions,ignore_index=True)
    pred.to_parquet(CACHE/'predictions.parquet',index=False)
    pd.DataFrame(receipts).to_csv(OUT/'folds.csv',index=False)
    pd.DataFrame(selection).to_csv(OUT/'inner_selection.csv',index=False)
    pd.DataFrame(coefficients).to_csv(OUT/'coefficients.csv',index=False)
    pd.DataFrame(weight_records).to_csv(OUT/'training_state_weights.csv.gz',index=False,compression='gzip')
    record_stage('training',[CACHE/'predictions.parquet',OUT/'folds.csv',OUT/'inner_selection.csv',OUT/'coefficients.csv'],
                 dict(model_files=len(list(model_dir.glob('*.json'))),prediction_interface_has_no_labels=True))

if __name__=='__main__':
    {'prepare':prepare,'train':train}[sys.argv[1]]()
