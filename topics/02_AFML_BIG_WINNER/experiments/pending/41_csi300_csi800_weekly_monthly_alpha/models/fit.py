from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
import json
from sklearn.metrics import roc_auc_score
from ep41inputs import *
import lightgbm as lgb

PARAM=dict(ep.PARAMS,num_threads=1)
def fit_tree(x,y,params=None,rounds=80):
    ds=lgb.Dataset(x,label=y,free_raw_data=False)
    cfg=PARAM| (params or {})
    warm=lgb.train(dict(cfg,objective='regression'),ds,num_boost_round=min(rounds,20))
    if rounds<=20:return warm
    y=np.asarray(y)
    def grad(p,d):return 2*(p-y),np.full(len(y),2.)
    return lgb.train(dict(cfg,objective=grad),ds,num_boost_round=rounds-20,init_model=warm)

def oof(q):
    cut=q.start_time
    train=D[D.weekly & D.m10.lt(cut) & D.y10.notna()]
    # Every historical quarter included here is earlier and has mature training labels.
    if train.signal_date.dt.to_period('Q').nunique()<4 or train.signal_date.min()>cut-pd.DateOffset(years=1)+pd.Timedelta(days=8):return pd.DataFrame()
    test=D[(Q==q) & D.weekly]
    base=ep.predict(test[COLS],ep.ridge(train,COLS,'y10'))
    out=test[KEY+['event','m10']].copy()
    out['R_oof']=base
    order=out.sort_values(['R_oof','instrument'],ascending=False).groupby('signal_date')
    out['in_core']=False
    out.loc[order.cumcount().loc[lambda r:r<order.R_oof.transform('size')//10].index,'in_core']=True
    known=train.dropna(subset=['event'])
    out['history']=known.event.mean()
    for name,cc in [('inc',COLS),('tail',COLS+TAIL)]:
        model=lgb.train(dict(PARAM,objective='binary',boost_from_average=True),lgb.Dataset(known[cc],label=known.event),num_boost_round=80)
        out[name]=model.predict(test[cc],num_threads=1)
    return out

def metrics(g,p):
    y=g.event.to_numpy();v=g[p].to_numpy()
    b=np.digitize(v,[.02,.05,.1,.2,.5])
    return (roc_auc_score(y,v),np.mean((v-y)**2),sum(abs((v-y)[b==k].sum()) for k in np.unique(b))/len(v))

def unique_cols(x):
    ordered=[c for c in x if c.startswith('ret_lag')]+[c for c in x if not c.startswith('ret_lag')]
    representatives=[]
    mapping={}
    for c in ordered:
        a=x[c].to_numpy()
        # Quickly exclude candidates whose first observations already differ.
        rep=next((p for p in representatives if np.allclose(a[:64],x[p].to_numpy()[:64],rtol=0,atol=1e-12,equal_nan=True) and np.allclose(a,x[p],rtol=0,atol=1e-12,equal_nan=True)),None)
        mapping[c]=rep or c
        if rep is None:representatives.append(c)
    return [c for c in x if c in representatives],mapping

def fold(q):
    cut=q.start_time
    tr=D[D.weekly & D.m10.lt(cut) & D.y10.notna()]
    te=D[(Q==q) & D.outer]
    result=te[KEY+['entry_idx','R','T','l1_name','l2_code','pseudo','h5','h10','h20','vol20','mom20','event']].copy()
    common=tr.loc[tr.R_oof.notna()]
    assert tr.m10.max()<cut<=te.signal_date.min() and len(common)
    v=OOF[OOF.in_core & OOF.m10.lt(cut)].dropna(subset=['event'])
    mt={name:metrics(v,name) for name in ['inc','tail','history']}
    passed=(v.event.value_counts().reindex([0,1],fill_value=0)>=20).all() and v.groupby('event').signal_date.nunique().min()>=4 and mt['tail'][0]>=.55 and mt['tail'][0]>mt['inc'][0] and mt['tail'][1]<min(mt['inc'][1],mt['history'][1]) and mt['tail'][2]<mt['inc'][2]
    known=tr.dropna(subset=['event'])
    risk=lgb.train(dict(PARAM,objective='binary',boost_from_average=True),lgb.Dataset(known[COLS+TAIL],label=known.event),num_boost_round=80)
    result['risk']=risk.predict(te[COLS+TAIL],num_threads=1)
    result['veto_enabled']=bool(passed)
    audit={'fold':str(q),'train_rows':len(tr),'train_weeks':tr.signal_date.nunique(),'common_rows':len(common),'common_weeks':common.signal_date.nunique(),'first_oof':str(common.signal_date.min().date()),'max_maturity':str(tr.m10.max().date()),'outer_start':str(te.signal_date.min().date()),'events':int(v.event.sum()),'non_events':int((1-v.event).sum()),'veto':bool(passed),'veto_metrics':mt,'trees':{},'maps':{}}
    for tag,inds in [('industry','l1_name'),('pseudo','pseudo'),('l2','l2_code')]:
        result['I_'+tag]=ep.predict(te[COLS],ep.ridge(tr,COLS,'y_'+inds))
    joint=tr[tr.m20.lt(cut)&tr[['h5','h10','h20']].notna().all(axis=1)].copy()
    for n in [5,10,20]:
        joint['joint_y']=pct(joint['h'+str(n)],joint.signal_date)
        result['E_h'+str(n)]=ep.predict(te[COLS],ep.ridge(joint,COLS,'joint_y'))
    audit['joint_rows']=len(joint);audit['joint_latest']=str(joint.m20.max().date())
    for name,rep,cohort,resid,variant in SPECS:
        cohort=tr if cohort=='all' else common
        arr=FEATURES[rep]
        x=arr.loc[cohort.index];tx=arr.loc[te.index]
        params={}
        if 'unique' in variant:
            cc,mapping=unique_cols(x);audit['maps'][name]=mapping
            x=x[cc];tx=tx[cc]
        if variant=='family':
            cc=[c for c in x if not c.startswith('xsret_lag') and c!='mom1']
            x=x[cc];tx=tx[cc]
        if '08' in variant:params['feature_fraction']=.8
        if variant=='depth3':params['max_depth']=3
        med=x.median().fillna(0)
        y=cohort.y10-(cohort.R_oof if resid else 0)
        rounds=80
        if variant=='stop':
            valid=cohort.signal_date.ge(cut-pd.DateOffset(months=6))
            inner=~valid & cohort.m10.lt(cohort.loc[valid,'signal_date'].min()+pd.Timedelta(days=1))
            im=x[inner].median().fillna(0)
            probe=fit_tree(x[inner].fillna(im),y[inner],params)
            valid_x=x[valid].fillna(im)
            stage=probe.predict(valid_x,pred_leaf=True,num_threads=1)
            losses=[]
            pred=np.zeros(valid.sum())
            for k in range(probe.num_trees()):
                leaves=stage[:,k];values=np.array([probe.get_leaf_output(k,j) for j in range(leaves.max()+1)])
                pred+=values[leaves];losses.append(np.mean((pred-y[valid])**2))
            rounds=int(np.argmin(losses)+1)
            audit['inner_max_maturity']=str(cohort.loc[inner,'m10'].max().date())
        tree=fit_tree(x.fillna(med),y,params,rounds)
        pred=tree.predict(tx.fillna(med),num_threads=1)
        result[name]=(te.R+pred) if resid else pred
        if resid: result[name+'_half']=te.R+.5*pred
        dump=tree.dump_model()
        splits=[]
        def visit(node):
            if 'split_feature' in node:
                splits.append((x.columns[node['split_feature']],node['threshold']))
                visit(node['left_child']);visit(node['right_child'])
        for branch in dump['tree_info']:visit(branch['tree_structure'])
        audit['trees'][name]={'n':rounds,'train_mse':float(np.mean((tree.predict(x.fillna(med),num_threads=1)-y)**2)), 'splits':splits}
    result.to_parquet(CACHE/(str(q)+'_pred.parquet'),index=False)
    (OUT/(str(q)+'_fold.json')).write_text(json.dumps(audit,default=float)+'\n')
    print(q,flush=True)

SPECS=[('M1_'+r,r,'all',False,'full') for r in ['raw','global','industry']]
SPECS += [('M1_'+r+'_'+v,r,'all',False,v) for r in ['global','industry'] for v in ['unique','family']]
SPECS += [('M2_'+r+'_'+t,r,'common',t=='res','full') for r in ['raw','global'] for t in ['direct','res']]
SPECS += [('M3_'+v,'global','common',True,v) for v in ['depth3','08','stop','unique','unique08']]
if __name__=='__main__':
    D=pd.read_parquet(CACHE/'panel.parquet')
    Q=D.signal_date.dt.to_period('Q')
    FEATURES={'raw':D[STOCK],**{r:pd.read_parquet(CACHE/(r+'.parquet')) for r in ['global','industry']}}
    qs=sorted(Q.unique())
    context=get_context('fork')
    with ProcessPoolExecutor(3,mp_context=context) as pool: OOF=pd.concat(pool.map(oof,qs))
    OOF.to_parquet(OUT/'weekly_oof.parquet',index=False)
    D['R_oof']=OOF.R_oof.reindex(D.index)
    with ProcessPoolExecutor(4,mp_context=context) as pool:list(pool.map(fold,sorted(Q[D.outer].unique())))
