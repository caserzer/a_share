from event_account import *
import json,re
def main():
    itemmap=[
      ('D4.1','fusion','eps20','ridge','HISTORICAL_PROXY','同机构同财年20日及半衰期60；另列同覆盖、纯标志和未正交'),
      ('D4.2','fusion','target20','ridge','HISTORICAL_PROXY','目标价同机构、拆并排除、币种A股映射；纯动量、同覆盖'),
      ('D4.3','fusion','coverage_delta','ridge','HISTORICAL_PROXY','滚动两组60日不同机构数及当前机构数对照；归档中断日期'),
      ('D4.4','fusion','sue20','ridge','NO_FUNDED_TRIGGER','年财期可算；Q1、半年、Q3无双机构且有历史误差的同口径共识'),
      ('D4.5','fusion','mixed','eps20','NO_INCREMENT_OVER_EPS','单EPS、单SUE、覆盖标志、两源交集和共同资金'),
      ('D4.6','events_h10','annual_profit','annual_profit_match','ANNUAL_ONLY_PROXY','正式、预告、快报各列；中期无触发；H10及H20独立行业市值匹配'),
      ('D4.7','events_h10','revenue_accel','revenue_accel_match','HISTORICAL_PROXY','营收、扣非各比单纯增速及同日匹配；H20受影响段独立重启'),
      ('D4.8','events_h10','eps_large','eps_large_match','HISTORICAL_PROXY','大幅对温和同日同资及行业市值配对，H10/H20'),
      ('D4.9','etf','two_flow','ridge','LAGGED_SHARE_PROXY','原300双基金、顺逆同席同资和退补代理'),
      ('D4.10','etf','expanded_flow','ridge','LAGGED_SHARE_PROXY','八只ETF、300共同席、各子域；800域外无冻结分与严格交易账'),
      ('D4.11','supply','expanded_supplier_partner','expanded_supplier_pseudo','DATED_EDGES_SMALL_N','9条合约，两个方向、同行动量、等数伪边及原4条'),
    ]
    rows=[];checks=[]
    for item,group,a,b,status,note in itemmap:
        c=pd.read_csv(OUT/group/'comparisons.csv')
        rr=c[(c.arm==a)&(c.comparator==b)&(c.stage=='all')].iloc[0]
        rows.append((item,status,group,a,b,rr.n,rr.bp,rr.low,rr.high,note))
    pd.DataFrame(rows,columns='item status group arm comparator months bp low high notes'.split()).to_csv(OUT/'register.csv',index=False)
    src=pd.read_parquet(OUT/'fund_inventory.parquet')
    names=src[['ts_code','csname','index_name','index_code','setup_date','list_date','list_status']].copy()
    names['sampled']=names.ts_code.str[:6].isin(pd.read_csv(HERE/'unit_history.csv',dtype=str).code)
    names['delisted_as_of_fetch']=names.list_status.eq('D')
    names['rename_history']='unverified';names['benchmark_change_history']='unverified'
    names.to_csv(OUT/'fund_lifecycle.csv',index=False)
    assert names.sampled.sum()==8 and names.delisted_as_of_fetch.sum()>0
    f=pd.read_csv(OUT/'fusion/folds.csv');assert(f.latest_mature_idx<f.quarter_start_idx).all()
    feat=pd.read_csv(OUT/'features/parity.csv');assert feat.rows.sum()==1076242 and feat.max_parity_error.max()<1e-10
    pairs=pd.read_parquet(OUT/'event_details/pairs.parquet')
    assert (pairs.cap_rank_difference<=.10+1e-12).all() and (pairs.event_security!=pairs.comparator_security).all()
    et=pd.read_parquet(OUT/'etf/choices.parquet')
    assert (et.score_flow>et.score_old).all() and (et.score_reverse<et.score_old).all()
    common=pd.read_parquet(OUT/'etf/targets.parquet',filters=[('arm','in',['two_common300_flow','expanded_common300_flow','ridge'])])
    pivot={a:{e:set(g.security_idx) for e,g in d.groupby('entry_idx')} for a,d in common.groupby('arm')}
    for e,t in pivot['ridge'].items():
        assert t-pivot['two_common300_flow'][e]==t-pivot['expanded_common300_flow'][e]
    for name in ['fusion','same_coverage','events_h10','events_h20','etf','supply']:
        v=pd.read_csv(OUT/name/'verification.csv');assert v.fee_error.max()<1e-10 and v.identity_error.max()<1e-10;checks.append((name,len(v),v.fee_error.max(),v.identity_error.max()))
    report=(HERE/'REPORT.md').read_text()
    for link in re.findall(r'\]\(([^)]+)\)',report):
        if '://' not in link:assert (HERE/link).is_file(),link
    evidence=[EP41/'p1/book.cpp',EP41/'p1/engine.py',EP41/'p1/matching.py',EP41/'p1/results/daily.parquet',EP41/'sources/n2/eps_events.parquet',EP41/'sources/n3_n4/results/annual_events.parquet',EP41/'sources/n3_n4/results/flash_events.parquet',EP41/'sources/n5/relationships.csv',engine.OUT800/'scores.parquet',engine.LOCAL/'wide_features.parquet',next(BASE.glob('35_*/data/r11_analyst_forecasts.parquet'))]
    gp=OUT/'artifact_hashes.csv'
    exclude={gp,OUT/'verification.json'}
    files=[f for f in HERE.rglob('*') if f.is_file() and '__pycache__' not in f.parts and f not in exclude]
    def digest(path):
        h=hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(1<<20),b''):h.update(block)
        return h.hexdigest()
    records=[('upstream',str(f),f.stat().st_size,digest(f)) for f in evidence]
    records.extend(('this_run',str(f.relative_to(HERE)),f.stat().st_size,digest(f)) for f in sorted(files))
    pd.DataFrame(records,columns='scope path bytes sha256'.split()).to_csv(gp,index=False)
    (OUT/'verification.json').write_text(json.dumps(dict(items=len(rows),artifacts_hashed=len(records),daily_feature_parity_max=float(feat.max_parity_error.max()),calibration_strict_maturity=True,etf_same_source_directions=True,etf_common_seats_verified=True,fund_inventory_status=names.list_status.value_counts().to_dict(),sources_acquired_after_historical_dates=True,audit_time_utc=pd.Timestamp.now(tz='UTC').isoformat(),account_checks=checks,manifest_sha256=digest(gp)),indent=2)+'\n')
    print('D4 verified',len(records),flush=True)
if __name__=='__main__':main()
