from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];EXT=ROOT.parent;OUT=ROOT/'outputs'
sys.path.insert(0,str(EXT/'v31_all_signal_economics/src'))
from common31 import sha,js,md,OLD,CACHE as ECON


def table(frame,columns,percent=()):
    g=frame[columns].copy()
    for c in percent:g[c]=g[c].map(lambda x:f'{x:.2%}' if pd.notna(x) else '未知')
    return md(g)


def run():
    checks=[]
    def ck(name,value):
        assert bool(value),name
        checks.append(name)
    receipt=json.loads((OUT/'negative_control_receipt.json').read_text())
    ck('original model replay exact and permutation prefix stable',receipt['original_q1_replay']=='PASS' and receipt['permutation_prefix']=='PASS')
    ck('negative-control scores hash matches',sha(OLD.parent/'mechanism_v32/shuffled_scores.parquet')==receipt['scores_sha256'])
    for fold in receipt['folds']:
        if fold['test']:
            ck('labels mature '+fold['quarter'],pd.Timestamp(fold['latest_label'])<pd.Timestamp(fold['quarter']))
    econ=pd.read_csv(OUT/'mechanism_economics.csv')
    v31=pd.read_csv(EXT/'v31_all_signal_economics/outputs/primary_metrics.csv').query('months==6')
    controls=econ[econ.method.isin(['accepted','capacity_matched','diffusion_matched','no_market','momentum_matched'])]
    merged=controls.merge(v31,on=['frequency','method','unit'],suffixes=('_new','_old'),validate='one_to_one')
    for c in ['signals','known_returns','mean_return','mean_excess','median_excess']:
        ck('V31 economics exactly reproduced '+c,np.allclose(merged[c+'_new'],merged[c+'_old'],equal_nan=True))
    daily=pd.read_csv(OUT/'rotation_daily_counts.csv')
    ck('rotation count bounds',daily.hit_new.le(daily.new_leaders).all() and daily.hit_future.le(daily.selected).all()
       and daily.retained.le(daily.current_leaders).all())
    cov=pd.read_csv(OUT/'rotation_coverage.csv')
    ck('future missing coverage retained',cov.known.le(cov.observations).all() and cov.fraction.lt(1).any())
    # Verify same-K selections before outcome-known filtering and fixed lockouts.
    for frequency in ['W','BW','M']:
        f=pd.read_parquet(ECON/'frames'/f'{frequency}_0.15_CSI_ALL.parquet').query("level=='L3'")
        for method in ['momentum_matched','capacity_matched','diffusion_matched']:
            ck('causal pre-outcome budget '+frequency+' '+method,
                f.groupby('date')['select_'+method].sum().equals(f.groupby('date').select_accepted.sum()))
    intervals=pd.read_csv(OUT/'mechanism_intervals.csv').query("unit=='six_month_launches'")
    rotation=pd.read_csv(OUT/'rotation_summary.csv').query('months==6')
    rotation_ci=pd.read_csv(OUT/'rotation_intervals.csv').query('months==6')
    market=pd.read_csv(OUT/'market_state_economics.csv').query("unit=='six_month_launches'")
    decisions=dict(
        market_filter='DESCRIPTIVE_RISK_COVERAGE_TRADEOFF_NOT_CAUSAL',
        diffusion_vs_same_capacity='NO_ROBUST_CROSS_FREQUENCY_INCREMENT',
        diffusion_vs_shuffled='PARTIAL_WEEKLY_BIWEEKLY_SUPPORT_SINGLE_SHUFFLE',
        leadership_persistence='NOT_SUPPORTED_BY_SIX_MONTH_RETENTION_TEST',
        new_leader_identification='BETTER_THAN_MOMENTUM_BUT_NOT_CONSISTENTLY_ABOVE_DATE_PRESERVING_PERMUTATION',
        predictable_economic_rotation='NOT_ESTABLISHED',
        strict_PIT='BLOCKED_DATA',independent_forward_validation='FORWARD_PENDING')
    js(OUT/'decision.json',decisions)
    text='''# EP32 V32：经济机制消融与行业领先更替

结论：当前筛选并未确立稳定的独立经济机制。真实扩散变量相对一次打乱行业对应关系的负对照，在周/双周有正向线索；但相对同容量无扩散模型，三种频率的收益差区间均跨零。行业领先更替存在，但6月领先留存不优于本次保留日期的置换对照，不能据此证明有规律、可预测的经济轮动。

## H1 市场环境：风险与覆盖的交换

固定去掉中证全指126日上涨过滤，其余分数阈值不变，分别运行6月首次启动计数。

'''+table(market,['frequency','method','market_up','signals','known_returns','mean_return','mean_excess','mean_max_drawdown'],['mean_return','mean_excess','mean_max_drawdown'])+'''
弱市场组也有正平均超额，但回撤更深。去掉过滤会在弱市场先启动观察段，随后强市场日期可能仍在锁定期，因此no_market的强市场子样本并不等于accepted样本。不能直接用子样本差解释市场过滤的因果贡献，也不能说弱市场没有机会。

## H2 风险结构及H3 同业扩散

风险/动量/同容量模型/扩散模型的全量对照见V31。V18容量对照和扩散模型均为240棵树、15叶、深度4；原风险树为90棵树、7叶、深度3，因此单看风险树与扩散树的差异无法排除容量影响。

本轮固定一个负对照：在同日、分类制度、层级、阈值、基准内，将11项扩散变量作为一个向量打乱与行业的对应关系，使用组身份派生seed32，不挑选seed。按原季度成熟标签规则重训同容量模型。训练数据和权重通过2021Q1原模型预测精确复现验证；2022Q1分类过渡没有观察样本，明确跳过，没有补造预测。每个组的随机顺序不受未来日期追加影响。

以下为共同日期平均6月超额收益差及12月时间块描述性区间。diffusion_matched−capacity_matched检验同容量新增特征，diffusion_matched−shuffled_matched检验真实行业对应关系，accepted−shuffled_fixed检验完整双模型门槛中替换扩散模型。

'''+table(intervals,['frequency','left','right','paired_dates','estimate','lower','upper'],['estimate','lower','upper'])+'''
只有单次打乱，不能当作置换显著性检验。多项对照及历史反复探索均未形成独立确认；个别区间为正不代表已证明龙头引领的因果机制。风险模型也未表现出跨全部简单基线稳定的6月收益优势。

## H4 行业轮动：领先者留存与新进入者

当时领先：同日同分类三级行业过去63日相对收益前20%。未来领先：可评价行业未来3或6月超额收益前20%。当前名单在删除未来缺失之前生成；未来缺失覆盖另报。未来收益前列描述一个窗口的相对表现，不代表整个窗口每天都领先，更不能解释成直接观察到资金转移。

'''+table(rotation.query("method in ['accepted','momentum_matched']"),['frequency','method','dates','active_dates','current_leader_retention','permutation_retention','future_leader_precision','new_leader_recall','permuted_new_recall'],['current_leader_retention','permutation_retention','future_leader_precision','new_leader_recall','permuted_new_recall'])+'''
retention的分母为当前领先且未来可评价的记录；new_leader_recall的分母为所有可评价新进入未来领先组的记录，包括模型未报警日期。各项是日期内计数再汇总，存在时间和行业重叠，不作为独立事件数。

当前领先组6月留存约18.5%—18.9%，本次置换约19.2%—19.9%，没有支持强领先持续性。模型对未来新领先者覆盖高于同K动量，但总体只约4%—5.5%，与保留日期的置换对照相比并非各频率更好。动量对照天然偏向当前领先者，因此超过它不足以单独证明可预测轮动。

当前模型减同K动量的新进入者召回差，按所有可评价日期（未报警为零）等权并按月时间块估计：

'''+table(rotation_ci,['frequency','months','dates','estimate','lower','upper'],['estimate','lower','upper'])+'''
这是一个相对动量的历史线索，不能把它升级为对随机日期内行业对照的稳健胜出。不同表的计数加权与日期等权不可混用。

## 执行和证据边界

两次实现失败均保留在attempts：空分类季度传入预测器，以及区间表的期限/跨度字段同名。修复均未改变候选、门槛、种子或统计规则。原实验制品不改写。基本面证据和严格PIT不足见V33；所有结果属于探索性历史研究。

[机制结果](../outputs/mechanism_economics.csv) · [机制区间](../outputs/mechanism_intervals.csv) · [轮动汇总](../outputs/rotation_summary.csv) · [逐日期计数](../outputs/rotation_daily_counts.csv) · [未来覆盖](../outputs/rotation_coverage.csv) · [模型重训收据](../outputs/negative_control_receipt.json)
'''
    (ROOT/'reports').mkdir(exist_ok=True);(ROOT/'reports/mechanism_rotation.md').write_text(text)
    js(OUT/'validation.json',dict(status='PASS',checks_count=len(checks),checks=checks))
    files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(ROOT.rglob('*'))
           if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts]
    js(OUT/'manifest.json',dict(files=files,file_count=len(files)))
    print(json.dumps(decisions,ensure_ascii=False,indent=2));print('PASS',len(checks),'checks')


if __name__=='__main__':run()
