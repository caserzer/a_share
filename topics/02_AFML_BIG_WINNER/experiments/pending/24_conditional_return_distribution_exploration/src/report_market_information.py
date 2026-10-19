"""R17 report, input/output receipts and checks against the unchanged goal."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from build_market_breadth import DEST, FEATURES, PRICE, MACRO, BREADTH
from diagnose_prediction_target import DEST as TARGET_DIR
from prepare_panel import EP
from run_four_horizons import BINS, BIN_NAMES

LABELS = {
    'macro_price_adjustment': '指数价格概率调整',
    'macro_credit_valuation_adjustment': '追加信用与估值',
    'macro_breadth_adjustment': '再追加市场广度（半收缩）',
    'macro_breadth_full_adjustment': '市场广度（不收缩）',
    'breadth_peer_distribution': '广度近邻',
}


def run():
    contract = json.loads((TARGET_DIR / 'target_contract.json').read_text())
    fits = pd.read_csv(DEST / 'fit_audit.csv')
    assert len(fits) == 192 and not fits.duplicated(['months', 'date']).any()
    assert (pd.to_datetime(fits.last_training_label) < pd.to_datetime(fits.date)).all()
    assert fits.training_months.min() >= 12
    receipts = []
    for source in contract['files']:
        path = Path(source['path'])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source['sha256']
        b = pd.read_parquet(path); b = b[b.model == 'B']
        output = DEST / f'predictions_{source["months"]}m.parquet'
        d = pd.read_parquet(output)
        assert set(d.model) == set(LABELS)
        for model, g in d.groupby('model'):
            joined = g.merge(b[['date', 'instrument', 'actual']], on=['date', 'instrument'],
                             suffixes=('', '_base'), validate='one_to_one')
            assert len(joined) == len(g) == len(b) == 27600
            np.testing.assert_allclose(joined.actual, joined.actual_base, equal_nan=True)
        pcols = ['p_up', 'p_down', 'p_zero']; bins = [f'p_{name}' for name in BIN_NAMES]
        assert np.isfinite(d[pcols + bins]).all().all()
        assert (d[pcols + bins] >= -1e-12).all().all()
        np.testing.assert_allclose(d[pcols].sum(axis=1), 1, atol=1e-10)
        np.testing.assert_allclose(d[bins].sum(axis=1), 1, atol=1e-10)
        observed = d.actual.notna()
        np.testing.assert_allclose(d.loc[observed, 'brier'], (d.loc[observed, 'p_up'] - (d.loc[observed, 'actual'] > 0))**2)
        expected = ((d.loc[observed, bins].to_numpy() - np.eye(5)[np.searchsorted(BINS, d.loc[observed, 'actual'], side='right')])**2).sum(axis=1)
        np.testing.assert_allclose(d.loc[observed, 'multiclass_brier'], expected)
        assert d.loc[~observed, ['brier', 'multiclass_brier', 'crps']].isna().all().all()
        assert (d.q05 <= d.q50).all() and (d.q50 <= d.q95).all()
        receipts.append(dict(path=str(output.relative_to(EP)), sha256=hashlib.sha256(output.read_bytes()).hexdigest(), rows=len(d)))
    features = pd.read_parquet(FEATURES)
    assert not features.loc['2021':, PRICE + MACRO + BREADTH].isna().any().any()
    board = pd.read_csv(DEST / 'target_scoreboard.csv')
    assert len(board) == 60
    decisions = []
    for model, g in board.groupby('model'):
        assert len(g) == 12 and set(g.months) == {1, 3, 6}
        decisions.append(dict(model=model, all_point_targets_met=bool(g.point_target_met.all()),
                              all_confidence_targets_met=bool(g.confidence_target_met.all())))
    audit = dict(technical_integrity_passed=True, goal_achieved=False, goal_status='active',
        candidate_count=5, point_gates_passed=int(board.point_target_met.sum()), total_point_gates=60,
        candidates=decisions, outputs=receipts,
        feature_sha256=hashlib.sha256(FEATURES.read_bytes()).hexdigest(),
        baseline_contract_sha256=hashlib.sha256((TARGET_DIR / 'target_contract.json').read_bytes()).hexdigest(),
        evidence='retrospective repeated exploration, not independent holdout validation')
    (DEST / 'research_integrity_audit.json').write_text(json.dumps(audit, indent=2) + '\n')

    lines = ['# R17：市场广度、信用与估值状态', '',
        '**5个新增方法均未达到双20%目标。与R16合计测试20个候选，目标仍未完成。** 原基线、同样本和每期限验收标准保持不变。', '',
        '## 新信息与方法', '',
        '使用历史每月500只股票成员的过去上涨比例、站上20日均线比例、动量分散程度、波动、规模集中度与估值分布。2021年起每月63日广度有效覆盖至少487只，估值覆盖500只；这些是原股票池状态代理，不是全市场广度。原股票池历史ST筛选偏差未解决。', '',
        '先用已到期训练月份的七类实际涨跌比例拟合正则化多分类模型，每月总训练权重为1，避免把一个市场月份误当成几百个独立市场环境。然后调整B的完整分布：指数信息、追加信用估值、再追加广度三个版本均保留50%B权重；另有无收缩敏感性和直接广度近邻对照。', '',
        '所有训练标签终点严格早于预测日期，归一化只看训练数据。每期限仍为27,600股票月、64预测月；原始标签截止2026-05-29。12个月未执行本轮新增比较，仍不能声称四期限20%目标完成。', '',
        '## 全部结果', '',
        '表中均为相对原B的改善百分比，正数较好、负数变差。每一行四项都≥20%才满足该期限的点估计目标；一个方法必须三个期限均达标。', '',
        '| 期限 | 方法 | 上涨Brier改善 | 五档Brier改善 | CRPS改善 | 命中率改善 |',
        '|---|---|---|---|---|---|']
    for h in [1, 3, 6]:
        for model, label in LABELS.items():
            g = board[(board.months == h) & (board.model == model)].set_index('metric')
            fields = [f'{g.loc[m,"relative_improvement"]*100:+.2f}%' for m in ['brier', 'multiclass_brier', 'crps', 'accuracy']]
            lines.append(f'| {h}个月 | {label} | ' + ' | '.join(fields) + ' |')
    lines += ['',
        '1个月不收缩广度模型的命中率51.98%→55.86%，相对提高7.47%，上涨Brier降低1.32%，但五档仅降低0.16%、CRPS降低0.74%。同一模型3个月命中率略差，6个月全部指标变差。半收缩广度模型1/3个月概率评分略好，6个月变差；没有稳定跨期限优势。', '',
        '## 盈利预期数据核验', '',
        '业绩预告：对603313的2025年报，两个公开表分别返回2行（归母/扣非）和1行，公告日期均为2026-04-29。修正说明提到2026-01-31的原始预告，但没有返回该原始版本。因此本轮不把这些当前查询结果当成可完整回放的历史预告面板。这是具体接口与样本的限制，不推断所有公开数据都不可用。原响应和哈希已保存。', '',
        '券商原始研报：找到一个可核验的积极线索。民生证券2019-10-30浦发银行原报告包含2019/2020/2021年的每股收益预测2.13/2.43/2.87元；列表发布日期为2019-10-31，应采用较晚日期作为保守可用时点。抽查列表中的5份旧报告，其结构化EPS字段均为空，不能把接口的当前年份标签套给历史预测。[原始研报，第1页](https://pdf.dfcfw.com/pdf/H3_AP201910311370071887_1.pdf?1574411299000.pdf=)。', '',
        '原PDF内容可由网页检索核验，但直接下载返回JavaScript挑战页面而非PDF，已记录响应；目前只有一个经核验的示例，尚无批量历史预测面板，更没有一致预期模型结果。该示例没有加入本轮预测或评分。下一步可以验证标准浏览器下载及不同券商预测表的年份提取，先建立可审计的小样本，再检验全样本覆盖。', '',
        '报告数据：[全部目标评分](outputs/r17_market_information/target_scoreboard.csv)、[分阶段成绩](outputs/r17_market_information/phase_scores.csv)、[技术核验](outputs/r17_market_information/research_integrity_audit.json)、[预告版本探测](outputs/r17_market_information/earnings_vintage_probe.json)、[原始研报预测示例](outputs/r17_market_information/historical_analyst_forecast_example.json)。', '',
        '本轮仍为重复查看历史数据后的探索，时间块置信区间也不能替代独立新增验证。技术核验不代表预测有效，更不能代替20%目标。', '']
    (EP / 'market_information_report.md').write_text('\n'.join(lines))
    print(json.dumps({k: v for k, v in audit.items() if k not in ['outputs', 'candidates']}, indent=2))


if __name__ == '__main__':
    run()
