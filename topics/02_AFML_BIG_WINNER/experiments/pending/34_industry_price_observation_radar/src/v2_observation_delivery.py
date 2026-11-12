"""Auditable historical observation delivery with local data-quality markers."""
import json,hashlib
import argparse,re
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--tag',required=True);args=parser.parse_args()
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}',args.tag):raise ValueError('Invalid version tag')
    root=EP/'outputs/refresh'/args.tag;out=root/'delivery'
    if out.exists():raise FileExistsError('Preserve delivery')
    out.mkdir()
    rawpath=PRIOR/'daily_industries.parquet'
    fields=['date','era','industry_code','nav','block','status','stale_members','max_stale_days','boundary_proxy','anchor_coverage']
    raw=pd.read_parquet(rawpath,columns=fields).rename(columns={'block':'price_chain_block','status':'raw_price_status'})
    data_version=sha(rawpath);checks=[];inputs={str(rawpath):data_version,str(root/'receipt.json'):sha(root/'receipt.json'),str(Path(__file__)):sha(Path(__file__))}
    for arm in ('A','B'):
        catpath=root/arm/'catalog_states.parquet';evpath=root/arm/'events.parquet'
        inputs.update({str(catpath):sha(catpath),str(evpath):sha(evpath)})
        cat=pd.read_parquet(catpath);ev=pd.read_parquet(evpath)
        d=cat.merge(raw,on=['date','era','industry_code'],how='left',validate='one_to_one',indicator=True)
        d['source_data_version']=data_version;d['source_price_date']=d.date.where(d._merge.eq('both')&d.nav.notna())
        new=ev[ev.kind.eq('NEW')].set_index('event_id')
        d['entry_price_chain']=d.observation_id.map(new.block)
        entrynav=raw.set_index(['date','era','industry_code']).nav
        anchors={r.event_id:entrynav.loc[(r.date,r.era,r.industry_code)] for r in new.reset_index().itertuples()}
        d['entry_nav']=d.observation_id.map(anchors)
        chain_ok=d.price_chain_block.notna()&d.price_chain_block.eq(d.entry_price_chain)&d.nav.gt(0)&d.entry_nav.gt(0)
        previous=d.since_entry.copy();d['since_entry']=(d.nav/d.entry_nav-1).where(chain_ok)
        suppressed=int((previous.notna()&d.since_entry.isna()).sum())
        d['since_entry_support']=np.where(d.observation_id.isna(),'NO_ACTIVE_OBSERVATION',np.where(chain_ok,'SAME_CHAIN','UNKNOWN_CHAIN_OR_PRICE'))
        d['has_stale_members']=d.stale_members.gt(0)
        d['unknowns']=d.unknowns+np.where(d.has_stale_members,'；部分成分价格沿用，详见stale_members/max_stale_days','')
        d['unknowns']=d.unknowns+np.where(d.boundary_proxy.fillna(False).astype(bool),'；分类/价格边界代理标记','')
        d['unknowns']=d.unknowns+np.where(d._merge.ne('both'),'；当前目录身份无本地日价格行','')
        for obs,g in d[d.state.isin(['NEW','TRACKING'])].groupby('observation_id'):
            r=new.loc[obs]
            assert g.era.eq(r.era).all() and g.industry_code.eq(r.industry_code).all()
            assert g.first_alert.eq(r.date).all() and g.date.ge(r.date).all()
            assert g.entry_price_chain.eq(g.price_chain_block).all()
        assert len(d)==len(cat) and not d.duplicated(['date','era','industry_code']).any()
        assert not any(x in d.columns for x in ['process_id','parent_id','child_id','label','covered','future_return'])
        d=d.drop(columns='_merge');dest=out/arm;dest.mkdir()
        d.to_parquet(dest/'all_observations.parquet',index=False)
        latest=d[d.date.eq(d.date.max())].copy();latest.to_csv(dest/'latest_full_catalog.csv',index=False)
        active=latest[latest.state.isin(['NEW','TRACKING'])].sort_values(['state','industry_code'])
        labels={'NEW':'新入观察','TRACKING':'持续跟踪','EXIT':'退出/失效','NOT_TRIGGERED':'暂未触发','DATA_INSUFFICIENT':'数据不足'}
        latest['状态']=latest.state.map(labels)
        def pct(x):return '未知' if pd.isna(x) else f'{x:.2%}'
        lines=[f'# {"20日质量候选" if arm=="A" else "5日及时性参照"}：历史观察清单','',
            f'**数据截至完整周 {d.date.max():%Y-%m-%d}；不能当作当前实时观察或买入建议。** 这是尚未完成业务验收的历史候选池。','',
            f'本期目录{len(latest)}个；在池{len(active)}个；新增{int(latest.state.eq("NEW").sum())}个；数据不足{int(latest.state.eq("DATA_INSUFFICIENT").sum())}个。每周新增最多5个，在池最多20个。',
            '', '|行业|状态|首次提示|跟踪周数|5日变化|20日变化|相对市场20日|入池后同链变化|数据提示|',
            '|---|---|---|---:|---:|---:|---:|---:|---|']
        for r in active.itertuples():
            flags=[]
            if r.has_stale_members:flags.append(f'{int(r.stale_members)}个成分沿用旧价')
            if pd.notna(r.boundary_proxy) and r.boundary_proxy:flags.append('边界代理')
            flags.append('非严格PIT')
            lines.append(f'|{r.industry_name}|{labels[r.state]}|{r.first_alert:%Y-%m-%d}|{int(r.age_weeks)}|{pct(r.r5)}|{pct(r.r20)}|{pct(r.relative20)}|{pct(r.since_entry)}|{"；".join(flags)}|')
        lines+=['','入池依据：40日同链历史可用，近5日与20日均上涨，按'+('20' if arm=='A' else '5')+'日涨幅排序进入本池空位。相对市场表现仅作背景，不是准入条件。',
            '', '持续跟踪不表示每周仍在升温；短期回落如尚未达到退出规则，清单会保留风险跟踪。',
            '', '失效规则：身份/价格链或数据不可用退出；连续两次周复核20日涨幅非正退出；入池满8周退出。重新入池至少间隔4周，分配新观察ID，但不自动增加事后过程成功数。',
            '', '研究入口：核查价格反馈是否具有行业共性、驱动因素是否持续。订单、盈利、基本面改善及配置价值尚未确认。价格观察有效不保证提示后继续上涨。',
            '', '完整目录含暂未触发、数据不足与退出，见同目录 latest_full_catalog.csv；全部历史逐期记录见 all_observations.parquet。后验标签与覆盖仅存于独立评价目录。']
        exits=latest[latest.state.eq('EXIT')]
        reasons={'EIGHT_WEEK_LIMIT':'满8周退出','TWO_WEAK_REVIEWS':'连续两次20日涨幅非正','DATA_OR_CHAIN_UNAVAILABLE':'价格链或数据不足','IDENTITY_MISSING':'分类身份不再可用'}
        lines+=['','本周退出：'+('；'.join(f'{r.industry_name}（{reasons.get(r.trigger_or_update_reason,r.trigger_or_update_reason)}）' for r in exits.itertuples()) or '无')]
        (dest/'latest_review.md').write_text('\n'.join(lines)+'\n')
        checks.append(dict(arm=arm,rows=len(d),latest_rows=len(latest),latest_pool=len(active),
            latest_stale_pool=int(active.has_stale_members.sum()),cross_chain_return_suppressed=suppressed,
            active_observation_ids_verified=True,no_future_label_columns=True))
    (out/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    version=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
    (out/'receipt.json').write_text(json.dumps(dict(inputs=inputs,delivery_version=version,
        artifacts={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}),indent=2)+'\n')
    print(json.dumps(checks,indent=2))


if __name__=='__main__':main()
