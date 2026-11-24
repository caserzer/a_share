from shared import *
from wide_sources import CACHE
sys.path.insert(0,str(PRIVATE.parent/'src'))
from common import release,read_sealed
from features import compute
from execution_status import opening_suspension

LOCAL=CACHE/'market'; LOCAL.mkdir(exist_ok=True)
SYMBOL=lambda c: ('SH' if c[0]=='6' else 'SZ')+c
FIELDS=['qfq_open','qfq_close','qfq_high','qfq_low','volume','money','turnover_rate','open','close','vendor_trade_status']

def prices():
    w=pd.read_parquet(OUT/'weights800.parquet')
    original=pd.read_parquet(PRIVATE/'qfq_close.parquet')
    symbols=sorted(set(w.con_code.str[-2:]+w.con_code.str[:6])|set(original.columns))
    root,manifest=release();sec=read_sealed(root,manifest,'inputs/normalized/securities.parquet')
    intervals=read_sealed(root,manifest,'inputs/normalized/code_intervals.parquet')
    days=original.index
    arrays={k:pd.DataFrame(np.nan,index=days,columns=symbols) for k in FIELDS}
    audit=[]
    for s in symbols:
        ids=set(sec.loc[sec.instrument.eq(s)|sec.metadata_instrument_v3.eq(s),'security_id'])
        ids.update(intervals.loc[intervals.instrument.eq(s),'security_id'])
        path=f'normalized/prices_qfq/{next(iter(ids))}.parquet' if len(ids)==1 else None
        ok=path in manifest
        audit.append(dict(instrument=s,unique_ids=len(ids),price_file=path,sha256=manifest[path]['sha256'] if ok else None))
        if not ok:continue
        g=read_sealed(root,manifest,path).set_index('date').reindex(days)
        for k in FIELDS:
            if k not in g: continue
            x=pd.to_numeric(g[k],errors='coerce'); conflict=k.replace('qfq_','')+'_conflict'
            if conflict in g:x=x.mask(g[conflict].fillna(False).astype(bool))
            if k.startswith('qfq_') or k in ['open','close']: x=x.where(x>0)
            arrays[k][s]=x
    np.testing.assert_allclose(arrays['qfq_close'][original.columns],original,equal_nan=True)
    for k,x in arrays.items():x.to_parquet(LOCAL/(k+'.parquet'))
    pd.DataFrame(audit).to_csv(OUT/'wide_price_inputs.csv',index=False)
    susp=pd.read_parquet(PRIVATE/'suspensions/daily.parquet')
    trade=arrays['vendor_trade_status'];state=pd.DataFrame(1.,index=days,columns=symbols)
    for r in susp[susp.suspend_type.eq('S')].itertuples():
        s=r.ts_code[-2:]+r.ts_code[:6];d=pd.Timestamp(r.trade_date)
        if s in state and d in days:
            opening=opening_suspension(r.suspend_timing)
            if opening is not False:state.at[d,s]=np.nan if opening is None else 0.
    state=state.mask(trade.notna()&state.notna()&trade.ne(state))
    state.to_parquet(LOCAL/'opening_trade_status_v2.parquet')
    (LOCAL/'suspensions').mkdir(exist_ok=True);(LOCAL/'limits').mkdir(exist_ok=True)
    link=LOCAL/'suspensions/daily.parquet'
    if not link.exists():link.symlink_to(PRIVATE/'suspensions/daily.parquet')
    lim=pd.concat([pd.read_parquet(PRIVATE/'limits/daily.parquet'),pd.read_parquet(OUT/'limits800.parquet')]).drop_duplicates()
    assert not lim.duplicated(['trade_date','ts_code']).any()
    lim.to_parquet(LOCAL/'limits/daily.parquet',index=False)

