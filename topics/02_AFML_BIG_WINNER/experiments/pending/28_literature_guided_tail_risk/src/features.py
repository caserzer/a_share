"""Past-only literature mechanisms and separate future shape labels; never fit predictors."""
from core import *


def hill(values, quantile=.05, minimum=100):
    v=np.asarray(values,float).ravel();v=v[np.isfinite(v)&(v>-1)]
    if not len(v):return np.nan,np.nan,0
    u=float(np.quantile(v,quantile));tail=v[v<u]
    if u>=0 or len(tail)<minimum:return np.nan,u,len(tail)
    return float(np.log(tail/u).mean()),u,len(tail)


def shape(values,maximum_missing=5):
    v=np.asarray(values,float);v=v[np.isfinite(v)]
    if len(values)-len(v)>maximum_missing or len(v)<20:return np.nan,np.nan
    x=v-v.mean();n=len(x);s2=np.sum(x*x)
    if s2<=1e-20:return np.nan,np.nan
    nc=-n*np.sqrt(n-1)*np.sum(x**3)/((n-2)*s2**1.5)
    down=x[x<0];up=x[x>0]
    du=np.log((len(up)-1)*np.sum(down**2)/((len(down)-1)*np.sum(up**2))) if min(len(down),len(up))>1 and min(np.sum(down**2),np.sum(up**2))>0 else np.nan
    return float(nc),float(du)


def risk_structure(stock,market,industry,minimum=50):
    x=np.column_stack([stock,market,industry]);x=x[np.isfinite(x).all(axis=1)]
    if len(x)<minimum:return np.full(5,np.nan)
    y,m,i=x.T;A=np.column_stack([np.ones(len(x)),m])
    bm=np.linalg.lstsq(A,y,rcond=None)[0];em=y-A@bm
    bi=np.linalg.lstsq(A,i,rcond=None)[0];orth=i-A@bi
    Z=np.column_stack([A,orth])
    if np.linalg.matrix_rank(Z)<3:return np.full(5,np.nan)
    b=np.linalg.lstsq(Z,y,rcond=None)[0];e=y-Z@b;sst=np.sum((y-y.mean())**2)
    if sst<=1e-20:return np.full(5,np.nan)
    return np.array([b[1],b[2],np.sqrt(np.sum(e*e)/(len(e)-3)*252),np.sum(e*e)/sst,
                     (np.sum(em*em)-np.sum(e*e))/sst])


