"""P0: immutable prior research, source-date industry and two separate population audits."""
from core import *


def st_marker(value):
    return 'ST' in str(value).upper().replace('＊','*').replace('Ｓ','S').replace('Ｔ','T')


def sh_history_flag(path):
    if not path.exists():return False,'missing_history'
    try:f=pd.read_csv(path,dtype=str)
    except pd.errors.EmptyDataError:return False,'empty_history'
    cols=[c for c in ['name','名称','证券简称','变更前简称','变更后简称'] if c in f.columns]
    return any(f[c].map(st_marker).any() for c in cols),'cached_history' if cols else 'no_recorded_history'


def total_return_sensitivity(rawpanel,calendar):
    folder=EP24/'outputs/local_cache/corporate_actions'
    actions=pd.read_parquet(folder/'RPT_SHAREBONUS_DET_all.parquet');rights=pd.read_parquet(folder/'RPT_IPO_ALLOTMENT_all.parquet')
    actions['event_date']=pd.to_datetime(actions.EX_DIVIDEND_DATE);actions['NOTICE_DATE']=pd.to_datetime(actions.NOTICE_DATE)
    actions=actions.sort_values('NOTICE_DATE').drop_duplicates(['SECURITY_CODE','event_date','REPORT_DATE'],keep='last')
    actions.SECURITY_CODE=actions.SECURITY_CODE.astype(str).str.zfill(6);rights.SECURITY_CODE=rights.SECURITY_CODE.astype(str).str.zfill(6)
    rights['begin']=pd.to_datetime(rights.EQUITY_RECORD_DATE).fillna(pd.to_datetime(rights.EX_DIVIDEND_DATE));rights['finish']=pd.to_datetime(rights.LISTING_DATE).fillna(pd.to_datetime(rights.EX_DIVIDEND_DATE))
    unexplained=pd.read_csv(EP24/'outputs/r09_total_return_sensitivity/unexplained_factor_events.csv',parse_dates=['date'])
    rows=[];receipts=[]
    for stock,g in rawpanel.groupby('instrument'):
        path=TOPIC/f'data/raw/akshare/day/raw/{stock}.csv';receipts.append(path)
        raw=pd.read_csv(path,parse_dates=['date']).set_index('date').reindex(calendar);close=raw.close.where(raw.close>0)
        a=actions[actions.SECURITY_CODE.eq(stock[2:])].copy();a['cash']=pd.to_numeric(a.PRETAX_BONUS_RMB,errors='coerce')/10;a['shares']=pd.to_numeric(a.BONUS_IT_RATIO,errors='coerce')/10
        cash=a.groupby('event_date').cash.sum(min_count=1).reindex(calendar).fillna(0);shares=a.groupby('event_date').shares.sum(min_count=1).reindex(calendar).fillna(0)
        bad=a.loc[(a.cash.isna()&a.shares.isna())|(a.cash<0)|(a.shares<0),'event_date'].tolist()
        bad += [d for d in a.event_date if d not in calendar or pd.isna(close.get(d))]
        bad += unexplained.loc[unexplained.instrument.eq(stock),'date'].tolist()
        gross=(close*(1+shares)+cash)/close.ffill().shift(1);gross.iloc[0]=1.;tr=gross.fillna(1.).cumprod()
        r=rights[rights.SECURITY_CODE.eq(stock[2:])]
        for row in g.itertuples():
            status='ok';value=np.nan;end=row.end_6
            if pd.isna(end):status='immature'
            elif pd.isna(close.get(row.date)) or pd.isna(close.get(end)):status='missing_start_or_end'
            elif ((r.begin<=end)&(r.finish>row.date)).any():status='rights_interval'
            elif any(row.date<d<=end for d in bad):status='unsupported_or_unexplained_action'
            else:value=float(tr.loc[end]/tr.loc[row.date]-1)
            rows.append(dict(date=row.date,instrument=stock,label_end=end,qfq_return=row.y_6,reinvested_return=value,status=status))
    return pd.DataFrame(rows),receipts


