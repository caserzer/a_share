"""Publish the current example with its credibility judgment adjacent to the probabilities."""
import json
from pathlib import Path
from run_four_horizons import EP, OUT, BIN_NAMES


def report():
    path=OUT/'current/SH600000_2026-10-19.json'
    d=json.loads(path.read_text())
    lines=['# 当前时点概率示例与可信度判断','',
        '**判断：尚未证明可信，只是探索性模型输出。** 示例股票为浦发银行 SH600000，信息时点2026-10-19收盘后。没有据此形成交易或仓位建议。','',
        '模型仅使用当日已知的63交易日年化波动率和总市值。行情与市值来自公开腾讯及东方财富接口，日期一致；历史交叠60日的最大单日收益差约0.174个百分点，作为源变动限制保留。','',
        '|期限|上涨|下跌|跌超20%|跌5%—20%|接近平盘|涨5%—20%|涨至少20%|','|---|---|---|---|---|---|---|---|']
    for h in d['horizons']:
        values=[h['p_up'],h['p_down']]+[h[f'p_{n}'] for n in BIN_NAMES]
        lines.append('|'+str(h['months'])+'个月|'+'|'.join(f'{v:.1%}' for v in values)+'|')
    lines+=['','上涨为R>0、下跌为R<0；严格平盘概率另列JSON，本示例为0。“接近平盘”是[-5%,5%)，包括小涨与小跌，因此五档与方向是两种不同汇总，不能把它们合并求和。完整分布保存为200等权原子。收益口径为前复权价格变化代理，不是已核验的含税分红再投资总收益。','',
        '## 为什么尚未证明可信','',
        '- 四期限方向概率尚未稳定优于简单历史分布。1/3个月的幅度分布有局部改善，不能替代上涨概率准确性。',
        '- 概率组校准是跨股票、跨历史月份的证据，不能保证单只股票这一次预测正确。每个方向和区间均附样本数、月份数、实际频率、时间块误差区间及缺失结果上下界。',
        '- 当前特征已更新到10月19日，但训练标签面板仍截止5月29日；本次按当前日期重训，历史验证则是月末预测、季度重训。因此当前应用范围尚未验证。',
        '- 历史股票池、可用财报与公司行动口径仍有缺口。没有检出显著校准误差不等于证明概率准确。','',
        '## 逐期限的局部证据','',
        '|期限|事件|本次概率|历史同概率组：预测 / 实际|已观测样本 / 月份|判断|','|---|---|---|---|---|---|']
    names={'up':'上涨','down':'下跌','zero':'严格平盘','loss_over20':'跌超20%','gain_over20':'涨至少20%'}
    statuses={'insufficient_evidence':'证据不足','miscalibrated':'检出校准偏差','not_rejected_not_proven':'未检出偏差，未证明可信'}
    for h in d['horizons']:
        for e in h['credibility']['events']:
            if e['event'] not in names:continue
            actual=f"{e['historical_predicted']:.1%} / {e['historical_observed']:.1%}" if 'historical_observed' in e else '无'
            lines.append(f"|{h['months']}个月|{names[e['event']]}|{e['predicted_probability']:.1%}|{actual}|{e['observed_rows']} / {e['prediction_months']}|{statuses[e['status']]}|")
    lines+=['','## 复跑','',
        '从主题目录运行：','', '```bash',
        'EP=experiments/pending/24_conditional_return_distribution_exploration',
        '.venv/bin/python "$EP/src/fetch_current_snapshot.py" --stock SH600000 --asof 2026-10-19',
        '.venv/bin/python "$EP/src/predict_from_snapshot.py" --snapshot "$EP/outputs/local_cache/current_snapshots/SH600000_2026-10-19/snapshot.json" --output "$EP/outputs/current/SH600000_2026-10-19.json"',
        '```','',
        '公开数据日期缺失、价格不一致、特征不可用或时间戳晚于预测时点时明确报错，不悄悄使用旧报价。该当前快照入口不承诺恢复历史原始版本；旧日期研究使用已保存的历史预测。', '',
        '[完整概率及证据JSON](outputs/current/SH600000_2026-10-19.json) · [四期限回溯报告](probability_research_report.md)']
    (EP/'current_probability_example.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':report()
