"""Publish coverage and all eight source comparisons, preserving the three segment clocks."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
OUT=Path(__file__).resolve().parent
DIRECTIONS={
    'less_down_5':'5日下行半方差占比低',
    'less_down_20':'20日下行半方差占比低',
    'positive_skew_5':'5日盘中正偏度',
    'close_above_vwap_5':'收盘高于日内VWAP',
    'positive_open30_5':'前半小时收益高',
    'up_amount_5':'上涨时段成交额占比高',
    'positive_ret_volume_corr_5':'收益和成交量相关为正',
    'daily_ohlcv_proxy_5':'日线下行半方差代理',
}
def main():
    receipts=pd.read_json(OUT/'five_minute_receipts.jsonl',lines=True)
    agg=pd.read_parquet(OUT/'five_minute_daily.parquet')
    assert len(receipts)==761 and receipts.days.sum()==len(agg)
    assert set(agg.n.unique())=={48} and not agg.duplicated(['instrument','date']).any()
    c=pd.read_csv(OUT/'coverage.csv')
    d=pd.read_parquet(OUT/'daily.parquet')
    q=d.groupby(['segment','arm']).agg(net=('nav','last'),fees=('fee','sum'),gross=('gross_pnl','sum'),start=('date','min'),end=('date','max'))
    q['net']-=1
    assert np.max(abs(q.net+q.fees-q.gross))<1e-10
    q.to_csv(OUT/'segment_accounts.csv')
    gap=q.unstack('arm').net
    row=c[c.spec=='less_down_5'];cov=row.covered.sum()/row.reserves.sum()
    match=c.groupby('spec').changes.sum()
    comp=pd.read_csv(OUT/'comparisons.csv').query('base=="rank"').set_index(['arm','segment'])
    gaps=[float(comp.at[('less_down_5',i),'net_bp']) for i in [1,2,3]]
    docs=['# N1｜用盘中量价重排沪深300候补',
       f'在三个预定历史区间，用5分钟数据计算过去5个交易日的下行半方差占比，优先选择下行占比较低的候补。相对相同核心仓、买入预算和成交条件的 Ridge 顺位，每个区间共同完整月的净差依次为 **{gaps[0]:+.2f}、{gaps[1]:+.2f}、{gaps[2]:+.2f} bp/月**。每段从该区间第一个交易日另起账，完整月指标排除首月起账影响；三段均只有两个可比完整月。下表另列含起账月的整个区间累计净差，单位为 bp。[区间和费用](segment_accounts.csv) · [逐月](monthly.csv) · [配对月均差](comparisons.csv)',
       '| 独立更改的信号 | 2021-02至04 | 2023-07至09 | 2025-04至06 | 变更买入席次 |\n|---|---:|---:|---:|---:|']
    for k,label in DIRECTIONS.items():
        x=(gap[k]-gap['rank'])*10000
        docs[-1]+=f'\n| {label} | {x.loc[1]:+.1f} | {x.loc[2]:+.1f} | {x.loc[3]:+.1f} | {match[k]} |'
    funds=pd.read_csv(OUT/'outcome_funds.csv').query('spec=="less_down_5"')
    amounts=funds[funds.changed].groupby('segment').executed_net_buy.sum().reindex([1,2,3],fill_value=0)
    denominator=funds.groupby('segment').executed_net_buy.sum()
    proportions=amounts/denominator
    detail='，'.join(f'{amounts.at[i]:.4f}（该段全部候补实际净买入额的{proportions.at[i]:.1%}）' for i in [1,2,3])
    docs.append('**实际改变的资金。** 每段初始本金为1，首项信号改变证券后实际对外新增净买入的累计金额依次为'+detail+'。同股票跨期反复买入会累计；每笔按跨袖抵消后的实际金额计入。真实D1、D10及中间档资金在逐项明细中列示。')
    docs += [f'**覆盖。** 从登记的三个严格区间，各取起点后前三个完整日历月。每段都选当时完整的沪深300候补档，查询本段每只实际候补需要的最长20日连续回看。共 {len(receipts):,} 个证券区间、{int(receipts.rows.sum()):,} 根原始5分钟记录，{len(agg):,} 个完整股票日，来自{agg.instrument.nunique()}只证券。再用信号日未复权收盘核价，容差0.011元，单列冲突与缺原收盘的股票日。首项在 {len(row)} 个信号日的 {row.reserves.sum():,} 个候补股票日中覆盖 {row.covered.sum():,} 个（{cov:.2%}），可评分的冻结原买入席次为 {row.covered_slots.sum()} / {row.base_slots.sum()}。缺测个股保留原顺位；每项只改变原可评分的买单位。[原始查询与摘要哈希](five_minute_receipts.jsonl) · [收盘价核对](close_checks.csv) · [各日资金支持](coverage.csv)',
       '**信号与成交。** 两个连续交易时段以各自开盘计首根收益，去掉午休和隔夜跳空。无成交时段收益设为0，全日零成交或缺48根完整时段不参与评分。日内相对收益避免跨日除权跳变；H10账本仍用经公司行动处理的原复权价格。波动、5日涨幅、20日日均额按同日合格池分位，两候补三项差均不超过0.20；匹配范围是本次将登记“相近”具体化的执行选择。每个原买单位可保留自身，尽量选择信号较优者，组内无放回。半方差按负收益平方和除以总平方和，偏度按全部5日时段收益中心矩。开盘半小时、收盘相对全日成交金额/股数的VWAP、量价相关取过去5个日值均值，上涨成交额比例取5日合计。主方向和六项次要方向逐一比较；日线代理取相同5日分钟支持上的收盘收益平方比例。涨量比仅代表成交时段代理。以上为短样本 Historical-proxy。[逐证券分数和席位](choices.parquet) · [真实D1/D10与净买入资金](outcome_funds.csv) · [实际订单](orders.parquet)',
       '**1分钟记录。** Tushare 对2023-01-05单只股票返回241条，进一步查询完整回看时账户依次返回每分钟1次、每小时1次的频率限制。三段每日候补的28日前向分块共需1,498次；另冻结每段第一候补日风险匹配对的6次取数方案，当前未取得足以配对的1分钟回看。上述账户全部使用独立的 BaoStock 5分钟历史，不将1分钟探针计入。未覆盖的年月与1分钟规格仍待检验。[Tushare探测](../provider_probes.json) · [限频记录](one_minute_limits.json) · [匹配对日期](pilot_design.csv) · [独立5分钟探针](baostock_probe.json)',
       '复算时先用 BaoStock 的 Python 包运行 `fetch5.py`，得到聚合与回执；运行 `run.py` 与上级目录的 `execution_audit.py n1` 后，再运行 `summarize_results.py`。已存汇总可直接进入后两步。[执行回执](verification.json)']
    (OUT/'REPORT.md').write_text('\n\n'.join(docs)+'\n')
    named=[p for p in OUT.iterdir() if p.is_file() and p.name!='verification.json']
    named+=[OUT.parent/'execution_audit.py',OUT.parent/'reserves.py',OUT.parents[1]/'p2/results/scores.parquet']
    (OUT/'verification.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in named},indent=2)+'\n')
if __name__=='__main__':main()
