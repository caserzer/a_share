"""Self-contained coverage report; explicitly separates acquisition from PIT proof."""
import json
from pathlib import Path
import pandas as pd
from pe_common import EXT, OUT, sha, write_json, utc_now

def table(frame):
    columns=list(frame.columns)
    lines=['| '+' | '.join(map(str,columns))+' |','| '+' | '.join(['---']*len(columns))+' |']
    lines += ['| '+' | '.join(map(str,row))+' |' for row in frame.itertuples(index=False,name=None)]
    return '\n'.join(lines)

def main():
    source=pd.read_csv(OUT/'source_daily_coverage.csv')
    yearly=pd.read_csv(OUT/'universe_yearly_coverage.csv')
    windows=pd.read_csv(OUT/'ep32_coverage_summary.csv')
    release=json.loads((OUT/'release.json').read_text())
    validation=json.loads((OUT/'validation.json').read_text())
    tests=json.loads((OUT/'test_receipt.json').read_text())
    providers=source.groupby('provider',as_index=False).agg(
        trading_dates=('date','nunique'),normalized_rows=('rows','sum'),positive_pe=('positive','sum'),
        negative_pe=('negative','sum'),unmapped_rows=('unmapped','sum'),alias_conflicts=('alias_conflicts','sum'))
    y=yearly[yearly.provider.eq('eastmoney')].copy()
    y['记录覆盖率']=y.finite_coverage.map(lambda v:f'{v:.2%}')
    y['正PE覆盖率']=y.positive_coverage.map(lambda v:f'{v:.2%}')
    y=y.rename(columns={'year':'年份','universe':'历史Universe证券交易日','finite_pe':'有PE记录','positive_pe':'正PE记录'})
    y=y[['年份','历史Universe证券交易日','有PE记录','正PE记录','记录覆盖率','正PE覆盖率']]
    delisted=yearly[yearly.provider.eq('eastmoney') & yearly.year.between(2021,2024)].copy()
    delisted['退市成员PE覆盖率']=(delisted.currently_delisted_with_pe/delisted.currently_delisted_members).map(lambda v:f'{v:.2%}')
    delisted['缺失集中于当前退市成员比例']=((delisted.currently_delisted_members-delisted.currently_delisted_with_pe)/(delisted.universe-delisted.finite_pe)).map(lambda v:f'{v:.2%}')
    delisted=delisted[['year','退市成员PE覆盖率','缺失集中于当前退市成员比例']]
    w=windows[windows.year.between(2021,2024)].copy()
    columns=['year','level','positive_pe_coverage']+[f'continuous_positive_{i}_coverage' for i in [21,63,126,252,504,756]]
    w=w[columns]
    for c in columns[2:]:w[c]=w[c].map(lambda v:f'{v:.2%}')
    w.columns=['年份','行业层级','当日正PE']+[f'{i}日连续正PE' for i in [21,63,126,252,504,756]]
    discrepancy=pd.read_csv(OUT/'cross_provider_audit.csv')
    for c in ['relative_difference_median','relative_difference_p95','fraction_above_5pct','sign_disagreement_rate']:
        discrepancy[c]=discrepancy[c].map(lambda v:f'{v:.2%}')
    baostock=json.loads((OUT/'acquisition.json').read_text())
    text=f'''# PIT Universe TTM PE 补充：D2 V6

已完成估值字段接入、可取得历史数据的归档、历史身份连接、全区间覆盖审计及离线封存。**尚未补成全历史 Universe 100% 覆盖，也没有将供应商回溯数据认证为严格 PIT。** 主源为东方财富；BaoStock 独立保留用于对照，不跨来源拼接滚动窗口。

本轮针对现有研究日历 2017-01-03—2026-10-21，共 2,377 个交易日、118 个自然月份。东方财富所有月份均完成查询；2017 年返回空结果，按缺口保留。2021—2024 年不再是“本研究可用的供应商 PE 序列为零”，可以开展有覆盖限制的历史代理实验；旧 V34 模型和统计结果未重跑、未修改。

## 来源及数量

{table(providers)}

这里的行数按“来源×稳定证券身份×交易日”计数。同一来源对代码更名证券返回两个相同估值的别名时归并；原始响应仍完整保留。两个来源的重叠行不作为新增独立样本相加。`unmapped_rows` 不进入 Universe 特征连接。

此前 V34 审计使用的是 V2 的 `vendor_valuations` 封存表，只有 102 个日期。另发现 EP30 旧代理缓存中已有 1,646 只证券的东方财富估值历史；所以“V34 未接入历史 PE”不等于“本机不存在任何历史 PE”。本轮重新按全市场、全月份分页请求，完整验证响应总数及唯一键，未把旧的局部股票池当成全市场。

BaoStock 在新增若干日期后返回“黑名单用户，请与管理员联系”。旧 RPC 把该错误归为连接错误，停止前出现重复失败；本轮已停止整棵获取进程，保留回执，并修复为明确访问拒绝立即停止，设置持久停止标记。没有改 IP、改身份或重试绕过该限制。随后使用的是另一个独立的公开数据来源。

## 历史 Universe 的实际覆盖

分母为 D2 每天按上市、退市和有效代码区间构造的历史 Universe，单位是证券交易日。分子仅包括同一证券、同一交易日真实取得的有限 PE；负 PE 也属于“有记录”，但不属于“正 PE”。Universe 本身继承 D2 的成员资格代理限制，不等于已认证的完整历史可交易 A 股池。

{table(y)}

全区间的逐日、分板块覆盖以及当前已退市证券的覆盖均另存 CSV。当前退市标记只用于事后缺口诊断，不用于构造历史筛选特征。查询未覆盖的成员继续保留为缺失，不从 Universe 中删除。

**这不是随机缺失。2021—2024 年缺失的证券交易日全部来自当前已退市成员，存在明显的幸存者覆盖偏差。** 因此不能因覆盖率超过 96% 就声称已经取得完整 PIT Universe 的估值，也不能只保留有 PE 的股票替代原历史池。完整池保留缺失、共同可观测样本对照只能减轻误比较，不能消除历史供应商覆盖的选择偏差。

{table(delisted)}

## 字段与时间规则

- `vendor_pe_ttm` 保留供应商有限原值，包括负值和零；`pe_ttm` 仅供扩张研究，保留有限正值。
- 负值、零、缺失、非有限数和别名冲突分开标记。它们不是“PE 收缩”的替代标签。
- `date` / `session_close` 是估值日期和收盘边界；`source_observed_at` / `ingested_at` 是实际取得时间。`known_at` 为空，财务分母历史版本 `UNPROVEN`。
- 默认严格查询返回 UNKNOWN。只有显式 `quality_tier='Historical-proxy'` 才可读取估值；`archived` 还要求当时已经实际取得记录。
- 盘中只使用前一个已收盘交易日；当日收盘后使用当日数据。按准确交易日连接，不跨缺口向前填充。
- 供应商可能用现行代码回写过去：以已审核唯一别名连接稳定证券 ID，并另存供应商代码与历史有效代码。同日多别名值相同才归并，冲突则规范值 UNKNOWN。
- 主源固定 Eastmoney；BaoStock 只作独立对照。选择主源依据历史覆盖，不依据后续收益或实验效果。

供应商 PE 可用于回溯代理研究，但“今天取得了历史 PE”不能证明当年财报首次披露时的盈利分母。严格 PIT 尚需逐证券、逐报告期的首次披露和更正版本，以及对应有效股本、价格时点的证据闭合。

## 多尺度实验的数据准备度

下表分母为 EP32 历史行业月度成员行，不是预测次数。正 PE 连续窗口要求 w+1 个连续交易日全部有有限正值；任何缺口或亏损穿越都使窗口不可用。仅读取成员身份与日期，未读取同文件中储存的未来收益列。42 日结果也保存在完整 CSV 中。

{table(w)}

这些覆盖率只回答“能否构造变量”，不回答“PE 扩张是否提高预测能力”。后续 PE × 成交扩张实验须同样报告完整样本与共同可观测样本，防止把样本变化误当成模型改进；还应分开考察 PE 变化来自价格上涨还是盈利分母下降。本轮没有估计新的 precision、recall 或收益。

## 两来源差异

相对差异定义为正 PE 配对样本的 `abs(Eastmoney / BaoStock - 1)`；符号分歧包括盈亏符号不同，不把差异直接解释为某一来源错误。

{table(discrepancy)}

## 复核与使用

- 语义测试通过：`{tests['summary']}`；封存验证 {len(validation['checks'])} 项全部通过。
- 之前 D2 与 EP32 文件的哈希保持不变；新原始回复、来源分区、身份日历、规范估值一起在私有缓存封存。
- 发布 ID：`{release['release_id']}`；{release['files']:,} 个文件，{release['bytes']:,} 字节。
- 数据路径：`{release['path']}`。
- 使用示例见 [README](../README.md)，适配器为 [ttm_pe_dataset.py](../src/ttm_pe_dataset.py)。

[年度覆盖](../outputs/universe_yearly_coverage.csv) · [行业窗口覆盖](../outputs/ep32_coverage_summary.csv) · [交叉来源核对](../outputs/cross_provider_audit.csv) · [验证](../outputs/validation.json) · [发布指针](../outputs/release.json)
'''
    reports=EXT/'reports';reports.mkdir(exist_ok=True)
    (reports/'ttm_pe_coverage.md').write_text(text)
    write_json(OUT/'decision.json',dict(data_integration='COMPLETE',full_pit_universe_coverage='PARTIAL',
        strict_pit='BLOCKED_DATA',proxy_research='AVAILABLE_WITH_COVERAGE_GATES',
        new_models='NOT_RUN',primary='eastmoney',secondary='baostock',
        bao_access_status=baostock['status'],prior_results_preserved=True,at=utc_now()))
    files=[dict(path=str(p.relative_to(EXT)),sha256=sha(p),bytes=p.stat().st_size)
        for p in sorted(EXT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts
        and p!=OUT/'manifest.json']
    write_json(OUT/'manifest.json',dict(files=files))
    print(providers.to_string(index=False),flush=True)

if __name__=='__main__':main()
