"""Explain frozen candidate observations without importing retrospective labels."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,CACHE,sha

CANDIDATES={'early_model':'BALANCED','momentum':'BROAD20'}
STATE={'NEW':'新入观察','TRACKING':'持续跟踪','EXIT':'退出/失效','NOT_TRIGGERED':'暂未触发','DATA_INSUFFICIENT':'数据不足'}
REASON={'LOWER_CURRENT_PRIORITY':'同日优先级低于新候选，释放观察位置；不等同于价格改善已经失败','TWO_WEAK_REVIEWS':'20日收益连续两次复核非正','EIGHT_WEEK_LIMIT':'达到8个观察周上限','IDENTITY_MISSING':'行业身份不在当前目录','DATA_OR_CHAIN_UNAVAILABLE':'数据支持不足或价格链变化','LOCAL_IMPROVEMENT':'5日价格仍有正向变化，继续跟踪','RISK_OR_NO_IMPROVEMENT':'本周5日价格未改善，记录风险并继续复核','FIXED_SCORE_POSITIVE_LOCAL_PRICE':'5日收益为正，满足数据支持、冷却和当日排序容量条件'}

def main():
    out=EP/'handoff/v3_candidates_20261016';assert not out.exists()
    replay=EP/'outputs/v3_m06_replay';models=EP/'outputs/v3_m02_models';inputs=[Path(__file__),replay/'receipt.json',models/'receipt.json']
    for root in [replay,models]:
        r=json.loads((root/'receipt.json').read_text())
        for f,h in r['artifacts'].items():assert sha(root/f)==h
    # Whitelist only contemporaneous fields. No label, process ID or maturity column.
    fields=['date','era','industry_code','industry_name','block','nav','r5','r20','r40','prior20','change5','change20','drawdown20','rebound20','vol20','negative_share20','enhance','eligible','score_LR_COVER','score_LR_EARLY_UNION']
    featurepath=models/'scored_catalog.parquet';features=pd.read_parquet(featurepath,columns=fields)
    for raw,name in [('score_LR_COVER','coverage_rank_pct'),('score_LR_EARLY_UNION','early_rank_pct')]:features[name]=features.groupby('date')[raw].rank(pct=True,method='average')
    features=features.drop(columns=['score_LR_COVER','score_LR_EARLY_UNION'])
    marketpath=CACHE/'forecast_v5/CSI_ALL.parquet';market=pd.read_parquet(marketpath).close
    # Use stored trading-calendar dates, preserving unknown market observations.
    version=json.loads((EP/'outputs/evaluation_versions/v3_m06/version.json').read_text());calendarpath=Path(version['calendar_path']);calendar=pd.read_parquet(calendarpath).date
    market=market.reindex(pd.DatetimeIndex(calendar));market5=market/market.shift(5)-1;market20=market/market.shift(20)-1
    inputs.extend([featurepath,marketpath,calendarpath]);out.mkdir(parents=True)
    support=pd.read_csv(replay/'calendar_coverage.csv',parse_dates=['date']);support.to_csv(out/'calendar_coverage.csv',index=False)
    manifests={}
    for name,arm in CANDIDATES.items():
        run='solo_'+arm+'_COMPETE';root=replay/run;dest=out/name;dest.mkdir()
        catalog=pd.read_parquet(root/'catalog_states.parquet');events=pd.read_parquet(root/'events.parquet');decision=pd.read_parquet(root/'decisions.parquet').set_index('date')
        inputs.extend([root/'catalog_states.parquet',root/'events.parquet',root/'decisions.parquet'])
        f=catalog.merge(features.drop(columns=['industry_name','r5','r20']),on=['date','era','industry_code'],how='left',validate='one_to_one')
        f['market_r5']=f.date.map(market5);f['market_r20']=f.date.map(market20);f['excess_r5']=f.r5-f.market_r5;f['excess_r20']=f.r20-f.market_r20
        f['prior_price_state']=np.where(f.prior20.isna(),'此前价格状态未知',np.where(f.prior20.le(0),'此前20日收益非正','此前20日收益为正'))
        f['candidate_version']='EP34-V3-CANDIDATE-'+name+'-20261112';f['model_version']=f.date.dt.year.map(lambda y:f'M02-{y}-LR_COVER+LR_EARLY_UNION' if arm=='BALANCED' else 'RULE-r20')
        f['score_meaning']='当日覆盖/早期两模型百分位等权；非上涨概率' if arm=='BALANCED' else '20日简单价格收益排序；非上涨概率'
        episode={};last={};ledger=[];lookup={};name_history={}
        for date,e in events.groupby('date',sort=True):
            for row in e.itertuples():
                k=(row.era,row.industry_code)
                if row.kind=='NEW':
                    assert k not in episode
                    episode[k]=dict(observation_id=row.event_id,first_alert=date,previous_observation_id=last.get(k))
                assert k in episode,(run,k,row.kind)
                info=episode[k].copy();lookup[(date,*k)]=info|dict(event_id=row.event_id,event_kind=row.kind,event_reason=REASON[row.reason])
                ledger.append(dict(date=date,era=row.era,industry_code=row.industry_code,event_id=row.event_id,event_kind=row.kind,raw_reason=row.reason,event_reason=REASON[row.reason],**info))
                if row.kind=='EXIT':last[k]=episode[k]['observation_id'];del episode[k]
        # Forward fill episode identity only for rows actually in pool; all UPDATEs have events.
        ids=[];reasons=[];ranks=[];free=[];research=[]
        for row in f.itertuples():
            info=lookup.get((row.date,row.era,row.industry_code),{})
            ids.append({k:info.get(k) for k in ['observation_id','first_alert','previous_observation_id','event_id','event_kind']})
            d=decision.loc[row.date];candidates=list(d.qualified_candidates);ranks.append(candidates.index(row.industry_code)+1 if row.industry_code in candidates else None);free.append(int(d.free_slots))
            if info:reason=info['event_reason']
            elif row.state=='DATA_INSUFFICIENT':reason='缺少同价格链40日支持；不能解释为没有机会'
            elif not row.eligible:reason='当前不满足5日正收益准入'
            else:reason='已有价格迹象，但冷却、联合前20或每周新增上限未允许入池；具体排序见决策台账'
            reasons.append(reason)
            research.append('价格已有初步反馈，可进一步核查持续性、行业事件及基本面；原因尚未确认' if row.state in ['NEW','TRACKING'] else '未形成当前观察建议；不代表无改善或无研究价值')
        f=pd.concat([f.reset_index(drop=True),pd.DataFrame(ids)],axis=1);f['trigger_or_state_reason']=reasons;f['qualified_candidate_rank']=ranks;f['free_slots_before_admission']=free;f['why_research']=research
        f['status_cn']=f.state.map(STATE);f['absolute_gain_before_alert_proxy']=f.r20
        f['prior_gain_definition']='截至本复核日的20日累计涨幅；不是后验过程起点涨幅'
        f['followup_focus']='下一次复核5/20日变化与价格链；增强辅助证据为相邻复核20日收益提高，尚不证明新过程'
        f['exit_conditions']='连续两次20日非正、满8观察周、身份/价格链失效，或被更高优先级候选替换；退出后冷却4周'
        f['unknowns']='历史代理；持续性及经济原因未确认；未使用事件/基本面/量能/扩散确认；分数未校准'
        f['observation_date']=f.date;f['data_vintage_cutoff']='2026-10-21';f['record_type']='HISTORICAL_SIMULATION_CONTEMPORANEOUS_FIELDS'
        assert len(f)==len(catalog)==107141 and not f.duplicated(['date','era','industry_code']).any()
        assert f[f.state.isin(['NEW','TRACKING','EXIT'])].observation_id.notna().all()
        assert not any('target' in z or 'label' in z or 'process_id' in z for z in f.columns)
        f.to_parquet(dest/'all_period_catalog.parquet',index=False)
        for date,g in f.groupby('date'):
            folder=dest/'periods';folder.mkdir(exist_ok=True);g.to_csv(folder/(str(date.date())+'.csv'),index=False)
        latest=f[f.date.eq(f.date.max())];latest.to_csv(dest/'latest_full_directory.csv',index=False);latest[latest.state.isin(['NEW','TRACKING'])].to_csv(dest/'latest_pool.csv',index=False)
        le=pd.DataFrame(ledger);le.to_parquet(dest/'event_history.parquet',index=False)
        assert set(le.event_id)==set(events.event_id)
        weekly=f.groupby('date').state.value_counts().unstack(fill_value=0).reindex(support.date)
        for z in STATE:
            if z not in weekly:weekly[z]=0
        weekly['event_exits']=events[events.kind.eq('EXIT')].groupby('date').size().reindex(weekly.index,fill_value=0)
        weekly['directory_status']=support.set_index('date').state
        missing=weekly.directory_status.ne('SUPPORTED_DIRECTORY');weekly.loc[missing,[z for z in weekly.columns if z!='directory_status']]=np.nan
        weekly.to_csv(dest/'weekly_workload.csv')
        manifests[name]=dict(run=run,rows=len(f),events=len(le),periods=f.date.nunique(),latest=str(f.date.max().date()),current_pool=int(latest.state.isin(['NEW','TRACKING']).sum()),new=int(events.kind.eq('NEW').sum()),score='M02 equal percentile combination' if arm=='BALANCED' else 'r20',status='RESEARCH_CANDIDATE_NOT_USER_SELECTED_OR_DEPLOYED')
        print(name,manifests[name],flush=True)
    (out/'candidate_manifest.json').write_text(json.dumps(dict(candidates=manifests,capacity=dict(weekly_new=5,pool=20),scope='Separate alternatives, never union into a double-capacity pool. No retrospective labels in observation tables.'),ensure_ascii=False,indent=2)+'\n')
    (out/'receipt.json').write_text(json.dumps(dict(inputs={str(p):sha(p) for p in inputs},artifacts={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}),indent=2)+'\n')

if __name__=='__main__':main()