def panel():
    member300=pd.read_parquet(PRIVATE/'daily_members.parquet')
    h=outer(); week=pd.read_parquet(PRIVATE/'features.parquet',columns=['signal_date']).signal_date.unique()
    raw=pd.read_parquet(OUT/'effective800.parquet');raw['instrument']=raw.code.map(SYMBOL)
    dates=pd.DatetimeIndex(sorted(set(week)|set(h.signal_date)|set(raw.signal_date)))
    universe=raw.assign(member=True).pivot(index='signal_date',columns='instrument',values='member').reindex(dates).eq(True)
    data={k:pd.read_parquet(LOCAL/(k+'.parquet')) for k in FIELDS[:7]}
    c=data['qfq_close']; days=c.index; symbols=c.columns
    unknown=set(universe.columns)-set(symbols)
    (OUT/'wide_missing_price_names.json').write_text(json.dumps(sorted(unknown)))
    mem=universe.reindex(index=days,columns=symbols,fill_value=False)
    mem.to_parquet(LOCAL/'daily_members.parquet')
    marketclose=pd.read_parquet(PRIVATE/'market.parquet').close
    returns=c[member300.columns].pct_change(fill_method=None).where(member300)
    mu=returns.mean(axis=1);sd=returns.std(axis=1,ddof=0).where(returns.count(axis=1)>=100)
    parts=[]
    for start in range(0,len(symbols),100):
        names=symbols[start:start+100]
        close=c[names];o=data['qfq_open'][names]
        member=member300.reindex(columns=names,fill_value=False)
        kwargs=[data[k][names] for k in ['qfq_close','qfq_open','qfq_high','qfq_low','volume','money','turnover_rate']]
        feats=compute(*kwargs,member,marketclose)
        i,j=np.where(mem[names].to_numpy())
        xs=close.pct_change(fill_method=None).sub(mu,axis=0).div(sd,axis=0)
        old=member.to_numpy();was300=old[i,j]
        d={}
        for k in COLS:
            if k.startswith('xsret_lag'):
                lag=int(k[9:]);v=xs.shift(lag).to_numpy()[i,j]
                # Preserve the archived membership mask on overlap, including recent entrants.
                v[was300 & ~member.shift(lag,fill_value=False).to_numpy()[i,j]]=np.nan
            else:v=feats[k].to_numpy()[i,j]
            d[k]=v
        g=pd.DataFrame(d);g['instrument']=names[j];g['signal_date']=days[i];g['in300']=was300
        g['weekly_ok']=(close.notna().rolling(60).sum().ge(60).to_numpy()[i,j]) & (g[COLS].notna().mean(axis=1)>=.8)
        g['outer_ok']=(close.gt(0).rolling(61).sum().eq(61)&(close.shift(5)/close.shift(60)).ne(1)&(close/close.shift(5)).ne(1)).to_numpy()[i,j] & (g[COLS].notna().mean(axis=1)>=.8)
        g['h10']=(o.shift(-11)/o.shift(-1)-1).to_numpy()[i,j];g['entry_idx']=i+1;g['exit_idx']=i+11
        parts.append(g)
    f=pd.concat(parts,ignore_index=True)
    f.to_parquet(LOCAL/'wide_features.parquet',index=False)
    keys=h[KEY+COLS].merge(f[KEY+COLS],on=KEY,validate='1:1',suffixes=('','_wide'))
    for k in COLS:np.testing.assert_allclose(keys[k],keys[k+'_wide'],equal_nan=True,atol=1e-12,rtol=0)
    scores=[];parity=[];folds=[]
    for q,test300 in h.groupby(h.signal_date.dt.to_period('Q')):
        train=f[f.signal_date.isin(week)&f.weekly_ok&f.h10.notna()&(f.exit_idx<days.searchsorted(q.start_time))].copy()
        train['rank']=train.groupby('signal_date').h10.transform(lambda x:x.rank()/(len(x)+1)-.5)
        fit=ridge(train,COLS,'rank'); base=json.loads((OLD/'local_cache/models'/f'{q}_{BASE}.json').read_text())
        test=f[f.signal_date.isin(test300.signal_date)&f.outer_ok].sort_values(KEY).copy()
        meta=test[KEY+['in300','entry_idx','exit_idx','h10']].copy()
        x=test[COLS]
        meta['transfer']=predict(x,base);meta['wide_train']=predict(x,fit)
        overlap=test300[KEY].assign(original=predict(test300,base)).merge(meta,on=KEY,validate='1:1')
        np.testing.assert_allclose(overlap.original,overlap.transfer,atol=1e-12)
        parity.append(dict(quarter=str(q),original=len(test300),overlap=len(overlap),max_error=(overlap.original-overlap.transfer).abs().max()))
        scores.append(meta);folds.append(dict(quarter=str(q),rows=len(train),dates=train.signal_date.nunique(),last_maturity=str(days[train.exit_idx.max()].date()),model=fit))
    output=pd.concat(scores)
    output.to_parquet(OUT/'wide_scores.parquet',index=False)
    inner_dates=pd.read_parquet(OUT/'contributions.parquet',columns=['signal_date']).signal_date
    early=f[f.signal_date.isin(inner_dates)&(f.signal_date<h.signal_date.min())&f.outer_ok].copy()
    models=json.loads((ROUNDS/'51_earlier_replication/results/models.json').read_text())
    calibration=[]
    for q,g in early.groupby(early.signal_date.dt.to_period('Q')):
        calibration.append(g[KEY+['entry_idx','exit_idx','h10','in300']].assign(transfer=predict(g[COLS],models[f'{q}_{BASE}'])))
    pd.concat(calibration+[output],ignore_index=True).to_parquet(OUT/'wide_calibration_panel.parquet',index=False)
    pd.DataFrame(parity).to_csv(OUT/'wide_overlap.csv',index=False)
    (OUT/'wide_models.json').write_text(json.dumps(folds))
if __name__=='__main__': {'prices':prices,'panel':panel}[sys.argv[1]]()
