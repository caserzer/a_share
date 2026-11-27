"""Historical event and cross-listed candidate replays; all times precede entry."""
from pathlib import Path
import gzip,json,sys
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
EP=HERE.parents[1]
OUTDIR=HERE/'results'
sys.path.insert(0,str(EP/'p2'))
from inputs import market,targets,SEGMENTS,industries,PRIVATE
from book import funded
from runpy import run_path
monthly=run_path(str(EP/'p2/summarize.py'))['monthly']

def events(m):
    raw=HERE/'raw/events'
    def read(api):
        frames=[]
        for p in sorted(raw.glob(api+'_*.json.gz')):
            o=json.loads(gzip.decompress(p.read_bytes()))['data']
            f=pd.DataFrame(o['items'],columns=o['fields'])
            if len(f):frames.append(f)
        d=pd.concat(frames).drop_duplicates()
        d['year']=d.end_date.str[:4].astype(int)
        assert d.end_date.str.endswith('1231').all()
        return d
    forecasts=read('forecast_vip')
    forecast_dates=forecasts.ann_date.where(forecasts.first_ann_date.isna(),forecasts.first_ann_date)
    forecasts['first']=pd.to_datetime(forecast_dates)
    flash=read('express_vip');flash['first']=pd.to_datetime(flash.ann_date)
    income=read('income_vip')
    income=income[income.report_type.astype(str)=='1'].copy()
    income['first']=pd.concat([pd.to_datetime(income.ann_date),pd.to_datetime(income.f_ann_date)],axis=1).max(axis=1)
    group=['ts_code','year']
    times=pd.concat([f.groupby(group)['first'].min().rename(k) for k,f in [('guidance',forecasts),('express',flash),('formal',income)]],axis=1)
    grouped=income.merge(times.formal,on=group)
    # Conflicting basic EPS on the first formal notice cannot establish the original.
    eps=grouped[grouped['first']==grouped.formal].groupby(group).basic_eps.agg(['min','max'])
    times['eps']=eps['min'].where(eps['min']==eps['max'])
    times['earliest']=times[['formal','guidance','express']].min(axis=1)
    src=next(EP.parent.glob('35*/data/r24_source_exclusion_overlay.parquet'))
    g=pd.read_parquet(src)
    g=g[g.basis=='eps_cny_per_share'].dropna(subset=['broker','value']).copy()
    g['ts_code']=g.stock_code+np.where(g.stock_code.str.startswith('6'),'.SH','.SZ')
    g['year']=g.fiscal_year
    g=g.merge(times,on=group)
    g=g[(g.publication_proxy_date<g.earliest)&((g.earliest-g.publication_proxy_date).dt.days<=365)]
    g=g[g.publication_proxy_date==g.groupby(group+['broker']).publication_proxy_date.transform('max')]
    grp=g.groupby(group+['broker']).value.agg(['min','max'])
    cons=grp.loc[grp['min']==grp['max'],'min'].groupby(group).agg(['median','size'])
    all_=times.join(cons).reset_index()
    all_['error']=all_.eps-all_['median']
    all_=all_[all_['size'].ge(2)&all_.error.notna()].sort_values('formal').copy()
    scales=[]
    for sym,one in all_.groupby('ts_code'):
        scales.extend((j,one.loc[(one.formal<row.formal)&(one.year<row.year),'error'].tail(8).std(ddof=1)) for j,row in one.iterrows())
    all_['prior_sd']=pd.Series(dict(scales))
    all_['SUE']=all_.error/all_.prior_sd.where(all_.prior_sd>0)
    all_['first_formal']=(all_.formal==all_.earliest)&(all_.guidance.isna()|(all_.guidance>all_.formal))&(all_.express.isna()|(all_.express>all_.formal))
    all_['instrument']=all_.ts_code.str[-2:]+all_.ts_code.str[:6]
    all_['signal_idx']=m.days.searchsorted(all_.formal,side='right')
    all_.to_parquet(OUTDIR/'annual_events.parquet',index=False)
    signal=all_[all_.first_formal&all_.SUE.notna()&all_.signal_idx.lt(len(m.days)-21)].copy()
    j=m.symbols.get_indexer(signal.instrument)
    signal=signal[j>=0].copy();j=j[j>=0];e=signal.signal_idx.to_numpy()+1
    hist=industries(m.days[np.unique(e-1)])
    signal['industry']=[hist[m.days[i-1]].get(sym,'未知') for i,sym in zip(e,signal.instrument)]
    signal['member']=m.members[e-1,j]
    for h in [5,10,20]:signal['h'+str(h)]=m.o[e+h,j]/m.o[e,j]-1
    signal.to_csv(OUTDIR/'SUE_event_outcomes.csv',index=False)
    pairs=signal[signal.member].merge(signal[signal.member],on=['signal_idx','industry'])
    pairs=pairs[(pairs.instrument_x<pairs.instrument_y)&((pairs.size_x-pairs.size_y).abs()<=1)]
    # Compare on the signal date's CSI300 free-float size percentile. Use
    # prior published share-count snapshot and contemporaneous raw close.
    if not pairs.empty:
        raw_close=pd.read_parquet(PRIVATE/'close.parquet')
        folder=PRIVATE/'style_caps_20261117'
        files=sorted(folder.glob('[0-9]'*8+'.json'))
        dates=pd.DatetimeIndex([pd.Timestamp(p.stem) for p in files])
        paired=[]
        for i,z in pairs.groupby('signal_idx'):
            day=m.days[i]
            loc=dates.searchsorted(day)-1
            if loc<0:continue
            f=files[loc];data=json.loads(f.read_bytes())['data']
            raw=pd.DataFrame(data['items'],columns=data['fields'])
            raw.index=raw.ts_code.str[-2:]+raw.ts_code.str[:6]
            raw=raw[raw.free_share.gt(0)&raw.free_share.le(raw.float_share*1.0001)]
            cap=(raw.free_share*raw_close.loc[day]).reindex(m.symbols[m.members[i]]).rank(pct=True)
            z=z.assign(cap_rank_x=z.instrument_x.map(cap),cap_rank_y=z.instrument_y.map(cap),
                       share_source=dates[loc])
            z['size_matched']=(z.cap_rank_x-z.cap_rank_y).abs()<=.10
            paired.append(z)
        pairs=pd.concat(paired)
    pairs.to_csv(OUTDIR/'same_day_industry_events.csv',index=False)
    formal_signal={(m.days[i],name):v for i,name,v in signal[['signal_idx','instrument','SUE']].itertuples(index=False,name=None)}
    # First flash report's diluted EPS is kept distinct from formal basic EPS.
    # Fit the historical scale only to previous flash-versus-forecast errors.
    flash0=flash.merge(times[['express']],on=group)
    feps=flash0[flash0['first']==flash0.express].groupby(group).diluted_eps.agg(['min','max'])
    f=times.join(cons).join(feps['min'].where(feps['min']==feps['max']).rename('flash_eps')).reset_index()
    f=f[(f['size']>=2)&f.flash_eps.notna()].sort_values('express').copy()
    f['error']=f.flash_eps-f['median']
    ss=[]
    for sym,one in f.groupby('ts_code'):
        ss.extend((j,one.loc[(one.express<row.express)&(one.year<row.year),'error'].tail(8).std()) for j,row in one.iterrows())
    f['scale']=pd.Series(dict(ss));f['sue']=f.error/f.scale.where(f.scale>0)
    f['first_flash']=(f.express==f.earliest)&(f.guidance.isna()|(f.guidance>f.express))&(f.formal.isna()|(f.formal>f.express))
    f['instrument']=f.ts_code.str[-2:]+f.ts_code.str[:6];f['signal_idx']=m.days.searchsorted(f.express,side='right')
    f.to_parquet(OUTDIR/'flash_events.parquet',index=False)
    f=f[f.first_flash&f.sue.notna()&(f.signal_idx<len(m.days)-11)]
    flash_signal={(m.days[i],sym):v for i,sym,v in f[['signal_idx','instrument','sue']].itertuples(index=False,name=None)}
    return formal_signal,flash_signal

