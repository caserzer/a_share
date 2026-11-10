"""Independent causal/coverage/feature formula checks against source records."""
from common34 import *


def run():
    checks=[]
    def ck(name,ok):
        assert bool(ok),name
        checks.append(name)
    receipt=json.loads((OUT/'feature_receipt.json').read_text())
    ck('feature bytes match frozen input',sha(CACHE/'expansion_features.parquet')==receipt['features_sha256'])
    ck('daily bytes match frozen input',sha(CACHE/'daily_expansion.parquet')==receipt['daily_sha256'])
    features=pd.read_parquet(CACHE/'expansion_features.parquet')
    daily=pd.read_parquet(CACHE/'daily_expansion.parquet')
    ck('no infinite feature values',not np.isinf(features[ADDED].to_numpy()).any())
    ck('online anchors never from future',features.candidate_low_date.le(features.date).all())
    ck('no future labels in feature schema',not any(c in features.columns for c in ['y','peak_date','future_return','next_return']))
    lookup=daily.set_index(KEY+['date'])
    for i,r in enumerate(features.dropna(subset=GROUPS['stage']).sample(60,random_state=32).to_dict('records')):
        key=tuple(r[c] for c in KEY)
        at=lookup.loc[(*key,r['date'])];low=lookup.loc[(*key,r['candidate_low_date'])]
        turn=np.log(at.turn21/low.turn21);share=np.log(at.share21/low.share21)
        ck('stage formula '+str(i),np.isclose(turn,r['stage_turn_change']) and np.isclose(share,r['stage_share_change'])
            and np.isclose(at.expansion_breadth-low.expansion_breadth,r['stage_breadth_change'])
            and np.isclose(turn/max(1,at.block_day-low.block_day),r['stage_turn_speed']))
    # Abrupt future shocks cannot change earlier rolling/PE features.
    index=pd.bdate_range('2017-01-02',periods=1000)
    turn=pd.Series(np.linspace(.01,.03,1000),index=index)
    volume=pd.Series(np.linspace(100.,1000.,1000),index=index)
    pe=pd.Series(np.linspace(10.,30.,1000),index=index)
    full=stock_features(turn,volume,pe);cut=800
    shocked_turn=turn.copy();shocked_volume=volume.copy();shocked_pe=pe.copy()
    shocked_turn.iloc[cut:]=10;shocked_volume.iloc[cut:]=1e12;shocked_pe.iloc[cut:]=1e6
    shocked=stock_features(shocked_turn,shocked_volume,shocked_pe)
    ck('future shock cannot alter past rolling features',np.allclose(full.iloc[:cut],shocked.iloc[:cut],equal_nan=True))
    t=799
    ck('nonoverlapping short turnover windows',np.isclose(full.turn_short.iloc[t],np.log(turn.iloc[t-20:t+1].mean()/turn.iloc[t-83:t-20].mean())))
    ck('nonoverlapping medium turnover windows',np.isclose(full.turn_medium.iloc[t],np.log(turn.iloc[t-62:t+1].mean()/turn.iloc[t-188:t-62].mean())))
    gaps=pd.Series(np.nan,index=index);gaps.iloc[[0,21,999]]=[10,20,30]
    ck('isolated PE snapshots never form continuous return',stock_features(turn,volume,gaps)[['pe_change21','pe_change63']].isna().all().all())
    missing=turn.copy();missing.iloc[100:180]=np.nan
    ck('missing turnover window is not zero expansion',pd.isna(stock_features(missing,volume,pe).turn_short.iloc[180]))
    ck('unknown PE excluded from model features',not any(c.startswith('pe_') for c in ADDED))
    ck('main PE remains entirely unavailable',features[features.date.between('2021-01-01','2024-09-30')][['pe_change21','pe_change63']].isna().all().all())
    # Recompute industry medians from individual source turnover windows.
    source_identity=json.loads((EXT/'v4_adaptive_6_18_months/outputs/audits/inputs.json').read_text())
    source=Path(source_identity['price_release'])
    members=pd.read_parquet(OLD.parent/'extension_v2/products/assignments.parquet')
    calendar=pd.DatetimeIndex(pd.read_parquet(OLD/'CSI_ALL.parquet').index).sort_values()
    samples=daily[daily.date.between('2021-01-01','2024-09-30')&daily.member_count.between(5,30)&daily.turn_short.notna()].sample(12,random_state=32)
    read_cache={}
    for n,r in enumerate(samples.itertuples()):
        g=members[members.era.eq(r.era)&members.level.eq(r.level)&members.industry_code.eq(r.industry_code)&members.month.eq(r.date.to_period('M')-1)]
        values=[];position=calendar.get_loc(r.date)
        for sid in g.security_id:
            if sid not in read_cache:
                f=pd.read_parquet(source/'normalized/prices_qfq'/f'{sid}.parquet',columns=['date','turnover_rate','turnover_rate_conflict']).set_index('date').reindex(calendar)
                read_cache[sid]=f.turnover_rate.where(f.turnover_rate.ge(0)&f.turnover_rate_conflict.eq(False))
            x=read_cache[sid]
            short=x.iloc[position-20:position+1];past=x.iloc[position-83:position-20]
            value=np.log(short.mean()/past.mean()) if short.count()>=17 and past.count()>=51 and short.mean()>0 and past.mean()>0 else np.nan
            values.append(value)
        expected=np.nanmedian(values)
        ck('industry prior-member median raw replay '+str(n),np.isclose(expected,r.turn_short,rtol=1e-6,atol=1e-7))
    for key,g in list(daily.groupby(KEY))[::100]:
        if len(g)<220:continue
        prefix=path_features(g.sort_values('date').iloc[:200])
        original=g.sort_values('date').iloc[:200]
        ck('industry path prefix '+str(key),np.allclose(prefix[GROUPS['paths']+['share_short']],original[GROUPS['paths']+['share_short']],equal_nan=True))
    js(OUT/'feature_validation.json',dict(status='PASS',checks_count=len(checks),checks=checks))
    print('PASS',len(checks),'feature causality and raw formula checks')


if __name__=='__main__':run()
