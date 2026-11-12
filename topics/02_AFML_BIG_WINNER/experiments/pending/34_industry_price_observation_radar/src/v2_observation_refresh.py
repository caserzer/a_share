"""Standalone local-only observation ledgers. No retrospective label input."""
import json
import argparse
import re
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,CACHE,sha
from v2_b06_replay import prepare


def same_chain_return(current,entry,current_block,entry_block):
    if any(pd.isna(v) for v in [current,entry,current_block,entry_block]):return None
    if current<=0 or entry<=0 or current_block!=entry_block:return None
    return float(current/entry-1)


def run(c,arm,relative,rule_version):
    pool={};exits={};history={};events=[];catalog=[];burden=[];number=0
    scorefield='r20' if arm=='A' else 'r5'
    for date,g in c.groupby('date',sort=True):
        week=int(g.week.iloc[0]);now={(r.era,r.industry_code):r for r in g.itertuples()};new=set();updated=set();exited={}
        def emit(key,kind,row,reason):
            nonlocal number
            number+=1;eid=f'S01-{arm}-{number:07d}'
            known=row is not None and np.isfinite(row.r5) and np.isfinite(row.r20) and np.isfinite(row.r40)
            events.append(dict(event_id=eid,date=date,week=week,era=key[0],industry_code=key[1],kind=kind,reason=reason,
                block=None if row is None else row.block,r5=None if row is None else row.r5,r20=None if row is None else row.r20,
                score=None if row is None else getattr(row,scorefield),positive_evidence=bool(known and row.r5>0),
                enhancement_evidence=bool(known and row.enhance)))
            return eid
        for key,p in list(pool.items()):
            row=now.get(key);known=row is not None and np.isfinite(row.r40) and np.isfinite(row.r5) and row.block==p['block']
            p['weak']=p['weak']+1 if known and row.r20<=0 else 0
            reason=('IDENTITY_MISSING' if row is None else 'DATA_OR_CHAIN_UNAVAILABLE' if not known else
                    'TWO_WEAK_REVIEWS' if p['weak']>=2 else 'EIGHT_WEEK_LIMIT' if week-p['entry_week']>=8 else None)
            if reason:
                emit(key,'EXIT',row,reason);exited[key]=reason;history[key]=p.copy();del pool[key];exits[key]=week
            else:emit(key,'UPDATE',row,'LOCAL_IMPROVEMENT' if row.r5>0 else 'RISK_OR_NO_IMPROVEMENT');updated.add(key)
        ranked=g[g.eligible].sort_values([scorefield,'industry_code'],ascending=[False,True])
        candidates=[r for r in ranked.itertuples() if (r.era,r.industry_code) not in pool and week-exits.get((r.era,r.industry_code),-100)>=4]
        q=min(5,20-len(pool),len(candidates))
        for row in candidates[:q]:
            key=(row.era,row.industry_code);eid=emit(key,'NEW',row,f'POSITIVE_5D_20D_RANK_{scorefield.upper()}')
            pool[key]=dict(observation_id=eid,entry_week=week,first_alert=date,entry_nav=row.nav,entry_r20=row.r20,block=row.block,weak=0)
            history[key]=pool[key].copy();new.add(key)
        for key,row in now.items():
            known=np.isfinite(row.r40) and np.isfinite(row.r5)
            state='NEW' if key in new else 'TRACKING' if key in pool else 'EXIT' if key in exited else 'DATA_INSUFFICIENT' if not known else 'NOT_TRIGGERED'
            obs=pool.get(key,history.get(key) if state=='EXIT' else None)
            m5,m20=relative.get(date,(np.nan,np.nan))
            rel5=(1+row.r5)/(1+m5)-1 if np.isfinite(row.r5) and np.isfinite(m5) else None
            rel20=(1+row.r20)/(1+m20)-1 if np.isfinite(row.r20) and np.isfinite(m20) else None
            reason=(f'近5日和20日均上行，按{20 if arm=="A" else 5}日表现排序新增观察' if state=='NEW' else
                    '短期价格继续改善，保留跟踪' if state=='TRACKING' and row.r5>0 else
                    '短期价格未继续改善，保留风险跟踪' if state=='TRACKING' else
                    exited.get(key) if state=='EXIT' else '同链历史不足或缺价，无法判断' if state=='DATA_INSUFFICIENT' else
                    '本期未新增：可能未满足价格条件、排名/容量或重入间隔限制；不代表没有机会')
            catalog.append(dict(date=date,era=row.era,industry_code=row.industry_code,industry_name=row.industry_name,state=state,
                rule_version=rule_version,observation_id=None if obs is None else obs['observation_id'],
                first_alert=None if obs is None else obs['first_alert'],age_weeks=None if obs is None else week-obs['entry_week'],
                weak_reviews=None if obs is None else obs['weak'],r5=row.r5,r20=row.r20,relative5=rel5,relative20=rel20,
                entry_prior20=None if obs is None else obs['entry_r20'],since_entry=None if obs is None else same_chain_return(row.nav,obs['entry_nav'],row.block,obs['block']),
                trigger_or_update_reason=reason,
                invalidation_rule='同链数据不可用/身份缺失退出；连续2次周复核20日涨幅非正退出；入池满8周退出；退出后至少4周可重入',
                evidence_grade='PRICE_ONLY_HISTORICAL_PROXY',
                unknowns='基本面、订单和盈利原因未确认；上游数据非严格PIT认证'+('；同链价格支持不足' if not known else '')+('；相对市场背景缺失' if rel20 is None else ''),
                research_question='核查价格变化的行业共性、驱动因素与延续条件，当前价格证据不能确认经济解释' if state in ('NEW','TRACKING') else None))
        burden.append(dict(date=date,new=q,pool=len(pool),updates=len(updated),exits=len(exited)))
        assert q<=5 and len(pool)<=20
    return pd.DataFrame(events),pd.DataFrame(catalog),pd.DataFrame(burden)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--tag',required=True);args=parser.parse_args()
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}',args.tag):raise ValueError('Use a simple immutable version tag')
    out=EP/'outputs/refresh'/args.tag
    if out.exists():raise FileExistsError('Preserve standalone observation version')
    out.mkdir(parents=True)
    rec=json.loads((PRIOR/'receipt.json').read_text());calendar=Path(next(k for k in rec['inputs'] if k.endswith('/calendar.parquet')))
    marketpath=CACHE/'forecast_v5/CSI_ALL.parquet'
    paths=[PRIOR/'daily_industries.parquet',EP/'outputs/r01/weekly_catalog.parquet',calendar,marketpath,
           EP/'src/v2_b06_replay.py',EP/'protocols/v2_s01/plan.md',EP/'protocols/v2_s02/plan.md',EP/'protocols/v2_s02/calendar_gap_addendum.md',Path(__file__)]
    hashes={str(p):sha(p) for p in paths};version='S02-'+hashlib.sha256(json.dumps({str(x):hashes[str(x)] for x in paths[4:]},sort_keys=True).encode()).hexdigest()[:16]
    c=prepare();cal=pd.DatetimeIndex(pd.read_parquet(calendar).date)
    expected=pd.Series(cal).groupby(cal.to_period('W-SUN')).max()
    if cal.max().weekday()<4:expected=expected.iloc[:-1]
    observed=pd.DatetimeIndex(sorted(c.date.unique()));expected=pd.DatetimeIndex(expected)
    registered_gap=pd.DatetimeIndex(pd.to_datetime(['2021-12-03','2021-12-10','2021-12-17','2021-12-24','2021-12-31']))
    if len(observed.difference(expected)) or not expected.difference(observed).equals(registered_gap):
        raise ValueError('Unregistered catalog/calendar mismatch; do not silently extend historical gap exception')
    coverage=pd.DataFrame({'date':expected})
    coverage['state']=np.where(coverage.date.isin(observed),'SUPPORTED_DIRECTORY','CLASSIFICATION_TRANSITION_UNKNOWN')
    coverage['directory_count']=coverage.date.map(c.groupby('date').size()).astype('Int64')
    coverage.to_csv(out/'calendar_coverage.csv',index=False)
    market=pd.read_parquet(marketpath).sort_index().close.reindex(cal)
    m5=market/market.shift(5)-1;m20=market/market.shift(20)-1
    relative={d:(a,b) for d,a,b in zip(cal,m5,m20)}
    summary={}
    for arm in ('A','B'):
        ev,st,b=run(c,arm,relative,version);dest=out/arm;dest.mkdir()
        assert len(st)==len(c) and not st.duplicated(['date','era','industry_code']).any()
        ev.to_parquet(dest/'events.parquet',index=False);st.to_parquet(dest/'catalog_states.parquet',index=False);b.to_csv(dest/'weekly_burden.csv',index=False)
        latest=st[st.date.eq(st.date.max())];latest.to_csv(dest/'latest_full_catalog.csv',index=False)
        active=latest[latest.state.isin(['NEW','TRACKING'])].sort_values(['state','industry_code'])
        lines=[f'# S01-{arm} 历史观察快照', '',f'截至完整周：{st.date.max():%Y-%m-%d}。这是本地历史数据快照，不是当前实时观察。尚未获业务验收，不构成买入建议。',
               '',f'规则：独立运行，按{20 if arm=="A" else 5}日表现排序；每周最多5个新增、同时最多20个。规则版本：{version}。',
               '',f'本期目录{len(latest)}个身份，在池{len(active)}个，新入{int(latest.state.eq("NEW").sum())}个。',
               '', '|行业|状态|首次提示|年龄（周）|5日变化|20日变化|相对市场20日|入池后变化|观察编号|', '|---|---|---|---:|---:|---:|---:|---:|---|']
        def pct(x):return '未知' if pd.isna(x) else f'{x:.2%}'
        for r in active.itertuples():
            lines.append(f'|{r.industry_name}|{r.state}|{r.first_alert:%Y-%m-%d}|{int(r.age_weeks)}|{pct(r.r5)}|{pct(r.r20)}|{pct(r.relative20)}|{pct(r.since_entry)}|{r.observation_id}|')
        lines+=['','失效规则：价格链或身份不可用退出；连续两次周复核20日涨幅非正退出；8周到期退出。未知不当作价格失败。','',
            '观察用途：核查行业价格反馈的原因及延续条件；订单、盈利、基本面和配置价值尚未确认。入池后变化不是预测承诺。',
            '', '完整目录五类状态、逐项原因及未知见同目录 latest_full_catalog.csv；后验过程标签只在独立评价目录中，不回填这份当时清单。']
        exited=latest[latest.state.eq('EXIT')]
        lines+=['','本周退出：'+('；'.join(f'{r.industry_name}（{r.trigger_or_update_reason}）' for r in exited.itertuples()) or '无')]
        (dest/'latest_review.md').write_text('\n'.join(lines)+'\n')
        summary[arm]=dict(events=ev.kind.value_counts().to_dict(),catalog_rows=len(st),latest_date=str(st.date.max().date()),
            latest_states=latest.state.value_counts().to_dict(),mean_new=float(b.new.mean()),mean_pool=float(b.pool.mean()),max_pool=int(b.pool.max()))
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    (out/'receipt.json').write_text(json.dumps(dict(inputs=hashes,rule_version=version,
        limits=['historical proxy, not strict PIT','standalone quantities differ from paired experiments','not deployed or validated','496 supported directory weeks; 5 classification-transition weeks unknown, not zero signals'],
        artifacts={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}),indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
