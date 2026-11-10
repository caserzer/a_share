"""Causal multi-scale turnover/volume and explicitly limited vendor PE audit."""
import warnings
from common34 import *


def run():
    freeze()
    identity=json.loads((EXT/'v4_adaptive_6_18_months/outputs/audits/inputs.json').read_text())
    release=Path(identity['price_release'])
    oldaudit=json.loads((EXT/'v5_rdagent_onset_forecast/outputs/daily_input_audit.json').read_text())
    assignment_path=OLD.parent/'extension_v2/products/assignments.parquet'
    members=pd.read_parquet(assignment_path)
    # Use only historical identity/membership, never next_return or entry outcomes.
    members=members[['era','level','industry_code','industry_name','month','security_id','unresolved']].copy()
    calendar=pd.DatetimeIndex(pd.read_parquet(OLD/'CSI_ALL.parquet').index).sort_values()
    ep30=EP.parent/'30_pit_data_foundation_v1'
    val_release=json.loads((ep30/'outputs/backfill_v2/release.json').read_text())
    val_path=Path(val_release['path'])/'normalized/vendor_valuations.parquet'
    vals=pd.read_parquet(val_path)
    vals['date']=pd.to_datetime(vals.date)
    assert not vals.duplicated(['instrument','date']).any()
    vals['year']=vals.date.dt.year
    val_year=vals.groupby('year').agg(rows=('date','size'),dates=('date','nunique'),instruments=('instrument','nunique'),
        positive_pe=('vendor_pe_ttm',lambda x:int(x.gt(0).sum())),known_at=('known_at',lambda x:int(x.notna().sum()))).reset_index()
    val_year.to_csv(OUT/'pe_raw_coverage.csv',index=False)
    pe_index=vals.set_index(['instrument','date']).vendor_pe_ttm
    sid_list=sorted(members.security_id.unique());sid_to_i={s:i for i,s in enumerate(sid_list)}
    stock_names=['turn_short','turn_medium','volume_short','turn_rank504','turn_rank756','pe_change21','pe_change63']
    arrays={name:np.full((len(calendar),len(sid_list)),np.nan,dtype=np.float32) for name in stock_names+['turn_median','money']}
    price_count=np.zeros(len(calendar),dtype=int);money_count=np.zeros(len(calendar),dtype=int)
    hashes={str(assignment_path):sha(assignment_path),str(val_path):sha(val_path)}
    stock_coverage=[];prefix_checks=0
    for i,sid in enumerate(sid_list):
        p=release/'normalized/prices_qfq'/f'{sid}.parquet'
        h=sha(p);assert h==oldaudit['reads'][str(p)] if 'reads' in oldaudit else h==identity['daily_read_files'][str(p.relative_to(release))]
        hashes[str(p)]=h
        d=pd.read_parquet(p,columns=['date','instrument','close','close_conflict','volume','money','turnover_rate',
            'volume_conflict','money_conflict','turnover_rate_conflict']).set_index('date').reindex(calendar)
        def valid(field):
            x=pd.to_numeric(d[field],errors='coerce')
            return x.where(x.ge(0)&d[field+'_conflict'].eq(False))
        turn=valid('turnover_rate');volume=valid('volume');money=valid('money')
        pe=pd.Series(pe_index.reindex(pd.MultiIndex.from_arrays([d.instrument,calendar])).to_numpy(),index=calendar)
        f=stock_features(turn,volume,pe)
        for name in stock_names:arrays[name][:,i]=f[name].to_numpy(np.float32)
        arrays['turn_median'][:,i]=turn.to_numpy(np.float32);arrays['money'][:,i]=money.to_numpy(np.float32)
        price_count+=(pd.to_numeric(d.close,errors='coerce').gt(0)&d.close_conflict.eq(False)).to_numpy()
        money_count+=money.notna().to_numpy()
        stock_coverage.append(dict(security_id=sid,turn_known=int(turn.notna().sum()),volume_known=int(volume.notna().sum()),
            money_known=int(money.notna().sum()),pe_known=int(pe.notna().sum()),pe_known_main=int(pe[pe.index.to_series().between('2021-01-01','2024-09-30')].notna().sum())))
        if i%1000==0:
            prefix=f.iloc[:1000];replay=stock_features(turn.iloc[:1000],volume.iloc[:1000],pe.iloc[:1000])
            assert np.allclose(prefix,replay,equal_nan=True);prefix_checks+=1
            print('verified multi-scale stock partitions',i,'/',len(sid_list),flush=True)
    pd.DataFrame(stock_coverage).to_csv(OUT/'stock_field_coverage.csv',index=False)
    money_total=np.nansum(arrays['money'],axis=1)
    money_total[(money_count<.8*price_count)|(money_total<=0)]=np.nan
    pd.DataFrame(dict(date=calendar,price_count=price_count,money_count=money_count,money_total=money_total)).to_csv(OUT/'market_proxy_coverage.csv',index=False)
    month=calendar.to_period('M');raw=[]
    for key,g in members.groupby(['era','level','industry_code','month'],sort=True):
        era,level,code,m=key;target=m+1
        if (era=='SW2014' and target>pd.Period('2021-11')) or (era=='SW2021' and target<pd.Period('2022-01')):continue
        days=np.flatnonzero(month==target)
        if not len(days):continue
        indexes=np.array([sid_to_i[s] for s in g.security_id]);n=len(indexes)+int(g.unresolved.max())
        r=pd.DataFrame(dict(date=calendar[days],era=era,level=level,industry_code=code,member_count=n))
        for name in stock_names+['turn_median']:
            values=arrays[name][np.ix_(days,indexes)];count=np.isfinite(values).sum(axis=1)
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',RuntimeWarning)
                median=np.nanmedian(values,axis=1)
            median[(count<.8*n)|(n<5)]=np.nan;r[name]=median
        values=arrays['turn_short'][np.ix_(days,indexes)];count=np.isfinite(values).sum(axis=1)
        r['expansion_breadth']=np.divide((values>0).sum(axis=1),count,out=np.full(len(days),np.nan),where=(count>=.8*n)&(n>=5))
        money=arrays['money'][np.ix_(days,indexes)];count=np.isfinite(money).sum(axis=1)
        sums=np.nansum(money,axis=1);sums[(count<.8*n)|(n<5)]=np.nan
        r['money_share']=sums/money_total[days]
        raw.append(r)
    panel=pd.concat(raw,ignore_index=True)
    daily=pd.read_parquet(OLD/'daily_industries.parquet',columns=KEY+['date'])
    panel=daily.merge(panel,on=['era','level','industry_code','date'],how='left',validate='one_to_one')
    paths=[]
    for key,g in panel.groupby(KEY):
        f=path_features(g);paths.append(f)
        if len(f)>200 and len(paths)%100==0:
            prefix=path_features(g.sort_values('date').iloc[:200])
            assert np.allclose(prefix[GROUPS['paths']+['share_short','turn21','share21']],f.iloc[:200][GROUPS['paths']+['share_short','turn21','share21']],equal_nan=True)
            prefix_checks+=1
    panel=pd.concat(paths,ignore_index=True)
    panel.to_parquet(CACHE/'daily_expansion.parquet',index=False)
    state=pd.read_parquet(OLD.parent/'online_v7/state_features.parquet')
    take=KEY+['date','turn21','share21','expansion_breadth','block_day']
    stage=state.merge(panel[KEY+['date']+GROUPS['levels']+GROUPS['paths']+['turn21','share21','block_day','pe_change21','pe_change63']],
        on=KEY+['date'],how='left',validate='many_to_one')
    anchors=panel[take].rename(columns={c:'anchor_'+c for c in take if c not in KEY})
    stage=stage.merge(anchors,left_on=KEY+['candidate_low_date'],right_on=KEY+['anchor_date'],how='left',validate='many_to_one')
    assert stage.candidate_low_date.le(stage.date).all()
    stage['stage_turn_change']=logratio(stage.turn21,stage.anchor_turn21)
    stage['stage_share_change']=logratio(stage.share21,stage.anchor_share21)
    stage['stage_breadth_change']=stage.expansion_breadth-stage.anchor_expansion_breadth
    stage['stage_turn_speed']=stage.stage_turn_change/(stage.block_day-stage.anchor_block_day).clip(lower=1)
    stage=stage[['row_id','threshold','date']+KEY+ADDED+['pe_change21','pe_change63','candidate_low_date']]
    assert not stage.duplicated(['row_id','threshold']).any()
    stage.to_parquet(CACHE/'expansion_features.parquet',index=False)
    cov=[]
    for (year,level),g in stage.assign(year=stage.date.dt.year).groupby(['year','level']):
        for name,cols in dict(GROUPS,pe=['pe_change21','pe_change63']).items():
            cov.append(dict(year=year,level=level,family=name,rows=len(g),complete=int(g[cols].notna().all(axis=1).sum()),
                any_feature=int(g[cols].notna().any(axis=1).sum())))
    pd.DataFrame(cov).to_csv(OUT/'feature_coverage.csv',index=False)
    main=stage[stage.date.between('2021-01-01','2024-09-30')]
    js(OUT/'pe_verdict.json',dict(status='BLOCKED_DATA',raw_rows=len(vals),known_at=int(vals.known_at.notna().sum()),
        main_pe_feature_rows=int(main[['pe_change21','pe_change63']].notna().any(axis=1).sum()),
        total_recent_feature_rows=int(stage[['pe_change21','pe_change63']].notna().any(axis=1).sum()),
        four_group_PE_volume_test='NOT_ESTIMATED',reason='no PE time series in 2021-2024 primary evaluation; 2017 isolated day and 2026 recent window; vintage unknown'))
    js(OUT/'feature_receipt.json',dict(source_hashes=hashes,features_sha256=sha(CACHE/'expansion_features.parquet'),
        daily_sha256=sha(CACHE/'daily_expansion.parquet'),rows=len(stage),prefix_checks=prefix_checks,
        no_outcomes_used=True,code_sha256=sha(__file__)))
    print('FEATURES COMPLETE',len(stage),'prefix checks',prefix_checks,flush=True)


if __name__=='__main__':run()
