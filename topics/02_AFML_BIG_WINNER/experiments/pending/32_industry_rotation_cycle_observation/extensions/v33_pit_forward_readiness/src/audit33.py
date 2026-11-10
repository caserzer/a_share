from pathlib import Path
import json
import sys
import hashlib
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];EXT=ROOT.parent
sys.path.insert(0,str(EXT/'v31_all_signal_economics/src'))
from common31 import sha,js,md,OLD
OUT=ROOT/'outputs'


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    ep30=EXT.parent.parent/'30_pit_data_foundation_v1'
    release_path=ep30/'outputs/pit_v4/release.json'
    release=json.loads(release_path.read_text())
    facts_path=Path(release['path'])/'normalized/financial_reviewed_facts.parquet'
    facts=pd.read_parquet(facts_path)
    summary_path=ep30/'outputs/pit_v4/reviewed_fact_summary.json'
    original=json.loads(summary_path.read_text())
    assert len(facts)==original['financial_facts']
    facts['field_type']=facts.field.str.rsplit(':',n=1).str[0]
    financial=dict(status='BLOCKED_DATA',financial_facts=len(facts),issuers=facts.security_id.nunique(),
        versions=facts.original_version.nunique(),fields=facts.field_type.nunique(),
        report_periods=facts.event_time.astype(str).nunique(), known_at_present=int(facts.known_at.notna().sum()),
        all_amendments_complete=original['all_amendments_complete_claimed'],
        representative_industry_panel=False, independent_human_review=original['independent_human_review'],
        evidence_hashes={str(p):sha(p) for p in [release_path,facts_path,summary_path]})
    js(OUT/'financial_audit.json',financial)
    facts.groupby(['field_type','quality_tier']).agg(facts=('record_id','size'),issuers=('security_id','nunique'),versions=('original_version','nunique')).reset_index().to_csv(OUT/'financial_field_coverage.csv',index=False)
    gap_rows=[
        dict(item='行业成员原始known_at及修订链',status='BLOCKED_DATA',reason='已有生效区间代理不能认证当时真实可得版本'),
        dict(item='收入/利润/现金流共同改善面板',status='BLOCKED_DATA',reason=f'仅{len(facts)}条已核验事实/{facts.security_id.nunique()}个发行人；不能构建代表性全行业面板'),
        dict(item='单季度同比及连续改善',status='BLOCKED_DATA',reason='少数年报期及更正样例，缺连续季度和完整修订链'),
        dict(item='信号当时基本面特征',status='NOT_ESTIMATED',reason='不将公告后或当今修订值回填'),
        dict(item='信号后经营验证',status='NOT_ESTIMATED',reason='需独立足量后续报告，不以价格标签代替'),
    ]
    pd.DataFrame(gap_rows).to_csv(OUT/'data_gaps.csv',index=False)
    features=pd.read_parquet(OLD/'features.parquet',columns=['date','frequency'])
    daily=pd.read_parquet(OLD/'daily_industries.parquet',columns=['date'])
    market=pd.read_parquet(OLD/'CSI_ALL.parquet')
    readiness=dict(audit_date='2026-11-08',timezone='Asia/Shanghai',latest_industry_price=str(daily.date.max().date()),
        latest_market_price=str(market.index.max().date()),
        latest_observations={k:str(v.date()) for k,v in features.groupby('frequency').date.max().items()},
        elapsed_calendar_days_since_prices=(pd.Timestamp('2026-11-08')-daily.date.max()).days,
        status='BLOCKED_DATA',new_forward_predictions_created=0,production_deployed=False,
        reasons=['frozen prices end 2026-10-21, not current observation inputs',
                 'membership known_at/version certification missing',
                 'historical leader market-cap ranking known_at incomplete',
                 'no current complete certified feature/training release'],
        independent_forward_validation='FORWARD_PENDING')
    js(OUT/'forward_readiness.json',readiness)
    specs={}
    for name,version,filename in [('risk','v12_duration_risk','frozen_candidates.json'),('diffusion','v18_conditional_diffusion','frozen_candidates.json')]:
        p=EXT/version/'outputs'/filename
        specs[name]=dict(path=str(p),sha256=sha(p))
    now=pd.Timestamp.now(tz='Asia/Shanghai')
    contract=dict(version='ep32-forward-v1',frozen_at=now.isoformat(),client_audit_date='2026-11-08',
        score_cutoff=.11,market_rule='CSI_ALL close / close.shift(126) - 1 > 0',
        primary=dict(level='L3',threshold=.15,benchmark='CSI_ALL'),frequencies=['W','BW','M'],
        fit_schedule='quarterly; labels known strictly before quarter start',
        outcome_policy='prediction-only snapshots; append later outcomes separately',
        maximum_recording_delay_days=1,models=specs,
        historical_feature_quality='Historical-proxy',strict_PIT='BLOCKED_DATA',
        code_hashes={str(p):sha(p) for p in sorted((ROOT/'src').glob('*.py'))},
        plan_sha256=sha(EXT/'v31_all_signal_economics/research_plan.md'),
        status='SPECIFICATION_FROZEN_INPUTS_NOT_ADMITTED')
    contract['identity_sha256']=hashlib.sha256(json.dumps(contract,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    js(OUT/'forward_contract.json',contract)
    report=f'''# EP32 V33：基本面PIT审计与前瞻准入

审计范围是当前仓库和本机已封存数据，未把历史样例升级为全行业证据。核对封存EP30财务原始事实表：{financial['financial_facts']}条事实、{financial['issuers']}个发行人、{financial['versions']}份版本、{financial['fields']}种字段。公告可得时间存在不等于全体季度/修订链完整。收入、利润及现金流的代表性行业改善面板仍BLOCKED_DATA，因此本轮不能执行有代表性的基本面机制估计。

{md(pd.DataFrame(gap_rows))}

## 前瞻准备结果

冻结日按客户端2026-11-08记录，实际冻结时刻单列于合同。行业与市场数据截至{readiness['latest_industry_price']}，距审计日{readiness['elapsed_calendar_days_since_prices']}个自然日。最新完整观察日：{readiness['latest_observations']}。没有用旧数据生成11月信号；新增真前瞻预测0条，FORWARD_PENDING。

已冻结模型配置引用、分数阈值、市场条件、季度成熟标签规则和输入契约，并提供仅追加记录器。记录器拒绝冻结前回填、未来时点、超过1天延迟的历史重建、价格日期不符、证据缺失或哈希不符、未成熟训练标签、重复名单、包含未来结果的预测文件及选择规则不符；同一决策时间不能覆盖重写。

该记录器校验元数据与证据文件，不自行认证数据来源真实性，也不自行训练或生成预测。启用前必须构建并审计实际当时可用的全量输入、模型训练及预测发布流水线。当前准入失败的具体原因见forward_readiness.json。未安装调度、未下单、未发送外部消息。历史价格研究仍可按Historical-proxy继续，但不能称严格PIT或真实前瞻已验证。

后续最小数据交付：覆盖候选行业与同日对照行业的成员版本、连续季度收入/利润/现金流公告原件与更正链；保留每条known_at和源哈希。补齐后先审计覆盖与样本代表性，再分别检验信号时可知改善和信号后的经营验证，不能把两者混成事前特征。

[财务审计](../outputs/financial_audit.json) · [实时输入检查](../outputs/forward_readiness.json) · [冻结契约](../outputs/forward_contract.json) · [追加记录器](../src/forward_gate.py)
'''
    (ROOT/'reports').mkdir(exist_ok=True);(ROOT/'reports/readiness.md').write_text(report)
    print(json.dumps(financial,ensure_ascii=False,indent=2));print(json.dumps(readiness,ensure_ascii=False,indent=2))


if __name__=='__main__':
    run()
