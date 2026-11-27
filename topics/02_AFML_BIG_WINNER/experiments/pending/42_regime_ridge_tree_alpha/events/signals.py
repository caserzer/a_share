from disclosures import *
def main():
    prices=pd.read_parquet(engine.LOCAL/'close.parquet');days=prices.index
    qfq=pd.read_parquet(engine.LOCAL/'qfq_close.parquet').reindex_like(prices)
    factor=qfq.div(prices)
    eps=pd.read_parquet(EP41/'sources/n2/eps_events.parquet').rename(columns={'publication_proxy_date':'dt'})
    eps['i']=days.searchsorted(eps.dt,side='right')
    archive=pd.read_parquet(next(BASE.glob('35_*/data/r11_analyst_forecasts.parquet')))
    archive=archive[archive.basis=='eps_cny_per_share'].copy();archive['instrument']=unit(archive.stock_code)
    archive['i']=days.searchsorted(archive.publication_proxy_date,side='right')
    archive=archive[['instrument','broker','fiscal_year','i']].drop_duplicates()
    data=pd.concat([pd.read_parquet(f) for f in sorted((EP24/'local_cache/r18_reports').glob('*.parquet'))],ignore_index=True)
    k=['instrument','broker','dt'];data=data.rename(columns={'orgCode':'broker','publishDate':'dt'})
    data['instrument']=unit(data.stockCode); data['dt']=pd.to_datetime(data.dt).dt.normalize()
    lo=pd.to_numeric(data.indvAimPriceL,errors='coerce');hi=pd.to_numeric(data.indvAimPriceT,errors='coerce')
    data['price']=pd.concat([lo.where(lo>0),hi.where(hi>0)],axis=1).mean(axis=1)
    data=data[data.price.notna()&data.instrument.isin(prices.columns)].copy()
    amb=data.title.fillna('').str.contains(r'港元|港币|美元|H股|港股|目标市值',case=False)
    receipt={'target_rows':len(data),'ambiguous_currency_or_basis_title_excluded':int(amb.sum())}
    data=data[~amb].copy()
    conflict=data.groupby(k).price.transform('nunique')>1;receipt['same_day_conflict_rows']=int(conflict.sum())
    data=data[~conflict].sort_values(k+['infoCode']).drop_duplicates(k)
    idx=days.searchsorted(data.dt,side='right')-1
    data['factor']=factor.to_numpy()[np.maximum(idx,0),prices.columns.get_indexer(data.instrument)]
    data.loc[idx<0,'factor']=np.nan
    gb=data.groupby(k[:2]);den=gb.price.shift(); f=gb.factor.shift()
    unitok=(data.factor/f-1).abs()<1e-6
    receipt['factor_changed_or_missing_among_prior']=int((den.notna()&~unitok).sum())
    data['target']=(data.price/den-1).where(unitok)
    data['i']=days.searchsorted(data.dt,side='right')
    data=data[data.target.notna()]
    (OUT/'target_source_receipt.json').write_text(json.dumps(receipt,indent=2))
    data[['instrument','broker','dt','i','price','target','factor','infoCode']].to_parquet(OUT/'target_revisions.parquet',index=False)
    sue=pd.read_parquet(OUT/'all_sue_events.parquet')
    # Prefer first parent-profit on the same event, then first basic EPS, finally flash proxy separately.
    sue=sue[sue['first'] & ~sue.kind.eq('flash_eps_proxy')].copy()
    sue['priority']=sue.kind.map({'formal':0,'guidance':1,'formal_eps':2})
    sue=sue.sort_values(['ann_date','priority']).drop_duplicates(['instrument','end_date','ann_date'])
    sue['i']=days.searchsorted(sue.ann_date,side='right')
    frames=[]
    for i,dt in enumerate(days):
        if dt<'2018-01-01' if isinstance(dt,str) else dt<pd.Timestamp('2018-01-01'):continue
        y=dt.year;val={}
        if dt<=archive_date:
            x=eps[(eps.fiscal_year==y)&(eps.i<=i)&(eps.i>i-180)].sort_values(['i','dt']).drop_duplicates(['instrument','broker'],keep='last')
            z=x[x.i>i-20]
            val['eps20']=z.groupby('instrument').move.mean()
            x=x.assign(weight=np.exp2(-(i-x.i)/60));val['eps60']=(x.move*x.weight).groupby(x.instrument).sum()/x.groupby('instrument').weight.sum()
            w=archive[(archive.fiscal_year==y)&(archive.i<=i)&(archive.i>i-120)]
            now=w[w.i>i-60].groupby('instrument').broker.nunique();old=w[w.i<=i-60].groupby('instrument').broker.nunique()
            if i>=120 and days[i-119]>=pd.Timestamp('2020-03-09'):
                keys=now.index.union(old.index);val['coverage_current']=now.reindex(keys,fill_value=0)
                val['coverage_delta']=val['coverage_current']-old.reindex(keys,fill_value=0)
        z=data[(data.i<=i)&(data.i>i-20)].sort_values(['i','dt']).drop_duplicates(['instrument','broker'],keep='last')
        val['target20']=z.groupby('instrument').target.median()
        z=sue[(sue.i<=i)&(sue.i>i-20)].sort_values(['i','ann_date']).drop_duplicates('instrument',keep='last')
        val['sue20']=z.set_index('instrument').sue
        frame=pd.DataFrame(val);frame.index.name='instrument';frames.append(frame.reset_index().assign(signal_date=dt))
    out=pd.concat(frames,ignore_index=True)
    out.to_parquet(OUT/'source_daily_signals.parquet',index=False,compression='zstd')
    print(out.count(),flush=True)
if __name__=='__main__':
    import json
    archive_date=pd.read_parquet(next(BASE.glob('35_*/data/r11_analyst_forecasts.parquet')),columns=['publication_proxy_date']).publication_proxy_date.max()
    main()
