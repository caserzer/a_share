"""R18 evidence summary; technical success never substitutes for the 20% goal."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from prepare_panel import EP, OUT
from fetch_historical_reports import DEST
from build_analyst_features import PANEL
from diagnose_prediction_target import DEST as TARGET_DIR
from run_four_horizons import BIN_NAMES

LABELS={'analyst_attention_peers':'评级与关注度近邻','analyst_target_peers':'目标价上行空间近邻',
        'analyst_full_peers':'完整分析师信息近邻','analyst_target_classes':'分析师信息浅层分类'}


def run():
    source=json.loads((DEST/'fetch_audit.json').read_text())
    assert {r['year'] for r in source if r['status']=='complete'}==set(range(2018,2027))
    fit=pd.read_csv(DEST/'fit_audit.csv')
    assert len(fit)==768 and not fit.duplicated(['months','date','model']).any()
    assert (pd.to_datetime(fit.last_training_label)<pd.to_datetime(fit.date)).all()
    assert (fit.adjusted_rows+fit.fallback_rows==fit.predicted_rows).all()
    panel=pd.read_parquet(PANEL)
    features=panel[panel.common_eligible&(panel.date>='2021-01-01')]
    assert len(features)==27600
    for col in ['latest_analyst_date','latest_target_date']:
        assert (features[col].isna()|(features[col]<features.date)).all()
    contract=json.loads((TARGET_DIR/'target_contract.json').read_text())
    receipts=[]
    for item in contract['files']:
        basepath=Path(item['path']);assert hashlib.sha256(basepath.read_bytes()).hexdigest()==item['sha256']
        base=pd.read_parquet(basepath);base=base[base.model=='B']
        path=DEST/f'predictions_{item["months"]}m.parquet';d=pd.read_parquet(path)
        assert set(d.model)==set(LABELS)
        for model,g in d.groupby('model'):
            joined=g.merge(base,on=['date','instrument'],suffixes=('','_base'),validate='one_to_one')
            assert len(joined)==len(g)==27600
            np.testing.assert_allclose(joined.actual,joined.actual_base,equal_nan=True)
            availability='analyst_available' if model=='analyst_attention_peers' else 'target_available'
            joined=joined.merge(features[['date','instrument',availability]],on=['date','instrument'],validate='one_to_one')
            trained=fit[(fit.months==item['months'])&(fit.model==model)].set_index('date').training_rows
            fallback=(~joined[availability])|(joined.date.dt.strftime('%Y-%m-%d').map(trained)<1000)
            numeric=['p_up','p_down','p_zero','brier','multiclass_brier','crps','q05','q50','q95','mean']+[f'p_{x}' for x in BIN_NAMES]
            np.testing.assert_array_equal(joined.loc[fallback,numeric].to_numpy(),joined.loc[fallback,[f'{x}_base' for x in numeric]].to_numpy())
        cols=['p_up','p_down','p_zero'];bins=[f'p_{x}' for x in BIN_NAMES]
        assert np.isfinite(d[cols+bins]).all().all() and (d[cols+bins]>=0).all().all()
        np.testing.assert_allclose(d[cols].sum(axis=1),1,atol=1e-10)
        np.testing.assert_allclose(d[bins].sum(axis=1),1,atol=1e-10)
        observed=d.actual.notna()
        np.testing.assert_allclose(d.loc[observed,'brier'],(d.loc[observed,'p_up']-(d.loc[observed,'actual']>0))**2)
        assert d.loc[~observed,['brier','multiclass_brier','crps']].isna().all().all()
        receipts.append(dict(path=str(path.relative_to(EP)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    score=pd.read_csv(DEST/'target_scoreboard.csv');assert len(score)==48
    decisions=score.groupby('model').point_target_met.all().to_dict()
    audit=dict(technical_integrity_passed=True,goal_achieved=False,goal_status='active',
        candidates_passing_all_point_gates=decisions,passed_point_gates=int(score.point_target_met.sum()),
        candidate_count=4,source_reports=sum(r['rows'] for r in source),prediction_rows_per_model=27600,
        unchanged_fallback_verified=True,receipts=receipts,
        feature_sha256=hashlib.sha256(PANEL.read_bytes()).hexdigest(),
        evidence='Repeated retrospective exploration; no independent holdout. Public metadata is not a complete immutable consensus history.')
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    fa=json.loads((DEST/'feature_audit.json').read_text())
    result='尚无方法达到原定双20%目标。' if not any(decisions.values()) else '有方法通过历史点估计门槛，尚未完成独立证据审核，不能宣布目标完成。'
    lines=['# R18：公开历史分析师预期实验','',f'**{result}** 本轮新增4个候选，继续固定R15 B、相同股票月及1/3/6个月期限；累计候选24个。','',
        '## 实际新增的数据','',
        f'完整读取2018年至2026-05-29的{audit["source_reports"]:,}份公开个股研报记录，原始分页与哈希保存在缓存。包含发布日期、机构、历史评级及部分目标价；没有使用接口按当前年份命名的EPS、当前行业或当前近一月研报数。', '',
        f'原27,600股票月中，180日内研报信息覆盖{fa["covered_analyst_rows"]:,}条（{fa["covered_analyst_rows"]/27600:.1%}），有效目标价覆盖{fa["covered_target_rows"]:,}条（{fa["covered_target_rows"]/27600:.1%}）。以下为逐年覆盖：','',
        '| 年份 | 原股票月 | 有研报信息 | 有有效目标价 |','|---|---|---|---|']
    coverage=pd.read_csv(DEST/'feature_coverage.csv')
    for r in coverage.itertuples(index=False):
        lines.append(f'| {r[0]} | {r.rows} | {r.analyst_available/r.rows:.1%} | {r.target_available/r.rows:.1%} |')
    lines+=['','目标价按报告发布前已知原始/复权价格转换至当前单位，再计算相对上行空间，避免把拆股前目标价直接除以拆股后价格。已知无法解释的复权事件区间不使用目标价。每家机构仅保留180日内最新报告；报告日期必须严格早于决策日期。','',
        '“分析师预期”是本公开来源中的目标价、评级、覆盖和分歧信息，不是已完成的EPS一致预期面板。不同机构的目标价期限可能不同，这里只将它们作为输入特征，不当作1/3/6个月标签。','',
        '## 同样本实验结果','',
        '三个近邻版本分别加入评级关注度、目标价上行空间、全部分析师因子；另一个固定浅层多类别模型学习分析师信息。可用部分均与原B完整分布各混合50%；不可用或训练不足1000行时逐值回退原B。原测试股票月没有删除。','',
        '| 期限 | 方法 | 上涨Brier改善 | 五档Brier改善 | CRPS改善 | 命中率相对改善 |','|---|---|---|---|---|---|']
    for h in [1,3,6]:
        for model,label in LABELS.items():
            g=score[(score.months==h)&(score.model==model)].set_index('metric')
            vals=[f'{g.loc[m,"relative_improvement"]*100:+.2f}%' for m in ['brier','multiclass_brier','crps','accuracy']]
            lines.append(f'| {h}个月 | {label} | '+' | '.join(vals)+' |')
    ceiling=pd.read_csv(DEST/'coverage_ceiling_oracle_only.csv')
    impossible=ceiling[(ceiling.coverage=='target_available')&(~ceiling.twenty_percent_possible_under_ceiling)]
    lines+=['','正数是改善，负数是变差；一个方法需要三个期限的全部四项都至少改善20%。原始评分与分阶段结果一并保存，未将不同方法的最好指标拼接。','',
        '## 覆盖限制与证据边界','',
        '另计算了覆盖带来的理论上限：假设有数据的行预测完全正确、其余保持B。它使用实际结果，仅用于判断这类回退结构是否可能达到20%，绝不能当作模型成绩。']
    if len(impossible):
        lines.append('目标价覆盖结构下，即便这个不可实现的完美假设也无法过线的项目为：'+ '；'.join(f'{r.months}个月 {r.metric} 最多改善{r.relative_improvement_ceiling:.1%}' for r in impossible.itertuples())+'。')
    else:
        lines.append('这一乐观上限未排除20%的数学可能，但完全不代表实际可达到；真实成绩仍以上表为准。')
    lines+=['',
        '三个目标价样例与原报告核对一致：浦发银行2019年、贵州茅台2020年、宁德时代2023年。抽查只能证明这三个样例一致，不能证明全部记录具有不可修改的历史版本。原股票池ST偏差、复权代理限制及多次历史探索偏差仍存在。', '',
        '原EPS读取：独立临时Chrome的直接访问和先访问站点首页两种方式仍未取得原PDF字节；网页检索可核验个别报告，但批量提取尚未完成。因此没有把EPS因子接入成功或称作预测改善。', '',
        '进一步验证发现，公开研报原始HTML正文可以直接读取：贵州茅台2020-10-29报告明确给出2020/2021/2022年EPS预测36.93/49.61/60.66元。只取原文正文，排除页面当前行情及2026年的网页缓存时间。该单例记录在`html_eps_feasibility.json`，尚未用于任何预测。下一轮可先验证不同机构的年份/数值解析及覆盖，再测试原始盈利预期的增量。', '',
        '明细：[目标评分](outputs/r18_analyst_expectations/target_scoreboard.csv)、[分阶段](outputs/r18_analyst_expectations/phase_scores.csv)、[覆盖理论上限](outputs/r18_analyst_expectations/coverage_ceiling_oracle_only.csv)、[目标价原文抽查](outputs/r18_analyst_expectations/target_vintage_spotcheck.json)、[技术核验](outputs/r18_analyst_expectations/research_integrity_audit.json)。', '',
        '原文：[贵州茅台报告](https://data.eastmoney.com/report/info/AP202010291424614577.html)、[宁德时代原PDF](https://pdf.dfcfw.com/pdf/H3_AP202310201602156909_1.PDF)。技术核验只验证流程和样本，不替代预测有效性或双20%目标。','']
    (EP/'analyst_expectations_report.md').write_text('\n'.join(lines))
    print(json.dumps({k:v for k,v in audit.items() if k!='receipts'},indent=2))


if __name__=='__main__':run()
