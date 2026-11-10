"""Audit overlapping V29 phase definitions without changing accepted signals.

Merge connected overlapping closed intervals within the same classification,
level, industry and continuous price block. Groups describe captured historical
episodes, not independently validated cycles or cross-level independent trades.
"""
from pathlib import Path
import hashlib
import json

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PREV = ROOT.parent / 'v29_signal_to_peak'
OUT = ROOT / 'outputs'
KEY = ['era', 'level', 'industry_code', 'block']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2,
                               allow_nan=False, default=str) + '\n')


def partition(frame):
    """Connected interval components, including touching intervals."""
    groups = []
    for _, industry in frame.groupby(KEY):
        current = []
        end = None
        for index, row in industry.sort_values(['start_date', 'peak_date']).iterrows():
            if current and row.start_date > end:
                groups.append(current)
                current = []
            current.append(index)
            end = row.peak_date if len(current) == 1 else max(end, row.peak_date)
        if current:
            groups.append(current)
    return groups


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    checks = []

    def check(name, condition):
        assert bool(condition), name
        checks.append(name)

    manifest_path = PREV / 'outputs/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    frozen = {PREV / f['path']: f['sha256'] for f in manifest['files']}
    frozen[manifest_path] = sha(manifest_path)
    check('V29 frozen files unchanged', all(sha(p) == value for p, value in frozen.items()))
    source = PREV / 'outputs/unique_cycle_outcomes.csv.gz'
    data = pd.read_csv(source, parse_dates=['date', 'start_date', 'peak_date'])
    check('original 341 exact-boundary records', len(data) == 341)
    groups = partition(data)
    check('partition contains each input exactly once', sorted(i for g in groups for i in g) == sorted(data.index))
    rows = []
    members = []
    for n, indexes in enumerate(groups):
        g = data.loc[indexes]
        component = f'overlap_{n:04d}'
        rows.append(dict(component=component, **{k: g.iloc[0][k] for k in KEY},
                         industry_name=g.industry_name.iloc[0], first_signal=g.date.min(),
                         union_start=g.start_date.min(), union_end=g.peak_date.max(),
                         source_records=len(g), source_years=','.join(map(str, sorted(g.date.dt.year.unique())))))
        members.append(g.assign(component=component))
    result = pd.DataFrame(rows)
    result['year'] = result.first_signal.dt.year
    detail = pd.concat(members, ignore_index=True)
    # A separate pairwise graph computation checks the sorted interval sweep.
    independent = []
    for _, g in data.groupby(KEY):
        remaining = set(g.index)
        while remaining:
            found = {remaining.pop()}
            pending = list(found)
            while pending:
                i = pending.pop()
                neighbours = {j for j in remaining if
                              g.loc[i, 'start_date'] <= g.loc[j, 'peak_date'] and
                              g.loc[j, 'start_date'] <= g.loc[i, 'peak_date']}
                remaining -= neighbours
                found |= neighbours
                pending.extend(neighbours)
            independent.append(frozenset(found))
    check('interval sweep matches independent overlap graph',
          set(map(frozenset, groups)) == set(independent))
    for _, g in result.groupby(KEY):
        g = g.sort_values('union_start')
        check('no overlap remains ' + str(tuple(g.iloc[0][KEY])),
              all(g.union_start.iloc[i] > g.union_end.iloc[i - 1] for i in range(1, len(g))))
    check('no classification level or industry crossed',
          all(g[KEY].drop_duplicates().shape[0] == 1 for _, g in detail.groupby('component')))
    annual = result.groupby(['year', 'level']).size().unstack(fill_value=0).reset_index()
    annual['total_groups_not_independent'] = annual.L2 + annual.L3
    annual['old_exact_boundary_records'] = annual.year.map(data.groupby(data.date.dt.year).size())
    original_three_years = int(data.date.dt.year.le(2023).sum())
    three = result[result.year.le(2023)]
    three_counts = three.groupby('level').size().to_dict()
    counts = dict(original_records=len(data), overlap_groups=len(result),
                  removed_repeated_records=len(data) - len(result),
                  groups_with_multiple_records=int(result.source_records.gt(1).sum()),
                  original_2021_2023_records=original_three_years,
                  groups_2021_2023=len(three), by_level_2021_2023=three_counts,
                  groups_over_18_months=int(result.union_end.gt(result.union_start + pd.DateOffset(months=18)).sum()),
                  cross_level_deduplicated=False, independent_opportunities=False)
    result.to_csv(OUT / 'overlap_groups.csv', index=False)
    detail.to_csv(OUT / 'source_to_group.csv.gz', index=False, compression={'method': 'gzip', 'mtime': 0})
    annual.to_csv(OUT / 'annual_counts.csv', index=False)
    write_json(OUT / 'counts.json', counts)
    write_json(OUT / 'input_receipt.json', dict(source=str(source), sha256=sha(source),
                                              predecessor_manifest_sha256=sha(manifest_path)))
    annual_table = '|首次信号年份|原起止精确去重记录|重叠合并后二级|重叠合并后三级|两层记录之和（非独立）|\n|---|---:|---:|---:|---:|\n'
    for row in annual.itertuples():
        annual_table += f'|{row.year}|{row.old_exact_boundary_records}|{row.L2}|{row.L3}|{row.total_groups_not_independent}|\n'
    report = f'''# EP32 V30：同一行业重叠周期计数更正

用户质疑成立。V29只合并相同分类、层级、行业、价格块及完全相同起止日期的记录；同一行业不同阈值识别出的重叠阶段仍重复加权。此前将三年236条描述为236次行业周期不够严谨，应更正。

## 本次审计口径

在同一分类版本、行业层级、行业代码、连续价格块内，将起点至峰值的闭区间有重叠或相接的阶段合并，传递性重叠亦合并。完整样本先合并，再按该组最早正确报警年份归属，避免跨年重复。每组只计一次，不跨分类或数据缺口拼接，不合并不同二级或三级行业。此处称重叠行情组，不重新宣称它们是唯一正确的经济周期定义。

{annual_table}

2021—2023三年由{original_three_years}条降为{len(three)}组，减少{original_three_years-len(three)}条。二级{three_counts['L2']}组，三级{three_counts['L3']}组。2021—2024年9月完整观察样本由{len(data)}条降为{len(result)}组，{counts['groups_with_multiple_records']}组包含多个原记录。本样本合并组没有超过18个月；合并规则本身不以满足6—18个月为目的，也不改变原标签。

2023年的部分记录与2022年首次报警的行情相重叠，合并后归属2022年。因此年度减少量不仅来自本年内部重复。

## 两种重复必须区分

本次去掉同一行业代码内的重叠阶段。例如二级贵金属的2024-09-12起点，在15%阈值下峰值为2025-10-13、20%阈值下为2026-01-29，V29计两条，此处合并为一组。

仍有二级与三级上下级重叠，不能把{len(three)}组称为{len(three)}个独立投资机会。例如SW2014的黄金在二级、三级均有2021-02-05至2021-09-13的阶段，信号日同为2021-03-26。此处应分别报告二级与三级；没有以共同市场日期为依据把所有行业合并，也没有完成成员暴露去重。

## 对既有结果的影响

V29的41.05%平均涨幅、31.87%中位涨幅仍是其341条精确起止记录的描述，存在重叠行情重复加权，不能称独立周期统计。本次仅更正计数，不通过选择合并组中最高涨幅来改写收益。若要给出唯一行业周期收益，需要先固定单一层级和阶段定义，或另行明确合并后峰值规则。

V28的precision与recall分别在36项任务内计算，每任务每周期检出仅计一次；本次发现的是跨任务汇总后的去重不足，不直接修改原任务指标，也不将原周期recall当作去重后独立机会recall。

仍只覆盖成功捕捉的已知正例；误报和未知没有消失。严格PIT BLOCKED_DATA，独立前瞻FORWARD_PENDING。原V29文件和哈希保留。

[年度计数](../outputs/annual_counts.csv) · [重叠组](../outputs/overlap_groups.csv) · [原记录到重叠组映射](../outputs/source_to_group.csv.gz)
'''
    (ROOT / 'reports').mkdir(exist_ok=True)
    (ROOT / 'reports/count_correction.md').write_text(report)
    check('original files preserved after audit', all(sha(p) == value for p, value in frozen.items()))
    write_json(OUT / 'validation.json', dict(status='PASS', checks_count=len(checks), checks=checks))
    files = [dict(path=str(p.relative_to(ROOT)), sha256=sha(p), bytes=p.stat().st_size)
             for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name != 'manifest.json' and '__pycache__' not in p.parts]
    write_json(OUT / 'manifest.json', dict(files=files, file_count=len(files)))
    print(json.dumps(counts, ensure_ascii=False, indent=2))
    print(annual.to_string(index=False))
    print('PASS', len(checks), 'checks')


if __name__ == '__main__':
    main()
