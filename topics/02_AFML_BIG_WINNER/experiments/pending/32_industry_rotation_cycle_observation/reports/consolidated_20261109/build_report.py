"""Rebuild the consolidated report from frozen public results; no model training."""
from pathlib import Path
import base64
import hashlib
import html
import json
import os
import re

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent
EP = ROOT.parents[1]
EXT = EP / 'extensions'
D2 = EP.parent / '30_pit_data_foundation_v1/extensions/v6_ttm_pe'
SOURCES = {}
CHECKS = []
TABLES = {}
FREQ = {'W': '周', 'BW': '双周', 'M': '月'}
FAMILY = {'levels': '多尺度水平', 'paths': '扩张路径', 'stage': '在线阶段'}
METHOD = {'accepted': '验收双树规则', 'risk_blend_baseline': '原 risk_blend',
          'baseline': '原38项扩散树', 'levels': '交易水平', 'paths': '交易路径', 'stage': '交易阶段',
          'pe': '仅新增PE', 'same_date_universe': '同日全行业', 'early_market_all': '早期＋市场池',
          'momentum_matched': '同K动量', 'diffusion_matched': '同K扩散树',
          'capacity_matched': '同K无扩散同容量树'}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def source(p):
    p = Path(p).resolve()
    assert p.is_file(), p
    SOURCES[os.path.relpath(p, ROOT)] = sha(p)
    return p


def csv(name, base=EXT):
    return pd.read_csv(source(base / name))


def js(name, base=EXT):
    return json.loads(source(base / name).read_text())


def check(name, ok):
    assert bool(ok), name
    CHECKS.append({'name': name, 'passed': True})


def table(name, data, cols, pct=(), decimal=(), pp=()):
    d = data.copy()
    d.to_csv(ROOT / 'tables' / (name.lower() + '.csv'), index=False)
    records = []
    for _, row in d.iterrows():
        cells = []
        for key in cols:
            value = row[key]
            if pd.isna(value): text = '—'
            elif key in pp: text = f'{float(value)*100:+.2f}'
            elif key in pct: text = f'{float(value):.2%}'
            elif key in decimal: text = f'{float(value):.2f}'
            elif key == 'frequency': text = FREQ.get(value, str(value))
            elif key == 'family': text = FAMILY.get(value, str(value))
            elif key in ['method', 'model']: text = METHOD.get(value, str(value))
            elif isinstance(value, (float, np.floating)): text = str(int(value)) if value == int(value) else f'{value:.6f}'
            else: text = str(value)
            cells.append(text.replace('|', '\\|').replace('\n', ' '))
        records.append('| ' + ' | '.join(cells) + ' |')
    result = '| ' + ' | '.join(cols.values()) + ' |\n| ' + ' | '.join(['---'] * len(cols)) + ' |\n' + '\n'.join(records)
    TABLES[name] = result
    return result


def first_launch(d, months=6):
    return d[d.unit.eq('six_month_launches') & d.months.eq(months)]


