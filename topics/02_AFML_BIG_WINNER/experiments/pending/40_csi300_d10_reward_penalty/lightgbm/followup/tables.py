"""Readable result tables from the saved ledgers. All contrasts are within calendar and fee."""
from common_inputs import *
def csv(n):return pd.read_csv(DEST/(n+'.csv'))
def table(f):
    a=f.copy().reset_index()
    if 'index' in a:a=a.drop(columns='index')
    def show(v):
        if isinstance(v,(np.floating,float)):return '—' if pd.isna(v) else f'{v:,.2f}'
        return str(v)
    head='| '+' | '.join(a.columns.map(str))+' |'
    return '\n'.join([head,'|'+('|'.join(['---']*len(a.columns)))+'|',*['| '+' | '.join(show(v) for v in row)+' |' for row in a.itertuples(index=False,name=None)]])
def main():
    buf=['# EP40 分组实验明细','主段为 100 个 H10，后段为 39 个 H10。表内收益差默认按窗口算术平均，单位为 bp/H10。区间采用连续三个窗口的循环时间块。历史回放使用研究时能够重建的供应商资料。']
    def section(title,explanation,frame):buf.extend(['## '+title,explanation,table(frame)])
    w=csv('paired');b=w.query('h==10 and phase==0 and delay==0 and mul==1')
    for name,items in [('原相位持仓',['B-R','T-R','A-R','C-T','B-A','R-E','B-V','B-J','R-U','T-U','B-U']),('固定换股两端',['X10-X00','X01-X00','Xinteraction','X11-R']),('行业复制与特征删列',['B-BI','B-BIV','T-TI','T-TIV','market_interaction','G1-R','G2-G1','T-G2','T-no_dd','T-no_amp','T-no_path']),('训练配方与标签',['F01-F00','T-F10','F10-F00','T-F01','recipe_interaction','T-T20','T-leaf100','T-l2_5'])]:
        section(name,'gross_bp 为毛差，fee_bp 为费用差。正费用差表示多付费用。holm 仅用于已登记比较族。',b[b.contrast.isin(items)][['scope','contrast','n','wins','gross_bp','fee_bp','net_bp','lo','hi','lo6','hi6','holm']])
    phases=w.query('h==10 and delay==0 and mul==1 and contrast in ["T-R","B-R","A-R","X11-R"]').pivot(index=['scope','phase'],columns='contrast',values='net_bp')
    trial=csv('challenge_phase').query('mul==1').pivot(index=['scope','phase'],columns='arm',values='bp')
    section('十个调仓起点','每个起点从整笔资金独立起账。右三列均减同起点 R。sector_swap 只允许同行业替换，X1169 用 69 项树替换约五席。',phases.join(trial))
    section('持有期和延迟','每种期限与同期限 Ridge 比较。延迟保留相同原信号和完整 H10。',w.query('phase==0 and mul==1 and contrast in ["T-R","B-R","X11-R"]')[['scope','h','delay','contrast','n','net_bp','lo','hi']])
    section('费用压力','以不同费率独立成交。mul 取 0、1、2 分别为零费、标准和双费。',w.query('phase==0 and h==10 and delay==0 and contrast in ["T-R","B-R","X11-R"]').pivot(index=['scope','contrast'],columns='mul',values='net_bp'))
    dc=csv('decay').groupby(['scope','arm'])[['first','second','third','weight','covered_weight']].mean()
    for c in ['first','second','third']:dc[c]=(dc[c]-dc.xs('R',level='arm')[c])*1e4
    section('信号何时兑现','固定实际初始持股与单位数，只保留有共同 H20 端点的信号。三段毛贡献差以窗口初始本金为分母。',dc)
    section('完整月份对全收益指数的风险','active_mean_annual、tracking_error、monthly_intercept 为小数收益单位，下表统一转换为百分数。beta 为对 Ridge 月收益差相对于指数月收益的斜率。',csv('monthly_risk').merge(csv('regression_ci'),on=['scope','arm','n']).assign(**{c:lambda g,c=c:g[c]*100 for c in ['active_mean_annual','tracking_error','monthly_intercept','alpha_low','alpha_high']}))
    section('三个月集中度','各账户在相同保留月份复利，单位为收益率百分点。',csv('concentration').query('excluded in ["best1","best3"]'))
    reg=csv('regime').query('arm in ["B","T","X11"]')
    section('市场状态','up/down 取信号日指数 20 日收益符号。high/low 取该折已成熟训练日期的波动率中位数。',reg)
    rng=csv('random_controls').groupby('scope').b_minus_p_bp.quantile([.05,.5,.95]).unstack()
    section('200 个随机换入账户','每个日期、种子和股票代码按 SHA-256 排序。表为 B 减随机路径的 5%、50%、95% 分位，所有路径保留 B 与 R 的共同席位。',rng)
    section('按已实现十分位解释利润','每笔持仓按窗口期初本金计，gross_bp 是各组对 R 的整个账户毛差。0 为未知标签。',csv('bridge').query('arm in ["B","T","X11"]').groupby(['scope','arm','bucket']).gross_delta.sum().mul(1e4).unstack('bucket'))
    section('实际资金偏好的股票','按实际权重统计信号日全池特征百分位，数值越大代表特征值越高。',csv('styles').query('arm in ["R","T","B","X11"]'))
    earlier=csv('earlier_scores')
    section('向更早年份复验','2019、2020 年独立起账。每个相位的完整年内窗口计算净差，表给十起点中位数及正差数。这是较早的历史检验。',earlier.groupby(['year','arm']).bp.agg(median='median',positive=lambda x:sum(x>0),worst='min',best='max'))
    section('冻结后迁移到新股票池','同一段只保留四组均可估值的窗口，缺口后重新起账。全800的指数为 H00906.CSI。',csv('wide/summary').query('size=="D10"').pivot(index=['pool','scope','n'],columns='arm',values='net_bp'))
    (ROOT/'TABLES.md').write_text('\n\n'.join(buf)+'\n')
if __name__=='__main__':main()