def hkscores(m):
    mapping=pd.read_csv(OUTDIR/'mapping.csv',dtype={'hk':str,'a':str})
    def prices(ticker,field):
        p=HERE/'raw'/(ticker+'.json.gz')
        if not p.exists():return pd.Series(dtype=float)
        d=json.loads(gzip.decompress(p.read_bytes()))['chart']['result'][0]
        tz=d['meta']['exchangeTimezoneName']
        dates=pd.to_datetime(d['timestamp'],unit='s',utc=True).tz_convert(tz).normalize().tz_localize(None)
        vals=d['indicators'][field][0]['adjclose' if field=='adjclose' else 'close']
        x=pd.Series(vals,index=dates,dtype=float)
        return x[~x.index.duplicated(keep='last')].sort_index().where(lambda s:s>0)
    fx=prices('HKDCNY=X','quote')
    assert len(fx)>0
    bench=prices('^HSI','adjclose')
    px=pd.DataFrame({r.instrument:prices(r.ticker,'adjclose') for r in mapping.itertuples()})
    px=px.dropna(axis=1,how='all')
    # Use strictly earlier shared calendar dates, selecting closes observed on both markets.
    ix=px.index.intersection(m.days).intersection(fx.index).intersection(bench.index).sort_values()
    hret=(px.loc[ix].mul(fx.loc[ix],axis=0)).pct_change(5,fill_method=None)
    c=pd.read_parquet(PRIVATE/'qfq_close.parquet').reindex(index=ix,columns=px.columns)
    aret=c.pct_change(5,fill_method=None)
    market=(bench.loc[ix]*fx.loc[ix]).pct_change(5,fill_method=None)
    hres=hret.sub(market,axis=0)
    hscore=hres-aret
    dates=[m.days[e-1] for e in BOOKS]
    hist=industries(dates)
    rows=[]
    for day in dates:
        j=ix.searchsorted(day)-1
        if j<5 or (day-ix[j]).days>7:continue
        z=pd.concat([hscore.iloc[j].rename('H_minus_A'),aret.iloc[j].rename('A5'),hres.iloc[j].rename('H_minus_market')],axis=1).dropna()
        sec=hist[day].reindex(z.index).fillna('未知')
        z['H_industry_resid']=z.H_minus_market-z.H_minus_market.groupby(sec).transform('median')
        rows.append(z.rename_axis('instrument').reset_index().assign(date=day,source_end=ix[j],source_start=ix[j-5],industry=sec.to_numpy()))
    data=pd.concat(rows)
    assert (data.source_end<data.date).all()
    data.to_parquet(OUTDIR/'AH_signals.parquet',index=False)
    return data

