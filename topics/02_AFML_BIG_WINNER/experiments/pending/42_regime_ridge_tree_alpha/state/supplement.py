"""Independent frozen-model check, supplementary single-state arms and account diagnostics."""
from mixture import *
from engine import STORE,OUT800
from matching import covariates
from inputs42 import CACHE,ci

def check_early():
    keys=['signal_date','instrument','entry_idx']
    scores=pd.read_parquet(OUT/'scores.parquet')
    wide=pd.read_parquet(OUT/'wide_scores.parquet')
    rows=[]
    import json
    for kind,frame,files in [
        ('narrow',scores,sorted(CACHE.glob('block_*.parquet'))),
        ('wide',wide,sorted((CACHE/'wide').glob('early_*.parquet')))]:
        features=pd.concat(pd.read_parquet(p,filters=[('signal_date','>=',pd.Timestamp('2021-01-01')),('signal_date','<',pd.Timestamp('2021-01-08'))]) for p in files)
        df=features.merge(frame,on=keys,validate='1:1')
        for model in (['transfer'] if kind=='narrow' else ['transfer','refit']):
            src=OUT800/'models'/model/'2021Q1'
            ridge=json.loads((src/'ridge.json').read_text())
            tree=ci.lgb.Booster(model_file=str(src/'tree.txt'))
            cs=tree.feature_name()
            pred=tree.predict(df[cs].fillna(pd.read_json(src/'medians.json',typ='series')),num_threads=2)
            for tag,y in [('R',ci.predict(df[ci.COLS],ridge)),('T',pred)]:
                ref=df[tag if kind=='narrow' else model+'_'+tag]
                err=np.max(np.abs(y-ref))
                rows.append((kind,model,tag,len(df),err))
                assert err<1e-9,rows[-1]
    pd.DataFrame(rows,columns=['domain','fit','score','overlap_rows','max_abs_error']).to_csv(OUT/'early_model_parity.csv',index=False)

def single_states():
    m=market();board=Board(m,pd.read_parquet(OUT/'scores.parquet'))
    z=pd.read_parquet(OUT/'states.parquet').set_index('signal_date')
    fit=pd.read_csv(OUT/'main/weights_quarterly.csv').set_index('q')
    cal=Calibration(board,z)
    coefs=[];history=[]
    for q in pd.period_range('2021Q1','2026Q3',freq='Q'):
        spans=cal.spans(q)
        b=fit.at[str(q),'b']
        for j in [1,2,3]:
            runs={}
            for a in SLOPES:
                p=cal.packed(b,0,j,a)
                runs[a]=pd.concat([monthly(replay(m,p,s),m.days).net for s in spans])
            mat=pd.concat(runs,axis=1).dropna();means=mat.mean()
            a=int(means.idxmax());coefs.append((str(q),j+1,a))
            history.extend((str(q),j+1,k,len(mat),v) for k,v in means.items())
    dest=OUT/'single_states';dest.mkdir(exist_ok=True)
    coeff=pd.DataFrame(coefs,columns=['quarter','state','a']).pivot(index='quarter',columns='state',values='a')
    coeff.to_csv(dest/'coefficients.csv')
    pd.DataFrame(history,columns=['quarter','state','coefficient','months','mean_net']).to_csv(dest/'objectives.csv',index=False)
    b=fit.b.reindex(board.dates.to_period('Q').astype(str)).fillna(0).to_numpy()
    weights={'static':b}
    for j in [2,3,4]:
        a=coeff[j].reindex(board.dates.to_period('Q').astype(str)).fillna(0).to_numpy()
        s=z['Z'+str(j)].reindex(board.dates)
        weights['only_Z'+str(j)]=np.clip(b+a*.0875*(2*s-1).fillna(0),0,.35)
    pd.DataFrame(weights,index=board.dates).to_parquet(dest/'weights.parquet')
    plans={k:board.pack(v) for k,v in weights.items()}
    mo=run_accounts(board,plans,SEG300,dest,set(plans))
    pd.concat([contrast(mo,'only_Z'+str(j)+f,'static'+f) for j in [2,3,4] for f in ['', '_2fee']]).to_csv(dest/'comparisons.csv',index=False)