def coverage_census(rawpanel,calendar):
    root=TOPIC/'data/raw/akshare/status';metadata=pd.read_csv(root/'instrument_metadata_target_universe.csv',parse_dates=['listing_date','delist_date'])
    metadata['code']=metadata.code.astype(str).str.zfill(6);dates=pd.DatetimeIndex(sorted(rawpanel.date.unique()))
    target=pd.DatetimeIndex([d+pd.DateOffset(months=6) for d in dates]);idx=calendar.searchsorted(target)
    ends=np.full(len(dates),np.datetime64('NaT'),dtype='datetime64[ns]');ok=idx<len(calendar);ends[ok]=calendar[idx[ok]].to_numpy()
    rawkeys=set(zip(rawpanel.date,rawpanel.instrument));rows=[];stockaudit=[];source=[]
    for row in metadata.itertuples():
        listed=(dates>=row.listing_date)&((dates<row.delist_date) if pd.notna(row.delist_date) else True)
        if not listed.any():continue
        path=TOPIC/f'data/raw/akshare/day/qfq/{row.instrument}.csv'
        flag=False;history='not_SH'
        if row.exchange=='SH':
            hp=root/f'sh_name_history/{row.instrument}.csv';flag,history=sh_history_flag(hp)
            if hp.exists():source.append(hp)
        if not path.exists():
            stockaudit.append(dict(instrument=row.instrument,exchange=row.exchange,is_delisted=bool(row.is_delisted),sh_lifetime_st=flag,history_status=history,source='missing_price_file',listed_origin_months=int(listed.sum()),quoted_origins=0,in_fixed_pool=bool(rawpanel.instrument.eq(row.instrument).any())));continue
        bars=pd.read_csv(path,usecols=['date','close','turnover_rate'],parse_dates=['date']).set_index('date');close=bars.close.where(bars.close>0);source.append(path)
        assert not close.index.duplicated().any();start=close.reindex(dates).to_numpy();finish=close.reindex(pd.DatetimeIndex(ends)).to_numpy();y=finish/start-1
        origin_idx=calendar.get_indexer(dates);mom={}
        for h in [63,126]:
            before=np.full(len(dates),np.nan);valid=origin_idx>=h
            before[valid]=close.reindex(calendar[origin_idx[valid]-h]).to_numpy();mom[h]=start/before-1
        turnover=bars.turnover_rate.reindex(calendar).rolling(21,min_periods=21).mean().reindex(dates).to_numpy()
        usable=listed&np.isfinite(start)&(start>0);stockaudit.append(dict(instrument=row.instrument,exchange=row.exchange,is_delisted=bool(row.is_delisted),sh_lifetime_st=flag,history_status=history,source='cached_price',listed_origin_months=int(listed.sum()),quoted_origins=int(usable.sum()),in_fixed_pool=bool(rawpanel.instrument.eq(row.instrument).any())))
        for k in np.flatnonzero(usable):rows.append(dict(date=dates[k],instrument=row.instrument,label_end=ends[k],actual=float(y[k]) if np.isfinite(y[k]) else np.nan,is_delisted=bool(row.is_delisted),exchange=row.exchange,sh_lifetime_st=flag,in_fixed_pool=(dates[k],row.instrument) in rawkeys,
            mom63=mom[63][k],mom126=mom[126][k],turnover21=turnover[k]))
    return pd.DataFrame(rows),pd.DataFrame(stockaudit),source


