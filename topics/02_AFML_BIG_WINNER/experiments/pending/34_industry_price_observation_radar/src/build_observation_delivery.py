"""Build an immutable research evidence catalogue from the failed R01 replay."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,CACHE,sha
from observation_evidence import trailing_evidence,entry_evidence

REASONS={'DATA_UNKNOWN':'价格历史不足，无法判断','NONPOSITIVE_MOMENTUM':'20日价格收益不再为正或未满足入池条件','POSITIVE_MOMENTUM_CAPACITY_RANK':'20日价格收益为正，并在当周容量排序中入选','CONTINUING':'继续跟踪原观察，未产生新提示','SUSPENDED_UNKNOWN':'数据暂缺，原观察暂停判断','MAX_OBSERVATION_AGE':'已达到60交易日观察期限','REPEATED_DATA_UNKNOWN':'连续两次复查数据不足','COOLDOWN':'退出后的冷却期未结束','CAPACITY_NOT_SELECTED':'正价格动量，但未进入当周容量名额','CLASSIFICATION_BOUNDARY':'分类制度切换，原观察结束'}
STATES={'NEW':'新入观察','TRACKING':'持续跟踪','EXIT':'退出/失效','NOT_TRIGGERED':'暂未触发','DATA_INSUFFICIENT':'数据不足'}


def main():
    out=EP/'outputs/delivery_v1';out.mkdir(exist_ok=True)
    if (out/'manifest.json').exists():raise FileExistsError('delivery version exists; never overwrite')
    catalogfile=EP/'outputs/r01/weekly_catalog.parquet';eventfile=EP/'outputs/r01/events.parquet';configfile=EP/'configs/r01_baseline.json'
    rawfile=PRIOR/'daily_industries.parquet';receiptfile=PRIOR/'receipt.json';marketfile=CACHE/'forecast_v5/CSI_ALL.parquet'
    receipt=json.loads(receiptfile.read_text());calendarfile=Path(next(x for x in receipt['inputs'] if x.endswith('/calendar.parquet')))
    cal=pd.DatetimeIndex(pd.read_parquet(calendarfile).date).sort_values();date_to_day={d:i for i,d in enumerate(cal)}
    market=pd.read_parquet(marketfile).close.reindex(cal);market.index=pd.RangeIndex(len(cal))
    raw=pd.read_parquet(rawfile,columns=['era','industry_code','date','day_i','nav','block','status'])
    cat=pd.read_parquet(catalogfile);events=pd.read_parquet(eventfile);config=json.loads(configfile.read_text())
    source=[catalogfile,eventfile,configfile,rawfile,receiptfile,calendarfile,marketfile,EP/'src/observation_evidence.py',Path(__file__)]
    hashes={str(x):sha(x) for x in source};data_version=sha(receiptfile)[:16]
    groups={k:g.set_index('day_i').sort_index() for k,g in raw.groupby(['era','industry_code'])}
    frames=[];prefix_checks=0
    for identity,c in cat.groupby(['era','industry_code'],sort=True):
        g=groups.get(identity,pd.DataFrame(columns=['nav','block','date'],index=pd.Index([],dtype=int)))
        if len(g):
            metrics=trailing_evidence(g,market)
            for stop in [1000,1800]:
                part=g[g.index<stop]
                if len(part):pd.testing.assert_frame_equal(metrics.loc[part.index],trailing_evidence(part,market[market.index<stop]));prefix_checks+=1
            current_dates=g.date.where(metrics.current_price_known)
            # Date metadata can carry last known date; prices are never forward-filled.
            last_dates=current_dates.reindex(range(int(g.index.min()),max(int(g.index.max()),int(c.day_i.max()))+1)).ffill()
        else:
            metrics=pd.DataFrame(columns=[f'{k}_return_{h}' for h in [5,20,60] for k in ['absolute','market','excess']]+['current_price_known']);last_dates=pd.Series(dtype='datetime64[ns]')
        c=c.copy();e=metrics.reindex(c.day_i);e.index=c.index;c=pd.concat([c,e],axis=1)
        c['current_price_known']=c.current_price_known.eq(True)
        c['price_data_date']=c.date.where(c.current_price_known)
        c['last_known_price_date']=c.day_i.map(last_dates)
        entry=[]
        for row in c.itertuples():
            first=None if pd.isna(row.first_hint_date) else date_to_day[row.first_hint_date]
            a,m,x,status=entry_evidence(g,market,first,int(row.day_i))
            entry.append(dict(since_first_hint_absolute=a,since_first_hint_market=m,since_first_hint_excess=x,since_first_hint_status=status,observation_age_sessions=None if first is None else row.day_i-first))
        c=pd.concat([c,pd.DataFrame(entry,index=c.index)],axis=1)
        for col in [x for x in c.columns if '_return_' in x]+['since_first_hint_absolute','since_first_hint_market','since_first_hint_excess','observation_age_sessions']:
            c[col]=pd.to_numeric(c[col],errors='coerce').astype(float)
        frames.append(c)
    f=pd.concat(frames).sort_values(['date','era','industry_code']).reset_index(drop=True)
    assert len(f)==len(cat) and not f.duplicated(['era','industry_code','date']).any()
    known=f.eligible.eq(True);assert np.allclose(f.loc[known,'score'],f.loc[known,'absolute_return_20'],atol=1e-12,rtol=1e-12)
    assert (f.input_asof<=f.date).all() and (f.price_data_date.dropna()<=f.loc[f.price_data_date.notna(),'date']).all()
    f['state_label']=f.state.map(STATES);f['trigger_explanation']=f.reason.map(REASONS);assert f.trigger_explanation.notna().all()
    f['artifact_version']='EP34-EVIDENCE-v1';f['data_version']=data_version;f['method_validation']='FAILED_R01_NOT_VALIDATED';f['simulation_status']='HISTORICAL_REPLAY'
    f['evidence_strength']=np.where(f.eligible.eq(True),'DESCRIPTIVE_PRICE_ONLY_UNCALIBRATED','INSUFFICIENT_PRICE_HISTORY')
    f['invalidation_conditions']='20日收益≤0；首次提示满60交易日；连续两次复查数据不足；分类制度切换。一次缺失只暂停判断。'
    f['economic_interpretation_status']='订单、盈利和产业景气未检验；价格观察不是买入建议。'
    f['research_reason']=np.where(f.state.isin(['NEW','TRACKING']),'历史价格变化线索，可进一步核查持续性与经济原因；规则本身未通过验收。',np.where(f.state.eq('DATA_INSUFFICIENT'),'数据不足，不能据此判断没有机会。',np.where(f.state.eq('EXIT'),'原观察结束；此状态不单独证明行业不存在其他机会。','该历史规则暂未提示，不等于没有改善过程。')))
    f['auxiliary_evidence_status']='BREADTH_AND_VOLUME_NOT_USED_BY_R01_RULE'
    f['price_process_id_asof']=None;f['process_identity_status']='RETROSPECTIVE_PROCESS_ID_NOT_USED_IN_ONLINE_CATALOG'
    f['historical_data_quality']='HISTORICAL_PROXY_NO_CERTIFIED_FIRST_VINTAGE'
    f.to_parquet(out/'weekly_evidence_catalog.parquet',index=False)
    events.to_parquet(out/'observation_events.parquet',index=False)
    weeks=f.groupby(['era','date']).agg(catalog_rows=('industry_code','size'),in_pool=('in_pool','sum'),data_insufficient=('state',lambda x:int(x.eq('DATA_INSUFFICIENT').sum())),new_industries=('state',lambda x:int(x.eq('NEW').sum())),exits=('state',lambda x:int(x.eq('EXIT').sum())))
    assert weeks.new_industries.le(config['weekly_new_cap']).all() and weeks.in_pool.le(config['pool_cap']).all()
    weeks.to_parquet(out/'weekly_workload.parquet')
    # Historical mature evaluation is a separate, explicitly later-asof file.
    evalfile=EP/'outputs/r01/evaluated_new_observations.parquet';ev=pd.read_parquet(evalfile);ev['evaluation_asof']=raw.date.max();ev['purpose']='RETROSPECTIVE_EVALUATION_ONLY_NOT_SIGNAL_INPUT'
    ev.to_parquet(out/'retrospective_evaluation.parquet',index=False)
    final=f[f.date.eq(f.date.max())];final.to_json(out/'latest_catalog.json',orient='records',date_format='iso',force_ascii=False,indent=2)
    manifest=dict(version='EP34-EVIDENCE-v1',status='RESEARCH_DELIVERY_ONLY_METHOD_FAILED',rules_version=config['version'],data_version=data_version,
        source_data_asof=str(raw.date.max().date()),latest_complete_review=str(f.date.max().date()),catalog_rows=len(f),review_weeks=len(weeks),latest_rows=len(final),state_counts=f.state.value_counts().to_dict(),
        weekly_new_cap=5,weekly_new_cap_provenance='USER_CONFIRMED',pool_cap=30,pool_cap_provenance='UNCONFIRMED_RESEARCH_ASSUMPTION',
        prefix_checks=prefix_checks,price_score_reproduced_rows=int(known.sum()),schema=list(f.columns),
        limitations=['R01 failed acceptance; no validated method','historical proxy data, not certified PIT','retrospective labels separate from asof evidence','not deployed or published','classification boundary exits also in events'],
        inputs={**hashes,str(evalfile):sha(evalfile)},artifacts={x.name:sha(x) for x in out.iterdir() if x.is_file()})
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ['status','catalog_rows','review_weeks','latest_rows','source_data_asof','latest_complete_review','prefix_checks','price_score_reproduced_rows']},ensure_ascii=False))


if __name__=='__main__':main()
