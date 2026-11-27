"""Render separate numbered reports and verifiable machine-readable historical execution receipts."""
from summarize import *
import hashlib
import json
from collections import OrderedDict

def tab(head,rows):
    def fmt(k):
        if isinstance(k,(float,np.floating)):return '—' if not np.isfinite(k) else f'{k:.2f}'
        return str(k)
    return '\n'.join(['| '+' | '.join(head)+' |','|'+'---|'*len(head)]+['| '+' | '.join(map(fmt,row))+' |' for row in rows])
def main():
    reports=HERE/'reports';reports.mkdir(exist_ok=True)
    s=pd.read_csv(RES/'comparisons.csv');cap=pd.read_parquet(RES/'decision_capital.parquet')
    ch=pd.read_parquet(RES/'decision_changes.parquet');sp=pd.read_csv(RES/'state_spreads.csv')
    common='''沪深300每季度用已成熟周标签训练，收盘生成信号、下一开盘建H10仓。十份独立本金错峰运行，每段初始本金1，买10 bp、卖20 bp，同股成交净额收费。前段为2021-01-11至2025-03-03，后段独立从2025-03-03至2026-10-12。共同完整月份49、18个；表中账户差均为配对月收益的算术平均，单位 bp/月。95%区间段内每次抽连续三个月，共10,000次，按月数合并。各项均是登记晚于回放终点的历史机制检验。'''
    footer='''[逐股分数和账户索引](../REPORT.md) · [逐月毛、费、历史回放净额](../results/months.csv) · [完整比较与双费](../results/comparisons.csv) · [逐年收益、指数及等权基准](../results/annual_benchmarks.csv) · [逐段净值、最大回撤](../results/paths.csv) · [目标与实际资金差](../results/decision_capital.parquet) · [状态与原始批次收支](../results/cohort_pnl.parquet)'''
    labels={'S2_A':'A 原值','S2_B':'B 当日中秩','S2_C':'C 放回训练边际','S2_D':'D 固定训练CDF','vol_live':'当日原尺度','vol_fixed':'固定水平和宽度','vol_loc':'仅保留当日水平','vol_width':'仅保留当日宽度','vol_lag20':'滞后20日','sector_live':'行业内当日','sector_fixed':'行业内固定','paired_live':'行业＋风格当日','paired_fixed':'行业＋风格固定','mse69':'平方损失树69','ridge69':'Ridge69','ridge78':'Ridge78','original78tree':'原配方树78','mse78':'平方损失树78','early':'仅早停树','shallow':'仅深度3树','shallow_early':'浅层早停树','R':'原Ridge78','G3_interaction':'含三项交互','G3_main':'仅新增主效应','dynamic':'D5动态'}
    def label(a):
        for suffix,txt in [('_commonmask','、同义列共同掩码'),('_supported','、共同支持'),('_invested','、可投资金')]:
            if a.endswith(suffix):return label(a[:-len(suffix)])+txt
        return labels.get(a,a)
    def table_for(tag,restrict=None,data=None):
        g=(s[s.id==tag] if data is None else data)
        rows=[]
        for (a,b),h in g.groupby(['arm','base'],sort=False):
            if restrict is not None and (a,b) not in restrict:continue
            idx=h.set_index(['segment','fee_multiple'])
            cell=idx.loc['all',1]
            rows.append((label(a)+' 减 '+label(b),idx.at[('primary',1),'net_bp'],idx.at[('later',1),'net_bp'],cell.net_bp,f'[{cell.lo:.1f}, {cell.hi:.1f}]',cell.gross_bp,cell.fee_bp,cell.drop_best3,idx.at[('all',2),'net_bp']))
        return tab(['比较','前段','后段','合计','合计95%区间','毛差','费差','各删最好三月','双费合计'],rows)
    def changes(tag,a,b):
        h=ch[(ch.id==tag)&(ch.arm==a)&(ch.base==b)]
        v=cap[(cap.id==tag)&(cap.arm==a)&(cap.base==b)]
        pct=100*(h.seats-h.shared).sum()/h.seats.sum()
        return f'这对模型在{len(h):,}个评分日改变{(h.seats-h.shared).sum():,}/{h.seats.sum():,}个目标席位（{pct:.2f}%）。两本独立账户的实际净买单逐股差绝对值之和的一半，按各段初始本金累计为{v.groupby("segment").changed_broker_buy.sum().get("primary",0):.3f}、{v.groupby("segment").changed_broker_buy.sum().get("later",0):.3f}倍；包含反复换手和复投。'
    def state_table(pairs):
        rows=[]
        for a,b in pairs:
            g=sp[(sp.arm==a)&(sp.base==b)].set_index('segment')
            if len(g)!=2:continue
            rows.append((label(a)+' 减 '+label(b),g.at['primary','high_minus_low_bp_h10'],f'[{g.at["primary","lo"]:.1f}, {g.at["primary","hi"]:.1f}]',g.at['later','high_minus_low_bp_h10'],f'[{g.at["later","lo"]:.1f}, {g.at["later","hi"]:.1f}]'))
        return tab(['两模型','前段高减低','前段区间','后段高减低','后段区间'],rows)
    def write(id,title,lead,body):
        (reports/(id+'.md')).write_text(f'# {id}｜{title}\n\n{lead}\n\n## 样本与账户\n\n{common}\n\n{body}\n\n{footer}\n')
    b=pd.read_csv(RES/'S1_structure.csv')
    sf=pd.read_parquet(RES/'S1_features.parquet')
    features=sf.query('cohort=="eligible" and path=="all"').groupby('feature').deviation.sum().nlargest(6)
    unobs=sf.groupby(['cohort','path'])[['observable_weight','unobserved_weight']].sum()
    leaves=pd.read_csv(RES/'S1_leaf_transitions.csv').groupby('cohort')[['common_trees','changed_leaves']].sum()
    names={'primary':'前段','later':'后段','all':'全部路径','observed_paths':'路径沿途皆观测','eligible':'每日合格池','fixed':'季前固定池'}
    write('S1','原值树的实际分支与市场状态','前段市场离散度越高，实际走支比例越偏离训练参考；锁定季前名单和剔除填补路径后结果相近。后段点值仍为正，但区间含零。路径会变，全账户择时的费后价值尚须独立检验。',f'''## 实际分支发生了什么

每个内部节点只计真正到达该父节点的股票，训练时到达频率决定权重。各节点当日左支率与训练左支率的绝对差按可见训练权重求均值。折内分别去掉两变量的均值后，计算结构量对连续Z1的斜率。表内斜率和区间均放大100倍，表示Z1从0到1对应结构量的百分点变化。转支率是相邻日同股、同父节点、仍可见时改变左右支的比例。

{tab(['阶段','名单','路径','日期','结构斜率','95%区间','同父转支率%'],[(names[r.segment],names[r.cohort],names[r.path],r.dates,100*r.slope,f'[{100*r.lo:.2f}, {100*r.hi:.2f}]',100*r.switch_rate) for r in b.sort_values(['segment','cohort','path'],ascending=[False,True,True]).itertuples()])}

资格名单407,372个股票日；固定季前名单406,411个，其中406,013个有当日报价（398个未知），396,492个仍符合当日资格。日常资格名单同一股票相邻日换叶率{100*leaves.at['eligible','changed_leaves']/leaves.at['eligible','common_trees']:.2f}%，固定名单{100*leaves.at['fixed','changed_leaves']/leaves.at['fixed','common_trees']:.2f}%。原池全部路径无到达节点的训练权重占比为{100*unobs.loc[('eligible','all'),'unobserved_weight']/unobs.loc[('eligible','all')].sum():.3f}%。对结构量加权分子贡献最大的六个实际分裂输入按顺序为{', '.join(features.index)}；它们同时反映树使用频率。

[真实节点逐日结构](../results/S1_daily.parquet) · [首折逐节点](../results/S1_nodes_2021Q1.parquet) · [叶索引与实际叶值模型](../results/leaves) · [可见性](../results/S1_coverage.csv) · [各特征与无支持权重](../results/S1_features.parquet) · [同股换叶](../results/S1_leaf_transitions.csv)''')
    write('S2','每日排名移除了什么','原值树胜过按日剥离边际分布的树，两段点估计均为正；合并区间含零，剔除各段最好三月后反号。统一同义滞后特征的缺失掩码后点差仍在，观察到的优势涉及整条日分布。',f'''## 四棵树及缺失对照

A用原值；B用当日有观测股的中秩除以有效数加一；C保持当日位置，用等日期、日内股票等权的历史训练分位函数映回原单位；D用训练经验分布固定编码原值。训练、测试的股票日、标签、树配方、缺失单元一致。另一组对20对 `ret_lag/xsret_lag`（第一对另外含 `mom1`）统一原始有效掩码再重复四臂。各臂只以自身训练中位数填补。

{table_for('S2')}

{changes('S2','S2_A','S2_C')} B与C间的净差、D对A的偏移表明分箱、取整、并列与训练参考范围外饱和会改变名单。四种编码均基于实际列顺序，按季度列出训练实值个数、并列、训练分箱、测试边界与范围外股票日；这些控制的合并差小于A−C点估计。边际分布还包括偏度和尾部，本项不能把整条分布归为市场波动水平。

[逐季分箱与并列](../results/S2_bins.csv) · [历史饱和覆盖](../results/encoding_support.csv) · [逐股预测](../results/model_scores.parquet) · [实际逐股成交](../results/orders)''')
    cells=pd.read_csv(RES/'S3_four_cells.csv')
    contrib=cells.groupby('segment')[['level','spread','interaction','joint']].mean()
    leaf=pd.read_csv(RES/'S3_leaf_changes.csv');v=leaf[leaf.arm=='fixed']
    extreme=cells.reindex(cells.joint.abs().nlargest(3).index)
    write('S3','波动水平和离散度的独立贡献','仅改变5、20、60日个股波动的截面中位数与四分位距，树的选股和买单会变化。原值对同时固定两项的费后差前正后负，未见跨段稳定增量。',f'''## 冻结树的四格对照

保留每股对数波动标准化后的截面位置，三列原缺失、零值和其他66列保持原观测。训练日期中位数给定固定水平和宽度；当日剩余分布形状仍保留。原值重构对每个正值检查相对误差≤1e−12，树分数对档案逐行核对。改为全固定后，有{int(v.any_leaf_changed.sum()):,}/{v.stocks.sum():,}个股票日改变至少一棵树的叶子。

{table_for('S3')}

{tab(['阶段','水平贡献','离散度贡献','四格交互','两项贡献之和'],[(names[k],*vals) for k,vals in contrib.iterrows()])}

两项贡献为各自两个边际差的等权均值，两者之和逐月核平联合差；交互单列。绝对变化最大三个月为{'、'.join(f'{r.month}（{r.joint:+.1f} bp）' for r in extreme.itertuples())}。{changes('S3','vol_live','vol_fixed')} 纯树原值的实际成交和原档账户核平。

[逐月四格](../results/S3_four_cells.csv) · [实际叶路径变化](../results/S3_leaf_changes.csv) · [逐列越界](../results/S4_column_support.csv) · [全部股票日四格分数](../results/scale_scores.parquet)''')
    pp=pd.read_csv(RES/'S4_placebo_spread.csv')
    coverage=pd.read_parquet(RES/'scale_scores.parquet',columns=['all_support','main_support'])
    serial=pd.read_csv(RES/'S4_scale_distribution.csv')
    a=serial[serial.arm.eq('live')].groupby('scale').lag1_autocorr.median()
    write('S4','把市场尺度移到较早的日期','全池当日尺度对滞后20日两段都占优，合并区间含零；要求所有干预均在训练支持内后，差额增至约6.56 bp/月。全池相对固定尺度的后段变负，20条错位安慰剂也跨零，登记的整体判据未通过。',f'''## 时间错位和训练支持

三列对数波动的中位数、四分位距六项一起搬移。t−20为主对照；20条路径用种子1–20，对各外层20日块只从季度开始前已结束的20日块抽取。股票日保持当日报价/资格及个股标准化位置。逐列检查训练范围，另对正值完整三维，用训练日以外最近点距离的训练期第99百分位作界。所有25种干预都支持的股票日占{100*coverage.all_support.mean():.2f}%，仅真实、固定和滞后均支持的占{100*coverage.main_support.mean():.2f}%。主支持复验取前者，对原 K 补足。

{table_for('S4')}

{tab(['股票范围','段','当日减安慰剂最小','中位','最大','正值路径/20'],[(('全池' if k[0]=='full' else '共同支持'),names[k[1]],g.net_bp.min(),g.net_bp.median(),g.net_bp.max(),int(g.net_bp.gt(0).sum())) for k,g in pp.groupby(['universe','segment'])])}

六项当日尺度自身滞后1日相关系数的各季中位数介于{a.min():.2f}至{a.max():.2f}。滞后20日仍可共享较长的波动周期。安慰剂共享市场与交易机会，20条路径之间存在相关性。{changes('S4','vol_live','vol_lag20')}

[安慰剂历史来源日期](../results/S4_placebo_dates.parquet) · [各路径全结果](../results/S4_placebo_spread.csv) · [六项分布与自相关](../results/S4_scale_distribution.csv) · [逐股联合支持标记](../results/scale_scores.parquet) · [逐日覆盖及未知](../results/S4_support.parquet) · [逐列单边越界](../results/S4_column_support.csv)''')
    pv=pd.read_csv(RES/'S5_paired_only_contrasts.csv');pv=pv[pv.fee_multiple==1]
    st=pd.read_csv(RES/'S5_state.csv');cv=pd.read_csv(RES/'S5_coverage.csv')
    write('S5','行业与风格相同的资金还有多少差额','严格匹配成功276对，只占行业内分歧席位9.61%。共股等额、未匹配两边持现后，登记全本金的费后差只剩约每月0.17 bp。固定行业与市值构成后，完整状态时钟没有可用日，无法用它识别条件效果。',f'''## 同一预算与可交易支持

行业预算取同日冻结Ridge前K；行业内先保留共同股票，再按自由流通市值及ADV20百分位双重卡尺0.10无放回配对，先最大化对数再最小化距离。两本各自允许成交受限、现金与遗留仓积累。总目标席{cv.K.sum():,}、行业预算后的共同席{cv.common.sum():,}、分歧{cv.disputed.sum():,}、可行边{cv.feasible_edges.sum():,}、配成{cv.matched.sum():,}。行业与股本快照使用历史代理；长期当时首次发布时间未认证。原Z1下高低条件H10在匹配资金上的点差之差前后为−0.45和−0.70 bp，均含零。

{table_for('S5')}

全本金主臂保留共同股票并对未配对份额留现金；“可投资金”给共同股和配成的两边重新等额投资。下表进一步仅保留分歧配对并完全剔除共同股，分别保留原目标席预算与将每次有配对机会的活跃份额全部投给配对股票。二者的复投路径和资金基数均另起账。

{tab(['仅分歧配对的分母','阶段','净差bp/月','95%区间'],[(('原席位预算' if r.method=='budget' else '仅配对席位'),('合计' if r.segment=='all' else names[r.segment]),r.net_bp,f'[{r.lo:.1f}, {r.hi:.1f}]') for r in pv.itertuples()])}

固定状态按上个完整季度的申万一级×自由流通市值三等分权重回建。需要所有正参考权重格均有收益支持；平均参考权重可见{100*st.reference_weight_supported.mean():.2f}%，有完整当日截面IQR的交易日{st.fixed_IQR.count()}个，20日连续均值和再前252日参考时钟都没有有效观测，原Z1同日期比较为0天。原Z1报告仍有观察。可比机会与构成的经济作用未辨明。

[逐股可配席与距离](../results/S5_pairs.parquet) · [每日覆盖](../results/S5_coverage.csv) · [实际持仓市值、流动性及行业](../results/S5_real_holdings.parquet) · [固定构成参考权重覆盖](../results/S5_state.csv) · [隔离配对账户](../results/S5_paired_only_contrasts.csv)''')
    g2=[('mse69','ridge69'),('S2_A','mse69'),('mse78','ridge78'),('original78tree','mse78'),('mse78','mse69'),('ridge78','ridge69'),('shallow','mse69'),('early','mse69'),('shallow_early','mse69'),('S2_A','R')]
    v=pd.read_csv(RES/'shallow_early_folds.csv')
    write('G2','同特征同损失下，线性与树是否随状态互换','69项原值、同样平方损失下，树对Ridge的高低Z1条件H10净差之差前段−18.78 bp、后段+13.52 bp，两段区间均含零。模型形式本身不足以解释登记所问的状态切换。',f'''## 事前状态的主要检验

每个可评信号日以同一初始现金开两本净费H10账户，按入场前Z1分三档。下表给出两模型净差的高档减低档，单位 bp/单次H10。前段高/低334/347个信号，后段168/96个。重叠H10按信号月抽连续三月块；后段有12/10,000次抽样缺高档或低档，仅在可辨识抽样中计算区间。它与滚动十份整账的月差度量不同。

{state_table(g2)}

69和78的普通树、Ridge共用同一训练行、填补和成熟期；原配方树先用内置平方损失20轮，再从该树续训60轮自定义梯度2(p−y)、二阶导数2。两者优化目标都属平方损失，梯度与正则的有效尺度和分阶段训练实现可以改变树。增加9项市场共同列和只改变配方各自列示。“仅深度3”“仅早停”“合并”均从同一普通平方损失69项出发。每季早停以截止前已成熟的最后6个月周样本作验证，再用外层已成熟全样本按所选轮数拟合；内层训练的最大标签到期早于验证起点。联合树23折早停轮数为{v.rounds.min()}–{v.rounds.max()}，历史早期8折另存。

{table_for('G2')}

预定联合树的D5动态减同内折静态权重复验为前段 +1.82、后段 −7.36、合并 −0.65 bp/月，合并95%区间[−3.41, +2.32]。没有从四个树模型中挑胜者。{changes('G2','mse69','ridge69')}

[逐折早停审计](../results/shallow_early_folds.csv) · [早期内折时钟](../results/early_history_folds.csv) · [条件净毛费](../results/state_conditional.csv) · [十个起点](../results/state_offsets.csv) · [联合浅树D5对照](../../state/results/shallow/comparisons.csv)''')
    gg=pd.read_csv(RES/'G3_coefficients.csv');cfs=gg[gg.feature.str.startswith('int_')].groupby('feature').standardized_coefficient.agg(['min','median','max'])
    d5=pd.read_csv(RES/'G3_D5.csv')
    write('G3','Ridge能否直接从离散度学习三个变系数','三项状态交互对同主效应Ridge的月平均差前段 +1.61 bp、后段 −0.48 bp，移动块区间未形成稳定增量。引入状态后确实发生排序变化。',f'''## 去除新增主效应的混淆

固定Ridge78的训练时钟、H10收益秩、正则、折内填补缩放。两臂都加入同日 −mom5、mom20、money_rel20 的中心化截面百分位；交互臂再各乘以 (2Z1−1)。缺特征中心值和缺状态交互回退零。主要对照使用已有相同三项主效应的基础臂；冻结R78另报。

{table_for('G3')}

{tab(['交互项','23折系数最小','中位','最大'],[(name,*[f'{val:.5f}' for val in row]) for name,row in cfs.iterrows()])}

系数是每折标准化后分数的系数。{changes('G3','G3_interaction','G3_main')} 入场时状态的高、低差之差见下表，单位 bp/H10。

{state_table([('G3_interaction','G3_main')])}

相同月份直接对比本轮D5动态账户如下。D5使用原始R、T，当季从此前内折冻结权重；两个比较包含模型及其组合的同时变化。

{table_for('G3',data=d5)}

[各季度系数与状态覆盖](../results/G3_coefficients.csv) · [未知特征与状态回退标记](../results/G3_input_flags.parquet) · [逐股分数](../results/G3_scores.parquet) · [各状态改选席位](../results/seats_by_state.csv) · [逐月D5差](../results/G3_D5.csv)''')
    statuses={'S1':'前段结构关联，后段未辨明','S2':'同掩码历史点差为正，区间跨零且集中','S3':'原尺度与固定尺度整账户跨段变号','S4':'支持子样本有历史线索，全池判据未通过','S5':'匹配分歧有限；固定构成状态无完整参考历史','G2':'同特征同损失的高低状态差未辨明','G3':'状态交互未见跨段稳定增量','A4':'两池分数与实际损益均核平，风险为历史代理'}
    rows='\n'.join('| ['+key+']('+('a4/REPORT.md' if key=='A4' else 'reports/'+key+'.md')+') | '+summary+' |' for key,summary in statuses.items())
    summary=f'''# EP42｜绝对量纲、模型形式与盈利归因的历史回放

407,372个沪深300股票日、23个季度折、1,389个日度评分截面已经完成核对。原值信息影响树的买单，但波动水平与离散度这一组特征的真实时点，对全账户的收益优势没有跨段通过登记条件。按市场状态在Ridge与树间切换，仍以D5主要账户检验判断。两池A4另核对特征、交易时段及风格归因。

| 实验和独立报告 | 本轮判读 |
|---|---|
{rows}

{common}

日度输入按日期、股票编码核对。原Ridge78、原值树69和原配方树78与EP41分数和账户逐日对照，净值、现金、费用及净额交叉最大偏差低于1e−10。S1叶值位于每折原值树存档，叶ID字节串每一个字节对应一棵树，按树序读取。时间窗与实现见各自报告。[账户、持仓批次与路径恒等式](results/account_audit.json) · [账户复核](results/book_parity.csv) · [模型及填补常数](results/models) · [各臂逐月](results/months.csv) · [各段逐年与基准](results/annual_benchmarks.csv) · [原始订单](results/orders) · [结果索引及哈希](results/verification.json)

## 复现

使用主题目录 `.venv/bin/python`。按序运行 `prepare.py`、`joint_tree.py`、`fit_models.py`、`transform_scale.py`、`branches.py`、`interaction.py`、`style.py`、`replay.py`、`trace_origins.py`、`summarize.py`、`paired_only.py`、`ledger_extras.py`、`path_audit.py`、`node_features.py`、`encoding_bins.py`、`decision_capital.py`、`benchmark_scale.py`、`audit_final.py`、`write_reports.py`。早期内折依赖EP42 state的原始季度时钟与每日特征块；A4复现顺序和800实际覆盖见[A4报告](a4/REPORT.md)。原有EP41档案只读。
'''
    (HERE/'REPORT.md').write_text(summary)
    book=pd.read_csv(RES/'book_parity.csv')
    receipt={'stage':'historical_replay','status':statuses,'scores':407372,'folds':23,'dates':1389,'book_parity_max_error':book.max_absolute_error.max(),'models_max_accepted_score_error':1e-10,'strict_fixed_Z1_dates':int(st.fixed_Z1.count()),'scored_arms_on_saved_daily':int(pd.read_csv(RES/'paths.csv').arm.nunique()),'files_sha256':{}}
    for f in sorted([*(f for f in RES.rglob('*') if f.is_file() and f.name!='verification.json'),*HERE.glob('*.py'),*reports.glob('*.md'),HERE/'REPORT.md']):
        receipt['files_sha256'][str(f.relative_to(HERE))]=hashlib.sha256(f.read_bytes()).hexdigest()
    (RES/'verification.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n')
if __name__=='__main__':main()