def details():
    d=OUT/'main';m=market()
    weights=pd.read_parquet(d/'weights_daily.parquet')
    mo=pd.read_csv(d/'monthly.csv')
    c=[]
    for f in ['', '_2fee']:
        indexed=mo.set_index(['arm','segment','month']).select_dtypes('number').sort_index()
        score=indexed.loc['dynamic'+f]-indexed.loc['static'+f]
        for b in ['budget','budgetK']:
            allocated=indexed.loc[b+'_dynamic'+f]-indexed.loc[b+'_static'+f]
            two=pd.concat([score.reset_index().assign(arm='score'),allocated.reset_index().assign(arm=b)])
            c.append(contrast(two,'score',b).assign(fee_multiple=2 if f else 1))
    pd.concat(c).to_csv(d/'g4_double_difference.csv',index=False)
    z=pd.read_parquet(OUT/'states.parquet').set_index('signal_date')
    take=weights.loc['2021-01-08':].copy()
    take['state']=np.where(take.Z1<1/3,'low',np.where(take.Z1>2/3,'high','mid'))
    take['entry']=m.days[take.entry_idx]
    take['segment']=np.where(take.entry>=pd.Timestamp(SEG300[1][0]),2,1)
    periods=(take.state.ne(take.state.shift())|take.segment.ne(take.segment.shift())).cumsum()
    sw=take.reset_index(names='decision').groupby(periods.to_numpy()).agg(segment=('segment','first'),state=('state','first'),first=('decision','first'),last=('decision','last'),trading_days=('entry','size'),first_age=('state_age','first'))
    sw.to_csv(d/'g6_transitions.csv',index=False)
    q=take.index.to_period('Q')
    targets=pd.read_parquet(d/'targets.parquet')
    target={arm:g.set_index('entry_idx').stock_indices.map(set) for arm,g in targets.groupby('arm')}
    take['seats_changed']=[len(target['dynamic'][e]-target['static'][e]) for e in take.entry_idx]
    flows=[]
    for seg in [1,2]:
        tr=pd.read_parquet(d/f'trace_dynamic_{seg}.parquet')
        for t in tr.loc[(tr.flow>0)&(tr.target>0)].itertuples(index=False):
            if t.stock in target['dynamic'].get(t.day,set())-target['static'].get(t.day,set()):
                flows.append((t.day,t.flow,t.fee/.001))
    rep=pd.DataFrame(flows,columns=['entry','buy_before_cross','broker_buy']).groupby('entry').sum()
    for v in rep:take[v]=take.entry_idx.map(rep[v]).fillna(0)
    take['changed']=abs(take.dynamic-take.static)>1e-12
    take['clipped']=((take.dynamic==0)|(take.dynamic==.35))
    take.groupby(q).agg(dates=('entry','size'),changed_days=('changed','sum'),clipped_days=('clipped','sum'),seats_changed=('seats_changed','sum'),avg_static=('static','mean'),avg_dynamic=('dynamic','mean'),changed_target_buy=('buy_before_cross','sum'),market_buy=('broker_buy','sum')).to_csv(d/'d5_quarterly_activity.csv')
    # Explicit style and cash measures for both implementations, weighted by target capital.
    cap,adv,vol,industry,_=covariates(m)
    base=pd.read_parquet(OUT/'scores.parquet',columns=['entry_idx','instrument'])
    obs={int(e):m.symbols.get_indexer(v.instrument) for e,v in base.groupby('entry_idx')}
    by_e={int(e):list(g.itertuples(index=False)) for e,g in targets[targets.arm.isin(['dynamic','static','budget_dynamic','budget_static','budgetK_dynamic','budgetK_static'])].groupby('entry_idx')}
    rows=[]
    for e in take.entry_idx:
        pool=obs[e];i=e-1
        ranks=pd.DataFrame({'cap':cap[i,pool],'adv':adv[i,pool],'vol':vol[i,pool]},index=pool).rank(pct=True)
        overlap=target['R'][e]&target['T'][e]
        for t in by_e[e]:
            ids=t.stock_indices;w=t.weights
            style=ranks.loc[ids]
            nums=(style.mul(w,axis=0).sum()/style.notna().mul(w,axis=0).sum()).to_list()
            rows.append((e,t.arm,len(ids),sum(v for j,v in zip(ids,w) if j in overlap),*nums))
    pd.DataFrame(rows,columns=['entry_idx','arm','names','overlapping_target_capital','cap_pct','adv_pct','vol_pct']).to_parquet(d/'g4_styles.parquet',index=False)

if __name__=='__main__':
    import sys
    {'parity':check_early,'single':single_states,'details':details}[sys.argv[1]]()

