"""Expose every catalog industry, including unobservable and zero-candidate groups.

Read-only presentation of V4, with no stage re-detection or outcome selection.
"""
from pathlib import Path
import hashlib
import json
import re

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EP = ROOT.parents[1]
V4 = ROOT.parent / 'v4_adaptive_6_18_months'
CACHE = Path.home() / '.cache/a_share/ep32'
KEY = ['era', 'level', 'industry_code']
THRESHOLDS = [.10, .15, .20]
BENCHMARKS = ['CSI300', 'CSI_ALL']


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_json(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def table(frame):
    return ('|' + '|'.join(frame.columns) + '|\n|' + '|'.join(['---'] * len(frame.columns)) +
            '|\n' + '\n'.join('|' + '|'.join(map(str, row)) + '|'
                              for row in frame.itertuples(index=False, name=None)) + '\n')


def main():
    out = ROOT / 'outputs'
    reports = ROOT / 'reports'
    out.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    inputs = {}
    checks = []

    def check(name, condition):
        assert bool(condition), name
        checks.append(name)

    def read(p):
        inputs[str(p)] = sha(p)
        return pd.read_parquet(p) if p.suffix == '.parquet' else pd.read_csv(p)

    predecessors = []
    for root in [EP, ROOT.parent / 'v2_full_history_benchmark',
                 ROOT.parent / 'v3_screening_review', V4]:
        p = root / 'outputs/manifest.json'
        inputs[str(p)] = sha(p)
        manifest = json.loads(p.read_text())
        check(root.name + ' original manifest', all(sha(root / x['path']) == x['sha256']
                                                   for x in manifest['files']))
        predecessors.extend((root / x['path'], x['sha256']) for x in manifest['files'])

    catalogs = [read(CACHE / 'extension_v2/sources/legacy_catalog.parquet')]
    catalogs += [read(CACHE / f'industry_v1/{level}.parquet') for level in ['L2', 'L3']]
    catalog = pd.concat(catalogs, ignore_index=True)
    catalog = catalog[['src', 'level', 'index_code', 'industry_name']].rename(
        columns={'src': 'era', 'index_code': 'industry_code'}).sort_values(KEY)
    check('complete catalog 331 old + 480 new', len(catalog) == 811 and not catalog.duplicated(KEY).any())
    monthly = read(V4 / 'outputs/details/industry_monthly_returns.csv.gz')
    # Provider membership codes can disagree with index_classify. Preserve both
    # identities rather than silently dropping observed paths or merging by name.
    catalog['identity_source'] = 'CATALOG'
    extra = monthly[KEY + ['industry_name']].drop_duplicates().merge(
        catalog[KEY], on=KEY, how='left', indicator=True)
    extra = extra[extra._merge.eq('left_only')].drop(columns='_merge')
    extra['identity_source'] = 'MEMBERSHIP_ONLY_CODE'
    catalog = pd.concat([catalog, extra], ignore_index=True).sort_values(KEY)
    check('membership-only codes preserved without name-based merge',
          len(catalog) == 812 and len(extra) == 1 and extra.industry_code.iloc[0] == '850412.SI')
    paths = read(V4 / 'outputs/details/industry_price_paths.csv.gz')
    phases = read(V4 / 'outputs/details/all_natural_stages.csv.gz')
    scores = pd.concat([read(V4 / f'outputs/details/stage_scores_T{t}.csv.gz')
                        for t in [10, 15, 20]], ignore_index=True)
    scores = scores[scores.policy.eq('EXACT')].copy()
    existing = read(V4 / 'outputs/metrics/candidate_summary.csv')
    existing = existing[existing.policy.eq('EXACT')]
    check('every phase has both benchmark rows', len(scores) == 2 * len(phases)
          and not scores.duplicated(['phase_id', 'benchmark']).any())
    check('all observed industries belong to catalog',
          monthly.merge(catalog[KEY], on=KEY, how='left', indicator=True)._merge.eq('both').all())
    groups = {k: g for k, g in monthly.groupby(KEY)}
    pgroup = {k: g for k, g in paths.groupby(KEY)}
    sgroup = {k: g for k, g in scores.groupby(KEY + ['threshold', 'benchmark'])}
    coverage, summaries = [], []
    for row in catalog.to_dict('records'):
        key = tuple(row[k] for k in KEY)
        g = groups.get(key, monthly.iloc[:0])
        p = pgroup.get(key, paths.iloc[:0])
        valid = g[g.return_value.notna()]
        status = ('NO_ASSIGNED_MEMBER_MONTHS' if g.empty else
                  'NO_VALID_PRICE_PATH' if p.empty else 'OBSERVABLE')
        cov = dict(row, coverage_status=status, assigned_return_months=len(g),
                   valid_return_months=len(valid), full_return_months=int((~valid.is_partial).sum()),
                   partial_return_months=int(valid.is_partial.sum()),
                   months_below5_members=int(g.members.lt(5).sum()),
                   months_below80pct_coverage=int(g.coverage.lt(.8).sum()),
                   price_blocks=int(p.block.nunique()),
                   first_price_date=None if p.empty else p.date.min(),
                   last_price_date=None if p.empty else p.date.max())
        coverage.append(cov)
        for threshold in THRESHOLDS:
            for benchmark in BENCHMARKS:
                s = sgroup.get((*key, threshold, benchmark), scores.iloc[:0])
                complete = s[s.phase_status.eq('CONFIRMED') & ~s.left_censored]
                bounded = complete[complete.duration_months.between(6, 18)]
                c = s[s.primary_stage]
                known = c[c.complete]
                success = int(known.all_positive_and_beat.eq(True).sum())
                result_status = (status if status != 'OBSERVABLE' else
                                 'NO_DETECTED_STAGE' if s.empty else
                                 'NO_QUALIFYING_STAGE' if c.empty else
                                 'TOP3_ALL_UNKNOWN' if known.empty else 'CANDIDATES_WITH_KNOWN_TOP3')
                summaries.append(dict(row, threshold=threshold, benchmark=benchmark,
                    coverage_status=status, result_status=result_status, natural_stages=len(s),
                    confirmed_known_start=len(complete), short_lt6=int(complete.duration_months.lt(6).sum()),
                    completed_6_18=len(bounded), long_gt18=int(complete.duration_months.gt(18).sum()),
                    open_stages=int(s.right_censored.sum()), left_censored=int(s.left_censored.sum()),
                    candidates=len(c), rank_known=int(c.rank_complete.sum()), endpoint_known=len(known),
                    endpoint_unknown=len(c)-len(known), all_three_successes=success,
                    all_three_success_rate=success/len(known) if len(known) else np.nan,
                    median_duration=c.duration_months.median(), median_industry_excess=c.industry_excess.median(),
                    median_portfolio_return=known.portfolio_return.median(),
                    median_portfolio_excess=known.portfolio_excess.median(),
                    median_worst_stock_excess=known.worst_stock_excess.median()))
    coverage = pd.DataFrame(coverage)
    summary = pd.DataFrame(summaries)
    check('all catalog and membership-only industries retained in all six comparisons', len(summary) == 812 * 6)
    check('unknown top3 never counted as failure',
          (summary.endpoint_known + summary.endpoint_unknown).eq(summary.candidates).all())
    check('unobservable industries have no invented return or success rate',
          summary.loc[summary.coverage_status.ne('OBSERVABLE'),
                      ['median_portfolio_return', 'all_three_success_rate']].isna().all().all())
    for old in existing.itertuples():
        g = summary[(summary.threshold == old.threshold) & (summary.level == old.level)
                    & (summary.benchmark == old.benchmark)]
        check(f'V4 denominator reconciliation {old.threshold} {old.level} {old.benchmark}',
              g.candidates.sum() == old.industry_candidate_stages and
              g.endpoint_known.sum() == old.endpoint_known and g.endpoint_unknown.sum() == old.unknown)
    coverage.to_csv(out / 'industry_coverage.csv', index=False, encoding='utf-8-sig')
    summary.to_csv(out / 'industry_summary.csv', index=False, encoding='utf-8-sig')
    coverage_counts = []
    links = []
    for (era, level), group in coverage.groupby(['era', 'level']):
        tag = f'{era}_{level}'
        s = scores[scores.era.eq(era) & scores.level.eq(level)].sort_values(
            ['industry_code', 'threshold', 'benchmark', 'start_date'])
        s.to_csv(out / f'{tag}_all_stages.csv', index=False, encoding='utf-8-sig')
        check(tag + ' stage export preserves every row',
              len(pd.read_csv(out / f'{tag}_all_stages.csv')) == len(s))
        view = group[['industry_code', 'industry_name', 'valid_return_months',
                      'first_price_date', 'last_price_date']].copy().fillna('—')
        view.columns = ['代码', '行业', '有效收益月数', '首个价格锚点', '最后价格日期']
        for t in THRESHOLDS:
            sg = summary[(summary.era == era) & (summary.level == level) & (summary.threshold == t)]
            lookup = sg.set_index(['industry_code', 'benchmark']).candidates
            view[f'{t:.0%}候选段 300/全指'] = [f'{lookup.loc[(c,"CSI300")]}/{lookup.loc[(c,"CSI_ALL")]}'
                                              for c in group.industry_code]
        view['覆盖状态'] = group.coverage_status.map({'OBSERVABLE':'可观察',
            'NO_ASSIGNED_MEMBER_MONTHS':'无已映射成员月份', 'NO_VALID_PRICE_PATH':'无合格价格路径'}).values
        view['代码来源'] = group.identity_source.map({'CATALOG':'分类目录',
            'MEMBERSHIP_ONLY_CODE':'仅成员记录，代码待核'}).values
        note = ('候选段：起点已知、已确认结束、6—18个月、行业自身上涨且跑赢对应基准。'
                '每格为沪深300/中证全指的段数，三种转折阈值分别列出，不能相加当独立样本。'
                '有效收益月数可能包括2026年10月21日的部分月；完整月与部分月在覆盖表分列。'
                '“0”仅表示本口径未检出候选，不表示行业没有上涨；缺乏价格路径的行业不能推断表现。\n\n')
        (reports / f'{tag}.md').write_text(f'# {era} {level}：全部{len(group)}个行业代码条目\n\n'+note+
            f'[全部阶段及当时市值前三逐股收益](../outputs/{tag}_all_stages.csv)；'
            '[各行业完整指标](../outputs/industry_summary.csv)。\n\n'+table(view))
        links.append(f'[{era} {level} 全部{len(group)}个行业代码条目]({tag}.md)')
        coverage_counts.append({'制度':era, '层级':level, '目录行业':int(group.identity_source.eq('CATALOG').sum()),
            '仅成员记录代码':int(group.identity_source.ne('CATALOG').sum()),
            '有成员月份':int(group.assigned_return_months.gt(0).sum()),
            '可形成价格路径':int(group.price_blocks.gt(0).sum()),
            '无法形成价格路径':int(group.price_blocks.eq(0).sum())})
    counts = pd.DataFrame(coverage_counts)
    counts.to_csv(out / 'coverage_counts.csv', index=False, encoding='utf-8-sig')
    text = ('# EP32：全行业逐项数据与覆盖核对\n\n'
        '研究范围是各个二级、三级行业。V4原计算已覆盖全行业，半导体和通信只是针对用户质疑的复查案例。'
        '本补充直接读取V4全量结果，按完整行业目录逐项展开，包括无数据、没有符合条件阶段和前三收益未知的行业。\n\n'
        '输入覆盖2017-01-03—2026-10-21；月末价格最早锚点为2017年1月。'
        '申万2014版用于2017—2021年11月，2021版用于2022年起；2021年12月分类断点不拼接。'
        '两版目录合计811个“制度×层级×代码”条目，另有1个仅出现在成员记录中的代码，共812个核对条目。'
        '存在行业重叠与分类调整，不能说成812个互不重叠行业。\n\n'+
        table(counts)+'\n完整目录：\n\n'+ '\n'.join('- '+s for s in links)+'\n\n'
        '[全行业覆盖表](../outputs/industry_coverage.csv)记录每个行业可用月份、首末日期、成员不足及收益覆盖不足月份。'
        '至少5个成员、至少80%收益端点覆盖是原V4的价格路径要求；两个不足原因可重叠。'
        '目录有行业但无已映射成员月份，与有成员却达不到价格路径要求分别列出。\n\n'
        '分类异常：SW2021目录的“特钢Ⅲ”为850401.SI，成员记录及原V4实际计算使用850412.SI。'
        '两个代码分别保留，前者无已映射成员月份，后者注明MEMBERSHIP_ONLY_CODE；未经来源核实不按同名合并。\n\n'
        '[逐行业结果总表](../outputs/industry_summary.csv)有4872行：812个核对条目×3个转折阈值×2个基准，'
        '列出自然段、6—18月候选、超18月、未结束、起点未知、前三排名完整数、收益未知数、'
        '前三组合超额中位数和三只均涨且跑赢比例。收益数值用小数单位，例如0.10表示10%收益或10个百分点收益差。'
        '比例只用已知收益样本，未知收益保持空白；各行业样本很少时不据此做行业排名。\n\n'
        '四份行业目录各自链接该层级全部阶段CSV。字段包括起止日期、实际月数、行业收益、基准收益、超额、'
        '起点市值前三代码及逐股收益；小于6月、大于18月、未结束和不跑赢的阶段也全部保留，'
        '用primary_stage列识别符合用户条件的主统计阶段。current_names仅为名称展示，不能当作历史名称断言。\n\n'
        '本补充采用EXACT精确起点报价层。7/31日旧报价估值诊断仍在原V4，未混入主表。'
        '前三按阶段起点市值锁定；行业以收盘到收盘比较，股票以起点后首个市场交易日开盘到段末比较，'
        '各自基准使用相同日期。超过18个月的长行情不拆分。10%/15%/20%转折口径并列，不能挑选对某行业最有利的一项。\n\n'
        '这仍是事后价格观察，转折点需要后来数据确认，尚未验证基本面景气轮动机制；'
        '历史分类、股本known_at与复权价格的严格PIT缺口仍保留，Historical-proxy / BLOCKED_DATA不变。\n\n'
        '[V4全市场统计与方法](../../v4_adaptive_6_18_months/reports/adaptive_stage_observation.md)；'
        '[本次核验](../outputs/validation.json)。\n')
    (reports / 'all_industries.md').write_text(text)
    (ROOT / 'README.md').write_text('# EP32 V4 全行业数据展开\n\n[全行业入口](reports/all_industries.md)。\n\n'
        '使用项目虚拟环境运行 `src/build.py`。只读复用V4及封存分类目录，不重新筛选或重估阶段。'
        '旧版报告保持原字节。\n')
    write_json(out / 'validation.json', dict(status='RUNNING'))
    for p in reports.glob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)', p.read_text()):
            check('link ' + p.name + ' ' + target, (p.parent / target).is_file())
    check('all predecessor files unchanged after reporting', all(sha(p) == h for p, h in predecessors))
    check('all read inputs unchanged', all(sha(Path(p)) == h for p, h in inputs.items()))
    write_json(out / 'inputs.json', inputs)
    write_json(out / 'validation.json', dict(status='PASS', checks=checks, catalog_rows=len(catalog),
               summary_rows=len(summary), exact_stage_benchmark_rows=len(scores),
               strict_PIT='BLOCKED_DATA', recalculated_stages=False))
    files = [dict(path=str(p.relative_to(ROOT)), sha256=sha(p), bytes=p.stat().st_size)
             for p in sorted(ROOT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts
             and p != out / 'manifest.json']
    write_json(out / 'manifest.json', dict(status='WORKING', files=files, strict_PIT='BLOCKED_DATA'))
    print(counts.to_string(index=False))
    print(f'PASS {len(checks)} checks; {len(summary)} industry-comparison rows; {len(scores)} stage-comparison rows')


if __name__ == '__main__':
    main()