def main():
    CACHE.mkdir(parents=True,exist_ok=True)
    protected=[]
    for root in [EP24,EP25,EP26]:
        protected += [p for p in root.rglob('*') if p.is_file() and not any(s in p.parts for s in ['local_cache','__pycache__','.pytest_cache']) and p.suffix in {'.py','.md','.json','.csv','.txt','.png'}]
    write_json(OUT/'prior_preservation.json',{str(p.relative_to(EP.parent)):digest(p) for p in sorted(protected)})
    panel,releases=prepare_panel()
    raw=pd.read_parquet(EP24/'outputs/local_cache/four_horizon_panel.parquet');calendar_path=TOPIC/'data/qlib/cn_data_pit_largecap/calendars/day.txt'
    calendar=pd.DatetimeIndex(pd.to_datetime(pd.read_csv(calendar_path,header=None)[0]));source=[calendar_path,EP24/'outputs/local_cache/four_horizon_panel.parquet',EP26/'config.json',EP26/'outputs/data_audit.json',EP26/'outputs/controls.json',EP24/'src/build_historical_industry.py',EP24/'src/check_total_returns.py']
    index_path=TOPIC/'data/processed/index/benchmark_indices_daily.csv';source.append(index_path)
    benchmark=pd.read_csv(index_path,parse_dates=['date']);benchmark=benchmark[benchmark.index_alias.eq('csi300')].set_index('date').sort_index().close.reindex(calendar)
    market_mom=benchmark/benchmark.shift(126)-1;market_vol=benchmark.pct_change(fill_method=None).rolling(63).std()*np.sqrt(252)
    np.testing.assert_allclose(panel.market_mom126,market_mom.reindex(panel.date),rtol=0,atol=1e-12,equal_nan=True)
    np.testing.assert_allclose(panel.market_vol63,market_vol.reindex(panel.date),rtol=0,atol=1e-12,equal_nan=True)
    for stock,g in raw.groupby('instrument'):
        path=TOPIC/f'data/raw/akshare/day/qfq/{stock}.csv';source.append(path)
        close=pd.read_csv(path,usecols=['date','close'],parse_dates=['date']).set_index('date').close
        for h in C['horizons']:
            end=g[f'end_{h}'];observed=close.reindex(pd.DatetimeIndex(end)).to_numpy()/close.reindex(g.date).to_numpy()-1
            np.testing.assert_allclose(observed,g[f'y_{h}'],rtol=0,atol=1e-12,equal_nan=True)
        # Date end convention is independently checked against the actual market calendar.
        targets=pd.DatetimeIndex([d+pd.DateOffset(months=6) for d in g.date]);idx=calendar.searchsorted(targets);ends=np.full(len(g),np.datetime64('NaT'),dtype='datetime64[ns]');ok=idx<len(calendar);ends[ok]=calendar[idx[ok]]
        np.testing.assert_array_equal(g.end_6.isna(),pd.isna(ends));np.testing.assert_array_equal(g.end_6.dropna(),ends[~pd.isna(ends)])
    known=panel.financial_available_date.notna();assert (panel.loc[known,'financial_available_date']<panel.loc[known,'date']).all();assert (panel.yield_observation_date<panel.date).all()
    ind=panel.industry_id.ne('UNKNOWN');assert (panel.loc[ind,'industry_published']<panel.loc[ind,'date']).all()
    for r in releases:source.extend([Path(r['pdf_path']),Path(r['table_path'])])
    tr,paths=total_return_sensitivity(raw,calendar);source+=paths;tr.to_parquet(CACHE/'label_sensitivity.parquet',index=False)
    statusroot=TOPIC/'data/raw/akshare/status'
    source += [statusroot/f for f in ['instrument_metadata_target_universe.csv','stock_info_sz_change_name_short.csv','stock_info_sh_delist_all.csv','stock_info_sz_delist_all.csv']]
    census,stocks,paths=coverage_census(raw,calendar);source+=paths;census.to_parquet(CACHE/'listing_quote_census.parquet',index=False);stocks.to_csv(OUT/'listing_st_delisting_audit.csv',index=False)
    # No future ST flag, delisted flag, future outcome or fixed-pool membership enters state aggregation.
    snapshots=rebuild_industry(census[['date','instrument','mom63','mom126','turnover21']],releases)
    snapshots.to_parquet(CACHE/'asof_peer_snapshot.parquet',index=False)
    indcols=['industry_id','industry_sector','industry_age_days','industry_stale','industry_published','industry_peer_count','industry_mom63','industry_mom126','industry_breadth63']
    panel=panel.drop(columns=indcols).merge(snapshots[['date','instrument']+indcols],on=['date','instrument'],how='left',validate='one_to_one')
    panel['industry_id']=panel.industry_id.fillna('UNKNOWN');panel['industry_sector']=panel.industry_sector.fillna('UNKNOWN');panel['industry_stale']=panel.industry_stale.fillna(1.)
    market=snapshots.groupby('date').agg(state_turnover=('turnover21','mean'),state_breadth63=('mom63',lambda x:x.dropna().gt(0).mean()),breadth_support=('mom63','count'),quote_members=('instrument','size'))
    panel=panel.drop(columns=['state_turnover','state_breadth63']).merge(market[['state_turnover','state_breadth63']],left_on='date',right_index=True,how='left',validate='many_to_one')
    panel=panel.sort_values(['date','instrument']).reset_index(drop=True);panel.to_parquet(PANEL,index=False);market.to_csv(OUT/'market_state_coverage.csv')
    census['event']=(census.actual<-.2).astype(float);census.loc[census.actual.isna(),'event']=np.nan
    out=[]
    for dimension in ['all','exchange','sh_lifetime_st','is_delisted','in_fixed_pool']:
        z=census[census.date>=C['prediction_start']].copy();z['group']='all' if dimension=='all' else z[dimension].astype(str)
        for (date,group),g in z.groupby(['date','group']):
            mature=g.label_end.notna();obs=mature&g.actual.notna();n=int(mature.sum());events=int((g.loc[obs,'actual']<-.2).sum());miss=int((mature&~obs).sum())
            out.append(dict(population='listing_quote_census_not_certified_PIT',dimension=dimension,group=group,date=date,predicted=len(g),mature=n,known=int(obs.sum()),events=events,missing=miss,event_rate_lower=events/n if n else np.nan,event_rate_upper=(events+miss)/n if n else np.nan))
    pd.DataFrame(out).to_csv(OUT/'census_coverage_by_month.csv',index=False)
    evalpanel=panel[panel.date>=C['prediction_start']];cov=[]
    for h in C['horizons']:
        for date,g in evalpanel.groupby('date'):
            mature=g[f'end_{h}'].notna();obs=mature&g[f'y_{h}'].notna();events=int((g.loc[obs,f'y_{h}']<-.2).sum());n=int(mature.sum());miss=int((mature&~obs).sum())
            cov.append(dict(population='EP26_fixed',horizon=h,date=date,predicted=len(g),mature=n,known=int(obs.sum()),events=events,missing=miss,event_rate_lower=events/n if n else np.nan,event_rate_upper=(events+miss)/n if n else np.nan))
    pd.DataFrame(cov).to_csv(OUT/'fixed_population_coverage.csv',index=False)
    industry=evalpanel.groupby('date').agg(rows=('date','size'),known=('industry_id',lambda x:x.ne('UNKNOWN').sum()),published=('industry_published','first'),stale=('industry_stale','mean'),state_known=('industry_mom63',lambda x:x.notna().mean()))
    industry.to_csv(OUT/'industry_coverage.csv')
    age=evalpanel.assign(valuation_observation_age_days=0).groupby('age_group').agg(rows=('date','size'),financial_age_median=('financial_age_days','median'),financial_age_min=('financial_age_days','min'),financial_age_max=('financial_age_days','max'),months=('date','nunique'))
    age.to_csv(OUT/'information_age.csv')
    same=evalpanel[['date','instrument','y_6']].merge(tr,on=['date','instrument'],validate='one_to_one');valid=same[same.status.eq('ok')&same.y_6.notna()]
    write_json(OUT/'label_sensitivity_audit.json',dict(main_labels_unchanged=True,valid_same_sample_rows=len(valid),main_event_rate=float((valid.y_6<-.2).mean()),reinvested_proxy_event_rate=float((valid.reinvested_return<-.2).mean()),event_disagreements=int(((valid.y_6<-.2)!=(valid.reinvested_return<-.2)).sum()),
        complete_total_return_repair=False,scope='calendar close-to-close ordinary cash/split reinvestment proxy; rights, unknown, unpriced and unexplained events excluded; all models later rescored same valid subset'))
    pd.Series(same.status.value_counts(),name='rows').to_csv(OUT/'label_sensitivity_coverage.csv')
    source += [EP24/'outputs/local_cache/corporate_actions/RPT_SHAREBONUS_DET_all.parquet',EP24/'outputs/local_cache/corporate_actions/RPT_IPO_ALLOTMENT_all.parquet',EP24/'outputs/r09_total_return_sensitivity/unexplained_factor_events.csv']
    source=sorted(set(source));pd.DataFrame([dict(path=str(p.relative_to(TOPIC)),sha256=digest(p),bytes=p.stat().st_size) for p in source]).to_csv(OUT/'source_receipts.csv',index=False)
    audit=dict(phase='P0',pass_for_limited_exploration=True,independent_confirmation_permitted=False,raw_labels_all_horizons_recomputed=True,fixed_rows=len(panel),prediction_rows=len(evalpanel),known_6m=int(evalpanel.y_6.notna().sum()),
        historical_releases=len(releases),industry_known_fraction=float(evalpanel.industry_id.ne('UNKNOWN').mean()),industry_stale_fraction=float(evalpanel.industry_stale.mean()),
        industry_same_asof_rule=True,current_classification_backfill=False,full_unbiased_PIT_universe_available=False,source_files=len(source),prior_preserved_files=len(protected),
        census_stocks=len(stocks),census_missing_price_stocks=int(stocks.source.eq('missing_price_file').sum()),census_delisted_stocks=int(stocks.is_delisted.sum()),
        sh_lifetime_ST_flagged_stocks=int(stocks.sh_lifetime_st.sum()),remaining_limits=['future Shanghai lifetime ST filtering','delisted and suspended quote/settlement missing','published historical industry documents not archived original byte certification; 2021-2023 stale gap','financial max(notice,update) not original vintage; median 456 days','historical valuation date age=0 is observation date only, not vintage certification','qfq proxy not complete total return','all prior historical periods selected and reused'],
        gate='Observed proxy labels reproducible; published-before-date industry and past-only market fields allow conditional diagnostics in fixed legacy population. No causal, full-market or independent probability confirmation. Census and SZ30 sensitivity kept separate.')
    audit['market_industry_state_population']='listing-date and contemporaneous positive quote coverage; no lifetime-ST filtering and no future outcomes in construction'
    audit['market_trend_volatility_independently_recomputed']=True
    write_json(OUT/'p0_audit.json',audit);print(audit,flush=True)

if __name__=='__main__':main()