def build():
    (ROOT / 'tables').mkdir(exist_ok=True)
    (ROOT / 'figures').mkdir(exist_ok=True)
    coverage = csv('v4_all_industry_review/outputs/coverage_counts.csv')
    table('INDUSTRY_COVERAGE', coverage, {k: k for k in coverage.columns})
    pe_cov = csv('outputs/universe_yearly_coverage.csv', D2)
    pe_cov = pe_cov[pe_cov.provider.eq('eastmoney')]
    table('PE_COVERAGE', pe_cov, {'year':'年份','universe':'历史Universe证券交易日','finite_pe':'有PE记录','positive_pe':'正PE记录','finite_coverage':'记录覆盖率','positive_coverage':'正PE覆盖率'},pct=['finite_coverage','positive_coverage'])
    natural = csv('v4_adaptive_6_18_months/outputs/metrics/natural_stage_counts.csv')
    table('NATURAL_COUNTS',natural,{'threshold':'阈值','level':'层级','confirmed_known_start':'已确认且起点已知','short_lt6':'不足6月','completed_6_18':'6—18月','long_gt18':'超过18月','left_censored':'左删失','right_censored':'未结束','median_completed_months':'全部已确认阶段中位月数'},pct=['threshold'])
    check('natural stage length inventory reconciles',natural.confirmed_known_start.eq(natural.short_lt6+natural.completed_6_18+natural.long_gt18).all())

    phases = csv('v4_adaptive_6_18_months/outputs/screens/industry_up_and_beat_6_18.csv')
    phases = phases[phases.policy.eq('EXACT') & phases.benchmark.eq('CSI_ALL')]
    check('V4 single policy single benchmark phase identity unique', not phases.phase_id.duplicated().any())
    ds = phases.groupby(['threshold', 'level']).agg(
        stages=('phase_id', 'size'), mean_months=('duration_months', 'mean'),
        median_months=('duration_months', 'median'), mean_return=('industry_return', 'mean'),
        median_return=('industry_return', 'median'), mean_excess=('industry_excess', 'mean'),
        median_excess=('industry_excess', 'median')).reset_index()
    check('V4 six descriptive cells preserved', len(ds) == 6)
    table('DURATION_STATS', ds, {'threshold':'转折阈值', 'level':'层级', 'stages':'阶段数',
          'mean_months':'平均月数', 'median_months':'中位月数', 'mean_return':'平均涨幅',
          'median_return':'中位涨幅', 'mean_excess':'平均超额', 'median_excess':'中位超额'},
          pct=['threshold','mean_return','median_return','mean_excess','median_excess'], decimal=['mean_months','median_months'])
    top = csv('v4_adaptive_6_18_months/outputs/metrics/candidate_summary.csv')
    top = top[top.policy.eq('EXACT') & top.benchmark.eq('CSI_ALL') & top.threshold.eq(.15)]
    table('TOP3', top, {'level':'层级','industry_candidate_stages':'行业候选段', 'endpoint_known':'前三终点已知',
         'unknown':'前三终点未知', 'median_portfolio_excess':'前三等权组合超额中位',
         'all_three_positive_and_beat_rate':'三只均上涨且跑赢（已知终点）'},
         pct=['median_portfolio_excess','all_three_positive_and_beat_rate'])

    winners = []
    for stage in ['a','b']:
        winner = js(f'v5_rdagent_onset_forecast/outputs/stage_{stage}/frozen_selection.json')['winner']
        winners.append(dict(stage=stage.upper(), candidate=winner['candidate'], features=len(winner['spec']['features']), **{k:v for k,v in winner['spec'].items() if k not in ['features','engineered','C','model']}))
    table('RD_CONFIG', pd.DataFrame(winners), {'stage':'阶段','candidate':'冻结候选','features':'输入项数','trees':'树数','leaves':'叶子数','max_depth':'深度','min_child_samples':'最小叶样本','learning_rate':'学习率','reg_lambda':'L2'})
    (ROOT/'tables/rd_winning_specs.json').write_text(json.dumps({s:js(f'v5_rdagent_onset_forecast/outputs/stage_{s}/frozen_selection.json')['winner'] for s in ['a','b']},ensure_ascii=False,indent=2)+'\n')
    model = js('v35_pe_activity_joint/outputs/model_freeze.json')
    source(EXT/'v12_duration_risk/src/experiment12.py')
    params = pd.DataFrame([
        dict(model='V12 risk_tree',features=27,trees=90,leaves=7,depth=3,minchild=500,lr=.03),
        dict(model='V18 diffusion_tree',features=38,trees=240,leaves=15,depth=4,minchild=200,lr=.03),
        dict(model='V34 levels / paths / stage',features='44 / 43 / 42',trees=240,leaves=15,depth=4,minchild=200,lr=.03),
        dict(model='V35 pe',features=45,trees=240,leaves=15,depth=4,minchild=200,lr=.03),
        dict(model='V35 joint_levels / paths / stage',features='51 / 50 / 49',trees=240,leaves=15,depth=4,minchild=200,lr=.03),
        dict(model='V35 三个缺失指示对照',features='51 / 50 / 49',trees=240,leaves=15,depth=4,minchild=200,lr=.03)])
    table('MODEL_PARAMS',params,{'model':'模型','features':'输入特征数','trees':'树数','leaves':'叶子上限','depth':'深度上限','minchild':'最小叶样本','lr':'学习率'})
    receipt=js('v35_pe_activity_joint/outputs/prediction_receipt.json')
    folds=pd.DataFrame(receipt['folds'])
    good=folds.training.notna()
    check('14 nonempty quarters, 404274 predictions', good.sum()==14 and int(folds.test.sum())==receipt['rows']==404274)
    check('all quarterly training labels predate fit', (pd.to_datetime(folds.loc[good,'latest_training_label']) < pd.to_datetime(folds.loc[good,'quarter'])).all())
    check('four exact Q1 replays recorded', set(receipt['q1_exact_replays'])=={'baseline','levels','paths','stage'})
    table('FOLDS', folds, {'quarter':'季度起点','training':'训练行','positive':'训练正例行','latest_training_label':'最近标签成熟日','test':'预测行','eligible':'符合在线资格行'})
    groups=[('状态和价格（19项）',model['base_features'][:19],'候选趋势位置、绝对/相对动量、波动、上涨宽度、量比、任务定义'),
            ('风险尺度（8项）',model['base_features'][19:27],'行情年龄、波动尺度、漂移噪声、距离终止线'),
            ('龙头/同业扩散（11项）',model['base_features'][27:],'前三与同业收益差、扩散宽度、市场残差、下跌韧性')]
    table('FEATURE_GROUPS', pd.DataFrame([{'group':a,'features':', '.join(b),'meaning':c} for a,b,c in groups]),{'group':'特征组','features':'字段','meaning':'可观察含义'})
    check('base 38 features and joint dimensions',len(model['base_features'])==38 and [len(model['models']['joint_'+x])+38 for x in ['levels','paths','stage']]==[51,50,49])
    rd_results=pd.DataFrame([
        ['A','W',.0287,-.0044,.0330,1.08],['A','BW',.0308,-.0032,.0348,1.04],['A','M',.0279,0,.0318,1.03],
        ['B','W',.0818,.0216,.1147,1.42],['B','BW',.0790,.0246,.1130,1.44],['B','M',.0814,.0331,.1142,1.37]],
        columns=['stage','frequency','base_rate','brier_gain','precision','lift'])
    source(EXT/'v5_rdagent_onset_forecast/reports/rdagent_observation.md')
    table('RD_RESULTS',rd_results,{'stage':'阶段','frequency':'频率','base_rate':'正例率','brier_gain':'Brier较先验改善','precision':'前10%命中率','lift':'同期正例率倍数'},pct=['base_rate','brier_gain','precision'],decimal=['lift'])
    acceptance=csv('v28_aggregate_acceptance/outputs/independent_summary.csv')
    table('ACCEPTANCE',acceptance,{'model':'方案','precision':'precision','point_recall':'时点recall','event_recall':'周期recall','active_date_fraction':'活跃日期','median_delay_days':'任务中位延迟平均/天'},pct=['precision','point_recall','event_recall','active_date_fraction'],decimal=['median_delay_days'])
    raw_accept=csv('v28_aggregate_acceptance/outputs/independent_metrics.csv')
    agg=raw_accept.groupby('model')[['precision','point_recall','event_recall','active_date_fraction','median_delay_days']].mean()
    check('36 task mean reconciles acceptance',np.allclose(agg.sort_index(),acceptance.set_index('model').loc[agg.sort_index().index,agg.columns],atol=1e-12))
    decision=js('v28_aggregate_acceptance/outputs/decision.json')
    check('V28 aggregate gates and unknown counts', decision['precision']>=.235 and decision['event_recall']>=.4125 and decision['known_alerts']+decision['unknown_alerts']==decision['alerts']==20308)
    freq_accept=csv('v28_aggregate_acceptance/outputs/frequency_summary.csv')
    table('FREQUENCY_ACCEPTANCE',freq_accept,{'model':'方案','frequency':'频率','precision':'precision','point_recall':'时点recall','event_recall':'周期recall','active_date_fraction':'活跃日期'},pct=['precision','point_recall','event_recall','active_date_fraction'])
    annual=csv('v28_aggregate_acceptance/outputs/annual_comparison.csv')
    table('ANNUAL_ACCEPTANCE',annual,{'year':'年','precision_base':'原precision','precision_new':'新precision','event_recall_base':'原周期recall','event_recall_new':'新周期recall','point_recall_new':'新时点recall','active_date_fraction':'新活跃日期'},pct=list(annual.columns[1:]))
    cyc=csv('v31_all_signal_economics/outputs/cycle_metrics.csv')
    cyc=cyc[cyc.threshold.eq(.15)&cyc.benchmark.eq('CSI_ALL')&cyc.level.eq('L3')]
    table('PEAK',cyc,{'frequency':'频率','detected_cycles':'捕捉周期','evaluable_cycles':'可评价周期','mean_remaining_gain':'平均到峰值涨幅','median_remaining_gain':'中位涨幅','mean_days_to_peak':'平均到峰值天数','median_days_to_peak':'中位天数'},pct=['mean_remaining_gain','median_remaining_gain'],decimal=['mean_days_to_peak','median_days_to_peak'])
    econ=csv('v31_all_signal_economics/outputs/primary_metrics.csv')
    acc=econ[econ.method.eq('accepted')&econ.unit.eq('six_month_launches')]
    ec_cols={'frequency':'频率','signals':'启动数','known_returns':'已知收益','missing_returns':'未知收益','mean_return':'平均收益','median_return':'中位收益','mean_excess':'平均超额','median_excess':'中位超额','mean_max_drawdown':'平均最大回撤'}
    ec_pct=['mean_return','median_return','mean_excess','median_excess','mean_max_drawdown']
    table('ECONOMICS',acc[acc.months.eq(6)],ec_cols,pct=ec_pct)
    table('HORIZONS',acc,{'frequency':'频率','months':'期限/月','signals':'启动数','known_returns':'已知收益','mean_return':'平均收益','median_return':'中位收益','mean_excess':'平均超额','median_excess':'中位超额'},pct=ec_pct)
    control=first_launch(econ)
    control=control[control.method.isin(['accepted','same_date_universe','early_market_all','momentum_matched','capacity_matched','diffusion_matched'])]
    table('ECON_CONTROLS',control,{'frequency':'频率','method':'方法','signals':'启动数','known_returns':'已知收益','mean_excess':'平均超额','median_excess':'中位超额'},pct=['mean_excess','median_excess'])
    ecy=csv('v31_all_signal_economics/outputs/primary_annual.csv')
    ecy=ecy[ecy.method.eq('accepted')&ecy.unit.eq('six_month_launches')]
    table('ECON_YEARS',ecy,{'frequency':'频率','year':'年','signals':'启动数','known_returns':'已知收益','mean_return':'平均收益','mean_excess':'平均超额','median_excess':'中位超额'},pct=['mean_return','mean_excess','median_excess'])

    expansion=pd.DataFrame([
        ['交易水平','21/63、63/126、504/756交易日','turn_short, turn_medium, volume_short, turn_rank504, turn_rank756, share_short','短中期活跃变化与长期位置'],
        ['交易路径','21日变化、63日斜率、6个21日区间','turn_slope63, turn_acceleration, turn_persistence, expansion_breadth, breadth_change21','持续、加速及成员扩散'],
        ['在线阶段','候选低点至当日，可变长度','stage_turn_change, stage_share_change, stage_breadth_change, stage_turn_speed','启动以来参与度变化'],
        ['PE变化','21/63/126/252交易日','pe_change21, pe_change63, pe_change126, pe_change252','成员连续正PE对数变化中位数'],
        ['PE位置与广度','504/756日秩、21日广度','pe_rank504, pe_rank756, pe_breadth21','长期位置与成员估值扩张占比']],columns=['group','windows','features','meaning'])
    table('EXPANSION_FEATURES',expansion,{'group':'家族','windows':'尺度','features':'字段','meaning':'含义'})
    act=first_launch(csv('v34_multiscale_expansion/outputs/economics_primary.csv'))
    act=act[act.method.isin(['baseline','levels','paths','stage'])]
    table('ACTIVITY_RESULTS',act,{'frequency':'频率','method':'方法','signals':'启动数','known_returns':'已知收益','mean_return':'平均收益','mean_excess':'平均超额','median_excess':'中位超额'},pct=['mean_return','mean_excess','median_excess'])
    main=csv('v35_pe_activity_joint/outputs/main_comparisons.csv')
    table('JOINT_MAIN',main,{'frequency':'频率','family':'家族','activity_mean_excess':'交易平均超额','joint_mean_excess':'联合平均超额','launch_mean_delta':'差值/pp','joint_launches':'联合启动数','known_returns':'已知收益'},pct=['activity_mean_excess','joint_mean_excess'],pp=['launch_mean_delta'])
    intervals=main.copy()
    intervals['ci95']=intervals.apply(lambda x:f'[{x.lower95*100:+.2f}, {x.upper95*100:+.2f}]',axis=1)
    intervals['ci9']=intervals.apply(lambda x:f'[{x.lower9*100:+.2f}, {x.upper9*100:+.2f}]',axis=1)
    intervals['delta_pp']=intervals.paired_estimate*100
    table('JOINT_INTERVALS',intervals,{'frequency':'频率','family':'家族','paired_dates':'配对日期','delta_pp':'配对增量/pp','ci95':'95%区间/pp','ci9':'九重校正区间/pp'},decimal=['delta_pp'])
    check('all nine primary intervals cross zero',len(main)==9 and main.lower95.lt(0).all() and main.upper95.gt(0).all() and main.lower9.lt(0).all())
    cls=csv('v35_pe_activity_joint/outputs/classification_primary.csv')
    c=cls[cls.method.isin(['joint_levels','joint_paths','joint_stage'])].copy()
    c['family']=c.method.str.replace('joint_','',regex=False)
    controls=cls[cls.method.isin(['levels','paths','stage'])][['frequency','method','precision','cycle_recall']].rename(columns={'method':'family','precision':'activity_precision','cycle_recall':'activity_recall'})
    c=c.merge(controls,on=['frequency','family'],validate='one_to_one')
    table('JOINT_CLASSIFICATION',c,{'frequency':'频率','family':'家族','activity_precision':'交易precision','precision':'联合precision','activity_recall':'交易周期recall','cycle_recall':'联合周期recall','point_recall':'联合时点recall','median_delay':'联合中位延迟/天'},pct=['activity_precision','precision','activity_recall','cycle_recall','point_recall'],decimal=['median_delay'])
    brier=csv('v35_pe_activity_joint/outputs/brier_relative_improvement.csv')
    table('BRIER',brier,{'frequency':'频率','family':'家族','activity':'交易Brier','joint':'联合Brier','relative_improvement':'相对改善'},pct=['relative_improvement'])
    check('all nine Brier errors worsen',len(brier)==9 and brier.relative_improvement.lt(0).all() and np.allclose(1-brier.joint/brier.activity,brier.relative_improvement))
    complete=csv('v35_pe_activity_joint/outputs/eligible_coverage.csv')
    complete=complete[complete.year.eq('ALL')]
    table('JOINT_COVERAGE',complete,{'frequency':'频率','family':'家族','eligible_rows':'合资格母体','complete_rows':'共同完整','complete_fraction':'完整比例','accepted_alerts':'原报警K总数','complete_alerts':'完整池报警K总数'},pct=['complete_fraction'])
    check('complete coverage ratios',np.allclose(complete.complete_rows/complete.eligible_rows,complete.complete_fraction))
    cells=csv('v35_pe_activity_joint/outputs/four_cells.csv')
    cells=cells[cells.year.eq('ALL')].copy()
    cells['cell']=cells.cell.map({'BOTH':'双扩张','PE_ONLY':'仅PE扩张','ACTIVITY_ONLY':'仅交易扩张','NEITHER':'均不扩张','UNKNOWN':'未知'})
    table('FOUR_CELLS',cells,{'frequency':'频率','cell':'组','signals':'启动数','known_returns':'已知收益','cycle_known':'已知标签','precision':'合并命中率','mean_excess':'平均超额','median_excess':'中位超额'},pct=['precision','mean_excess','median_excess'])
    inc=csv('v35_pe_activity_joint/outputs/annual_increment.csv').pivot(index=['frequency','family'],columns='year',values='delta').reset_index()
    table('JOINT_ANNUAL',inc,{'frequency':'频率','family':'家族',2021:'2021/pp',2022:'2022/pp',2023:'2023/pp',2024:'2024/pp'},pp=[2021,2022,2023,2024])
    all35=first_launch(csv('v35_pe_activity_joint/outputs/economics_primary.csv'))
    ablation=all35[all35.method.isin(['baseline','pe','levels','joint_levels'])].pivot(index='frequency',columns='method',values='mean_excess').reset_index()
    table('JOINT_ABLATION',ablation,{'frequency':'频率','baseline':'原38项基线','pe':'仅新增PE','levels':'仅新增交易水平','joint_levels':'交易水平＋PE'},pct=['baseline','pe','levels','joint_levels'])
    for row in main.itertuples():
        left=all35[all35.frequency.eq(row.frequency)&all35.method.eq('joint_'+row.family)].iloc[0]
        right=all35[all35.frequency.eq(row.frequency)&all35.method.eq(row.family)].iloc[0]
        check(f'{row.frequency} {row.family} main table matches economics',np.isclose(left.mean_excess-right.mean_excess,row.launch_mean_delta,atol=1e-12) and left.signals==row.joint_launches and left.known_returns==row.known_returns)
    audit=[]
    for version,expected in [('v34_multiscale_expansion',179),('v35_pe_activity_joint',245)]:
        val=js(version+'/outputs/validation.json')
        check(version+' recorded validation PASS',val['status']=='PASS' and val['checks_count']==expected)
        audit.append(dict(scope=version,checks=expected,status=val['status'],type='原轮次保存结果'))
    table('AUDIT_TABLE',pd.DataFrame(audit),{'scope':'实验','checks':'检查项','status':'结果','type':'性质'})

    # Preserve full current-results appendices, not just favorable rows.
    attachments=[]
    for name in ['v28_aggregate_acceptance/outputs/independent_metrics.csv',
                 'v31_all_signal_economics/outputs/primary_metrics.csv',
                 'v35_pe_activity_joint/outputs/classification_all_tasks.csv',
                 'v35_pe_activity_joint/outputs/classification_primary.csv',
                 'v35_pe_activity_joint/outputs/annual_classification.csv',
                 'v35_pe_activity_joint/outputs/economics_primary.csv',
                 'v35_pe_activity_joint/outputs/annual_economics.csv',
                 'v35_pe_activity_joint/outputs/paired_intervals.csv',
                 'v35_pe_activity_joint/outputs/outcome_coverage.csv',
                 'v35_pe_activity_joint/outputs/feature_importance.csv']:
        p=source(EXT/name);dest=ROOT/'tables'/('_'.join([p.parts[-3].split('_')[0],p.name]))
        dest.write_bytes(p.read_bytes());attachments.append(f'- [{dest.name}](tables/{dest.name})：原结果逐字节副本。')
    TABLES['ATTACHMENTS']='\n'.join(attachments)+'\n\n特征重要性是树的分裂增益，不是因果效应；相关变量之间可能相互替代。'
    feature_rows=[{'model':name,'features':', '.join(cols),'count':len(model['base_features'])+len(cols)} for name,cols in model['models'].items()]
    table('FULL_FEATURE_LIST',pd.DataFrame(feature_rows),{'model':'V35新增模型','count':'总维度','features':'在第4.4节全部38项基础上新增字段'})
    (ROOT/'tables/model_freeze.json').write_text(json.dumps(model,ensure_ascii=False,indent=2)+'\n')

    index=[]
    # Main reports plus all per-hypothesis descriptions, excluding failed attempt copies.
    reports=list((EP/'reports').glob('*.md'))
    for directory in sorted(EXT.iterdir(),key=lambda p:(int(re.search(r'v(\d+)',p.name)[1]) if re.search(r'v(\d+)',p.name) else 999,p.name)):
        reports.extend(sorted((directory/'reports').glob('*.md')))
    reports.append(D2/'reports/ttm_pe_coverage.md')
    for p in reports:
        source(p);title=p.read_text().splitlines()[0].lstrip('# ').strip()
        index.append(f'- [{p.parent.parent.name}：{title}]({os.path.relpath(p,ROOT)})')
    TABLES['REPORT_INDEX']='\n'.join(index)

    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150})
    fig,axs=plt.subplots(1,2,figsize=(11,4.3),layout='constrained')
    a=acceptance.set_index('model');keys=['precision','event_recall','point_recall'];x=np.arange(3)
    axs[0].bar(x-.18,a.loc['risk_blend_baseline',keys]*100,.36,label='Original risk blend',color='#aeb9c2')
    axs[0].bar(x+.18,a.loc['accepted',keys]*100,.36,label='Accepted dual-tree rule',color='#187e94')
    axs[0].set_xticks(x,['Precision','Cycle recall','Point recall']);axs[0].set_ylabel('Percent');axs[0].set_title('36-task macro averages');axs[0].legend(fontsize=8)
    axs[1].plot(annual.year,annual.event_recall_base*100,'o-',label='Original risk blend',color='#8c9ca7')
    axs[1].plot(annual.year,annual.event_recall_new*100,'o-',label='Accepted rule',color='#187e94')
    axs[1].set_xticks(annual.year);axs[1].set_ylabel('Cycle recall (%)');axs[1].set_title('Annual limitation remains');axs[1].legend(fontsize=8)
    fig.savefig(ROOT/'figures/acceptance.png');plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,5.3),layout='constrained');y=np.arange(len(main))
    ax.hlines(y,main.lower9*100,main.upper9*100,color='#b8d5dd',linewidth=7,label='99.444% (9 comparisons)')
    ax.hlines(y,main.lower95*100,main.upper95*100,color='#187e94',linewidth=2,label='95%')
    ax.scatter(main.paired_estimate*100,y,color='#132f3b',s=28,zorder=4);ax.axvline(0,color='#bb663a',linestyle='--')
    ax.set_yticks(y,[f'{r.frequency} / {r.family}' for r in main.itertuples()]);ax.invert_yaxis();ax.set_xlabel('Joint minus activity: date-paired mean excess return (percentage points)')
    ax.set_title('PE + activity: no positive primary confidence interval');ax.legend(fontsize=8,loc='lower left',bbox_to_anchor=(0,1.055),ncol=2)
    fig.savefig(ROOT/'figures/joint_intervals.png');plt.close(fig)

    template=(ROOT/'report_template.md').read_text()
    for name,value in TABLES.items():template=template.replace('@@'+name+'@@',value)
    check('all report placeholders resolved',not re.search(r'@@[A-Z_]+@@',template))
    (ROOT/'report.md').write_text(template)
    # Resolve every local evidence and attachment link; store hashes for external-to-this-report sources.
    links=re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',template)
    checked=0
    for link in links:
        if link.startswith(('http://','https://','#')):continue
        p=(ROOT/link.split('#')[0]).resolve()
        check('report link '+link,p.is_file());checked+=1
        if not p.is_relative_to(ROOT):source(p)
    md=MarkdownIt('commonmark',{'html':True}).enable('table')
    rendered=md.render(template)
    for p in (ROOT/'figures').glob('*.png'):
        rendered=rendered.replace('src="figures/'+p.name+'"','src="data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode()+'"')
    headings=[]
    def heading(match):
        i=len(headings)+1;headings.append((i,re.sub('<[^>]+>','',match[2])))
        return f'<h{match[1]} id="section-{i}">{match[2]}</h{match[1]}>'
    rendered=re.sub(r'<h([23])>(.*?)</h\1>',heading,rendered)
    toc='<nav><strong>目录</strong><ol>'+''.join(f'<li><a href="#section-{i}">{html.escape(t)}</a></li>' for i,t in headings)+'</ol></nav>'
    css='''body{margin:0;color:#20313d;background:#f6f8fa;font:16px/1.8 system-ui,sans-serif}main{max-width:1160px;margin:auto;padding:48px;background:white}h1{font-size:2rem;color:#123c50}h2{margin-top:2.8rem;border-bottom:2px solid #d9e6eb;padding-bottom:.4rem}h3{margin-top:2rem}a{color:#086c92}table{display:block;overflow-x:auto;border-collapse:collapse;font-size:13px;line-height:1.6;margin:1.4em 0}th,td{border:1px solid #d8e0e5;padding:8px 10px;vertical-align:top}th{background:#eaf2f5;white-space:nowrap}tr:nth-child(even){background:#fafcfd}img{max-width:100%;height:auto}pre{padding:16px;background:#f1f5f7;overflow:auto}code{overflow-wrap:anywhere}nav{padding:20px;background:#f1f6f8}nav ol{columns:2;font-size:14px}p,li{overflow-wrap:anywhere}@media print{body{background:white}main{padding:0}nav{display:none}h2,h3{break-after:avoid}table{display:table;width:100%;font-size:9px}img{max-height:20cm}}@media(max-width:700px){main{padding:20px}nav ol{columns:1}}'''
    (ROOT/'report.html').write_text('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EP32 完整实验报告 · 2026-11-09</title><style>'+css+'</style></head><body><main>'+toc+rendered+'</main></body></html>')
    for path,digest in SOURCES.items():check('source unchanged '+path,sha(ROOT/path)==digest)
    (ROOT/'sources.json').write_text(json.dumps({'report_date':'2026-11-09','timezone':'Asia/Shanghai','sources':SOURCES},ensure_ascii=False,indent=2)+'\n')
    (ROOT/'validation.json').write_text(json.dumps({'status':'PASS','scope':'report-only reconciliation; no training or old test rerun','checks_count':len(CHECKS),'checks':CHECKS,'local_links':checked,'source_files':len(SOURCES),'strict_PIT':'BLOCKED_DATA','independent_forward':'FORWARD_PENDING'},ensure_ascii=False,indent=2)+'\n')
    manifest=[{'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts]
    (ROOT/'manifest.json').write_text(json.dumps({'report_date':'2026-11-09','files':manifest},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':'PASS','checks':len(CHECKS),'sources':len(SOURCES),'links':checked,'files':len(manifest),'report_chars':len(template)},ensure_ascii=False))


if __name__=='__main__':build()