def tail_loading(return_values,tail_values,minimum=36):
    y=np.asarray(return_values,float);x=np.asarray(tail_values,float)
    valid=np.isfinite(x)&np.isfinite(y);x=x[valid];y=y[valid]
    if len(y)<minimum or np.var(x)<1e-15:return np.nan
    return float(np.linalg.lstsq(np.column_stack([np.ones(len(x)),x]),y,rcond=None)[0][1])


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--verify-cutoff');args=parser.parse_args()
    if not args.verify_cutoff:assert not (EP/'outputs/manifests/preregistration.json').exists()
    gate=json.loads((EP/'outputs/audits/data_gate.json').read_text())
    assert gate['D0_labels_unchanged']
    panel=pd.read_parquet(CACHE/'d0_panel.parquet')
    axes=json.loads((CACHE/'daily_axes.json').read_text());calendar=pd.DatetimeIndex(axes['dates']);stocks=axes['instruments'];lookup={s:j for j,s in enumerate(stocks)}
    z=np.load(CACHE/'daily_prices.npz');close=z['close'];turn=z['turnover']
    if args.verify_cutoff:
        mask=calendar<=pd.Timestamp(args.verify_cutoff)
        calendar=calendar[mask];close=close[mask];turn=turn[mask]
        panel=panel[panel.date<=pd.Timestamp(args.verify_cutoff)].copy()
    returns=np.full_like(close,np.nan);returns[1:]=close[1:]/close[:-1]-1
    returns[(returns<=-1)|~np.isfinite(returns)]=np.nan
    benchmark_path=TOPIC/'data/processed/index/benchmark_indices_daily.csv'
    bench=pd.read_csv(benchmark_path,parse_dates=['date']);b=bench[bench.index_alias.eq('csi300')].set_index('date').close.reindex(calendar)
    market=b.pct_change(fill_method=None).to_numpy();logmarket=np.log1p(market)
    monthly_index=pd.DatetimeIndex(pd.Series(calendar).groupby(calendar.to_period('M')).max())
    mi=calendar.get_indexer(monthly_index);months=calendar.to_period('M')
    mclose=close[mi];monthly_returns=np.full_like(mclose,np.nan);monthly_returns[1:]=mclose[1:]/mclose[:-1]-1
    tail=[];mturn=[]
    for date in monthly_index:
        mask=months==date.to_period('M');v,u,n=hill(returns[mask],C['features']['tail_quantile'],C['features']['minimum_tail_exceedances'])
        tail.append(dict(date=date,tail_hill=v,tail_threshold=u,exceedances=n,valid_observations=int(np.isfinite(returns[mask]).sum())))
        t=turn[mask];valid=np.isfinite(t).sum(axis=0);s=np.nansum(t,axis=0);s[valid<len(t)*C['features']['turnover_min_daily_coverage']]=np.nan;mturn.append(s)
    tails=pd.DataFrame(tail);tails['tail_change']=tails.tail_hill.diff();tails['market_month_return']=b.reindex(monthly_index).pct_change(fill_method=None).to_numpy()
    if not args.verify_cutoff:tails.to_csv(OUT/'tail_history.csv',index=False)
    mturn=np.array(mturn);tl=tails.tail_hill.to_numpy();lagtail=np.r_[np.nan,tl[:-1]]
    releases=json.loads((EP24/'outputs/local_cache/r32_industry/parse_manifest.json').read_text())
    for item in releases:
        assert digest(item['table_path'])==item['table_sha256'] and digest(item['pdf_path'])==item['pdf_sha256']
    definitions=C['tail_features']+C['structure_features']+C['disagreement_features']
    for col in definitions:panel[col]=np.nan
    panel['feature_cutoff']=panel.date
    panel['future_ncskew6']=np.nan;panel['future_duvol6']=np.nan
    for num,(date,g) in enumerate(panel.groupby('date',sort=True)):
        d=calendar.get_loc(date);m=monthly_index.get_loc(date);ids=np.array([lookup[s] for s in g.instrument]);ix=g.index
        panel.loc[ix,'tail_hill']=tl[m];panel.loc[ix,'tail_change']=tails.tail_change.iloc[m]
        window=slice(max(0,m+1-C['features']['tail_beta_window_months']),m+1)
        for row,j in zip(ix,ids):
            beta=tail_loading(monthly_returns[window,j],lagtail[window],C['features']['tail_beta_min_months'])
            panel.loc[row,'tail_beta']=beta;panel.loc[row,'tail_beta_x_level']=beta*tl[m]
        six=(calendar>date-pd.DateOffset(months=6))&(calendar<=date)
        twelve=(calendar>date-pd.DateOffset(months=12))&(calendar<=date)
        # Fixed non-overlapping 6-month vs previous 18-month turnover proxy; no original-formula claim.
        if m>=23:
            current=mturn[m-5:m+1];prior=mturn[m-23:m-5]
            enough=np.isfinite(current).all(axis=0)&np.isfinite(prior).all(axis=0)
            dt=np.mean(current,axis=0)-np.mean(prior,axis=0);dt[~enough]=np.nan
            panel.loc[ix,'dturn6_18']=dt[ids]
        for row,j in zip(ix,ids):
            logret=np.log1p(returns[:,j])
            nc,du=shape(logret[six]-logmarket[six]);panel.loc[row,['past_ncskew6','past_duvol6']]=[nc,du]
            for mask,name in [(six,'past_excess6'),(twelve,'past_excess12')]:
                a=logret[mask]-logmarket[mask]
                if np.isfinite(a).sum()>=len(a)-5:panel.loc[row,name]=float(np.nansum(a))
            end=panel.loc[row,'end_6']
            if pd.notna(end):
                future=(calendar>date)&(calendar<=end);nc,du=shape(logret[future]-logmarket[future])
                panel.loc[row,['future_ncskew6','future_duvol6']]=[nc,du]
        available=[r for r in releases if pd.Timestamp(r['published'])<date]
        industry=np.full(len(stocks),'UNKNOWN',dtype=object)
        if available:
            item=max(available,key=lambda r:r['published']);table=pd.read_parquet(item['table_path']).set_index('code');table.index=table.index.astype(str).str.zfill(6)
            ids_=pd.Series([s[2:] for s in stocks]).map(table.major);valid=ids_.fillna('').str.fullmatch('[A-S][0-9]{2}')
            era='legacy' if pd.Timestamp(item['published']).year<=2021 else 'revised'
            industry[valid]=era+':'+ids_[valid]
        hist=returns[max(0,d-62):d+1];mk=market[max(0,d-62):d+1]
        current_valid=np.isfinite(close[d])
        for sector in np.unique(industry):
            if sector=='UNKNOWN':continue
            members=np.flatnonzero((industry==sector)&current_valid);own=[(row,j) for row,j in zip(ix,ids) if industry[j]==sector]
            if not own:continue
            peer=hist[:,members];sums=np.nansum(peer,axis=1);counts=np.isfinite(peer).sum(axis=1)
            for row,j in own:
                ownret=hist[:,j];count=counts-np.isfinite(ownret)
                mean=np.divide(sums-np.nan_to_num(ownret),count,out=np.full(len(hist),np.nan),where=count>=C['features']['minimum_industry_peers'])
                panel.loc[row,C['structure_features']]=risk_structure(ownret,mk,mean,C['features']['structure_min_sessions'])
        if num%12==0:print(f'feature month {num}/100 {date.date()}',flush=True)
    assert panel[definitions].replace([np.inf,-np.inf],np.nan).equals(panel[definitions])
    if args.verify_cutoff:
        original=pd.read_parquet(CACHE/'panel.parquet')
        original=original[original.date<=pd.Timestamp(args.verify_cutoff)]
        pd.testing.assert_frame_equal(panel[definitions],original[definitions],check_exact=True)
        write_json(EP/'outputs/audits/pit_truncation.json',dict(passed=True,cutoff=args.verify_cutoff,
            rows=len(panel),features=definitions,comparison='all past features bit-identical after removing all later daily quotes and index observations'))
        print('PIT truncation verification passed',flush=True);return
    original=pd.read_parquet(CACHE/'d0_panel.parquet')
    pd.testing.assert_frame_equal(panel[original.columns],original)
    panel.to_parquet(CACHE/'panel.parquet',index=False)
    coverage=[]
    for scope,g in [('all_train_and_test',panel),('test',panel[panel.date>='2021-01-01'])]:
        for name in definitions+['future_ncskew6','future_duvol6']:
            coverage.append(dict(scope=scope,feature=name,rows=len(g),known=int(g[name].notna().sum()),fraction=float(g[name].notna().mean())))
    pd.DataFrame(coverage).to_csv(EP/'outputs/audits/feature_coverage.csv',index=False)
    write_json(EP/'outputs/audits/feature_gate.json',dict(passed=True,rows=len(panel),prior_columns_unchanged=True,feature_cutoff_lte_origin=True,
        source_price_vintages='retrospective proxies; raw recovery receipts separate',new_panel_sha256=digest(CACHE/'panel.parquet'),
        index_source_sha256=digest(benchmark_path),no_model_scored=True,labels_separate_from_features=True))
    print(pd.DataFrame(coverage).query("scope=='test'").to_string(index=False),flush=True)


if __name__=='__main__':main()