def evaluate(m,actions,plans,signals):
    output=[];support=[];ordrows=[];risk=[]
    labels={}
    for e,(ids,*_) in BOOKS.items():
        if e+10>=len(m.days):continue
        with np.errstate(invalid="ignore",divide="ignore"):
            y=m.o[e+10,ids]/m.o[e,ids]-1
        v=pd.Series(y,index=ids).dropna().sort_index().sort_values(kind="stable")
        labels[e]=pd.Series(np.floor(10*np.arange(len(v))/len(v)).astype(int)+1,index=v.index).to_dict()
    for exp,lookup in (signals|{k+"_covered_basket":v for k,v in signals.items() if k=="N4_H_minus_A"}).items():
        for rule in ['signal','covered_ridge']:
            chosen={}
            for e,(ids,r,pool,removed,adds,_) in BOOKS.items():
                day=m.days[e-1]
                ok=[j for j in pool if (day,m.symbols[j]) in lookup]
                byscore=sorted(ok,key=lambda j:(lookup[day,m.symbols[j]],m.symbols[j]),reverse=True)
                base=pool[:len(adds)]
                covered_slots=[j for j in base if j in ok]
                n=min(len(ok),len(adds)) if exp.endswith('_covered_basket') else len(covered_slots)
                picks=(byscore if rule=='signal' else ok)[:n]
                remaining=(list(pool[~np.isin(pool,picks)])[:len(adds)-n] if exp.endswith('_covered_basket')
                           else [j for j in base if j not in covered_slots])
                new=np.r_[picks,remaining].astype(int)
                chosen[e]=np.r_[plans['tree'][e][:-len(adds)],new]
                if rule=='signal':
                    counter_ids=np.r_[ok[:n],pool[~np.isin(pool,ok[:n])][:len(adds)-n]].astype(int) if exp.endswith('_covered_basket') else base
                    support.append(dict(test=exp,entry_idx=e,k=len(r),reserve=len(pool),covered=len(ok),covered_seats=n,
                        changed=len(set(new)-set(counter_ids)),date=day))
            for scope,beg,fin in SEGMENTS:
                lo,hi=m.days.get_indexer([beg,fin])
                def record(e,ph,plan,state,before,info):
                    _,_,buy,ticket,_=info
                    date=m.days[e-1]
                    adds=plan[-len(BOOKS[e][4]):]
                    for j in adds:
                        risk.append(dict(test=exp,rule=rule,scope=scope,entry_idx=e,instrument=m.symbols[j],
                            supported=(date,m.symbols[j]) in lookup,planned=ticket,bought=buy[j],
                            actual_value=state.units[ph,j]*np.nan_to_num(m.marks['flat'][0][e,j]),
                            realized_decile=labels[e].get(j)))
                daily,orders,_,_=funded(m,actions,chosen,lo,hi,arm=rule,books=BOOKS,observer=record)
                output.append(daily.assign(test=exp,rule=rule,scope=scope))
                ordrows.append(pd.DataFrame(orders,columns='idx sleeve instrument order fee'.split()).assign(test=exp,rule=rule,scope=scope))
    pd.DataFrame(risk).to_parquet(OUTDIR/'incoming_capital.parquet',index=False)
    d=pd.concat(output)
    d.to_parquet(OUTDIR/'daily.parquet',index=False)
    pd.DataFrame(support).to_parquet(OUTDIR/'coverage.parquet',index=False)
    pd.concat(ordrows).to_parquet(OUTDIR/'orders.parquet',index=False)
    mo=pd.concat([monthly(v).assign(test=exp,rule=rule,scope=scope) for (exp,rule,scope),v in d.groupby(['test','rule','scope'])])
    mo.to_csv(OUTDIR/'full_months.csv',index=False)
    rows=[]
    for (exp,scope),g in mo.groupby(['test','scope']):
        w=g.pivot(index='month',columns='rule',values=['net','gross','fee'])
        gap=w.net.signal-w.net.covered_ridge
        rows.append(dict(test=exp,scope=scope,n=len(w),gap_bp=gap.mean()*1e4,net_ex3=gap.drop(gap.nlargest(3).index).mean()*1e4,
                gross_bp=(w.gross.signal-w.gross.covered_ridge).mean()*1e4,fee_bp=(w.fee.signal-w.fee.covered_ridge).mean()*1e4))
    pd.DataFrame(rows).to_csv(OUTDIR/'comparisons.csv',index=False)
if __name__=='__main__':
    m,acts=market();plans,BOOKS=targets(m)
    sue,flash_proxy=events(m)
    ah=hkscores(m).set_index(['date','instrument'])
    signals={'N3_formal_SUE':sue,'N3_flash_diluted_EPS_proxy':flash_proxy}
    for key in ['H_minus_A','A5','H_minus_market','H_industry_resid']:signals['N4_'+key]=ah[key].dropna().to_dict()
    evaluate(m,acts,plans,signals)
