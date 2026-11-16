"""Monthly records from frozen daily accounts; never fill stopped accounts."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import markdown
from common import EP, PRIVATE, sha, save_json
from q5_rebalance_sensitivity import DEST

TARGET = DEST / 'monthly_records'
REPORT = EP / 'reports/q5_rebalance_20261116/monthly_records'

def main():
    TARGET.mkdir(exist_ok=True); REPORT.mkdir(exist_ok=True)
    period = json.loads((DEST/'comparison_periods.json').read_text())
    anchor = pd.Timestamp(period['signal_close_anchor'])
    market = pd.read_parquet(PRIVATE/'market.parquet').sort_index()
    source_path = PRIVATE/'net_excess_20261116/H00300.CSI.json'
    raw = json.loads(source_path.read_text())['data']
    tr = pd.DataFrame(raw['items'], columns=raw['fields'])
    tr = tr.assign(date=pd.to_datetime(tr.trade_date)).set_index('date').sort_index().close
    months = pd.period_range(anchor, market.index.max(), freq='M')
    rows=[]; checks=[]; inputs={str(source_path):sha(source_path)}
    for rp in sorted((DEST/'accounts').glob('*.json')):
        receipt=json.loads(rp.read_text()); cp=rp.with_suffix('.csv')
        assert sha(cp)==receipt['nav_sha256']
        inputs[str(cp)]=sha(cp); inputs[str(rp)]=sha(rp)
        f=pd.read_csv(cp,parse_dates=['date']).set_index('date').sort_index()
        assert f.index.is_unique and f.nav.notna().all()
        nav=pd.concat([pd.Series([1.], index=[anchor]), f.nav])
        bench=tr.reindex(nav.index); assert bench.notna().all()
        own_ret=nav.pct_change().iloc[1:]; bench_ret=bench.pct_change().iloc[1:]
        observed=[]
        for month in months:
            g=f.loc[f.index.to_period('M')==month]
            base={k:receipt[k] for k in ['account','valuation','model','frequency','cost']}
            base.update(month=str(month), sessions=len(g))
            if g.empty:
                base.update(status='BLOCKED', note='账户中止后无收益记录', failure=receipt['failures'])
            else:
                first,last=g.index.min(),g.index.max()
                before=nav.index[nav.index<first][-1]
                n0,n1=float(nav.loc[before]),float(nav.loc[last])
                b0,b1=float(bench.loc[before]),float(bench.loc[last])
                full=market.index[market.index.to_period('M')==month]
                reasons=[]
                if first!=full.min():reasons.append('首月自建仓日起')
                if last<full.max():reasons.append('账户中止月')
                if month==market.index.max().to_period('M') and market.index.max()<month.end_time.normalize():reasons.append('数据截止月')
                ret=n1/n0-1; br=b1/b0-1
                base.update(base_date=str(before.date()),start=str(first.date()),end=str(last.date()),nav_start=n0,nav_end=n1,benchmark_start=b0,benchmark_end=b1,net_return=ret,benchmark_return=br,excess_difference=ret-br,relative_return=(1+ret)/(1+br)-1,status='PARTIAL' if reasons else 'FULL',note='；'.join(reasons) or '完整月')
                assert np.isclose((1+own_ret.loc[g.index]).prod()-1,ret,atol=1e-12)
                assert np.isclose((1+bench_ret.loc[g.index]).prod()-1,br,atol=1e-12)
                observed.append(base)
            rows.append(base)
        assert np.isclose(np.prod([1+x['net_return'] for x in observed]),f.nav.iloc[-1],atol=1e-11)
        checks.append(dict(account=receipt['account'],monthly_chain_matches_nav=True,observed_months=len(observed),end=str(f.index.max().date())))
    allrows=pd.DataFrame(rows)
    primary=allrows.loc[allrows.valuation.eq('suspend_flat')&allrows.cost.eq('main')].copy()
    primary=primary.sort_values(['month','model','frequency']).reset_index(drop=True)
    assert len(primary)==70*9 and len(allrows)==70*81
    # Independent reconciliation with already delivered annual returns.
    annual=pd.read_csv(DEST/'annual_performance.csv')
    for keys,g in allrows.dropna(subset=['net_return']).groupby(['valuation','model','frequency','cost']):
        a=annual.loc[annual.benchmark.eq('CSI300_TOTAL_RETURN')]
        for col,v in zip(['valuation','model','frequency','cost'],keys):a=a.loc[a[col].eq(v)]
        for year,h in g.groupby(g.month.str[:4]):
            expected=a.loc[a.period.astype(str).eq(year)].iloc[0]
            assert np.isclose((1+h.net_return).prod()-1,expected.portfolio_return,atol=1e-11)
            assert np.isclose((1+h.benchmark_return).prod()-1,expected.benchmark_return,atol=1e-11)
    allrows.to_csv(TARGET/'all_81_accounts_monthly.csv',index=False,encoding='utf-8-sig')
    primary.to_csv(TARGET/'primary_9_accounts_monthly.csv',index=False,encoding='utf-8-sig')
    save_json(TARGET/'monthly_validation.json',dict(status='PASS',primary_rows=len(primary),all_rows=len(allrows),checks=checks,annual_reconciliation='PASS',inputs=inputs))
    clean=json.loads(primary.to_json(orient='records',double_precision=15))
    save_json(TARGET/'workbook_data.json',clean)
    lines=['# E1、E2、E3 完整逐月收益记录','',
        '范围：2021-01 至 2026-10，共70个月、9个主口径账户、630条记录。沿用 Q5 等权，买入10bps、卖出20bps，已确认停牌旧收盘估值代理；不改变原始预测或账户。月度调仓指自然月首个可用周信号后的下一交易日。','',
        '每月收益＝本月最后可用净值／上月最后净值−1；首月以2021-01-08收盘初始资金1为基准，含首次建仓费用。基准为同起止日期的沪深300全收益指数 H00300；超额为当月净收益减基准收益，以百分点表示，不是年化收益。','',
        '“*”表示部分月份：2021-01从1月11日建仓起；E1周度／双周2025-03仅到3月3日，此后为“—”；E1月度2026-10仅到10月16日；E2/E3的2026-10仅到10月21日。“—”是未知，不是0收益。不同账户的部分月份不可直接横比。','',
        '全部81成本／估值分支的逐月记录另附CSV。月收益逐日复利、全期净值及原有年度记录均已核对通过。','',
        '[Excel收益表](../../../outputs/sensitivity/q5_rebalance_20261116/monthly_records/E1_E2_E3_monthly_returns.xlsx) · [9账户明细CSV](../../../outputs/sensitivity/q5_rebalance_20261116/monthly_records/primary_9_accounts_monthly.csv) · [81分支CSV](../../../outputs/sensitivity/q5_rebalance_20261116/monthly_records/all_81_accounts_monthly.csv) · [原敏感性报告](../REPORT.html)','']
    labels={'1w':'每周调仓','2w':'双周调仓','1m':'每月调仓'}
    for freq,label in labels.items():
        lines+=['## '+label,'','| 月份 | E1净收益 | E1超额(pp) | E2净收益 | E2超额(pp) | E3净收益 | E3超额(pp) |','|---|---:|---:|---:|---:|---:|---:|']
        for month in months:
            cells=[str(month)]
            for model in ['E1','E2','E3']:
                r=primary.loc[primary.month.eq(str(month))&primary.model.eq(model)&primary.frequency.eq(freq)].iloc[0]
                suffix='*' if r.status=='PARTIAL' else ''
                cells += ['—','—'] if r.status=='BLOCKED' else [f'{r.net_return:.2%}{suffix}',f'{100*r.excess_difference:+.2f}{suffix}']
            lines.append('| '+' | '.join(cells)+' |')
        lines+=['']
    lines+=['## 精确起止日期与基准','', '下表收益为小数原值，例如0.01表示1%；缺失显示为“—”。','',primary[['month','model','frequency','base_date','end','net_return','benchmark_return','excess_difference','status','note']].fillna('—').to_markdown(index=False,floatfmt='.6f')]
    content='\n'.join(lines)+'\n'; (REPORT/'MONTHLY.md').write_text(content)
    body=markdown.markdown(content,extensions=['tables'])
    (REPORT/'MONTHLY.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>完整逐月收益记录</title><style>body{max-width:1400px;margin:30px auto;padding:0 22px;font:16px/1.65 system-ui;color:#253344}table{border-collapse:collapse;display:block;overflow:auto;margin:20px 0;font-size:14px}th,td{padding:7px 12px;border-bottom:1px solid #dde3e8;white-space:nowrap}th{background:#eaf0f5}tr:nth-child(even){background:#f7f9fb}h2{margin-top:40px}</style><body>'+body+'</body></html>')
    print('PASS:',len(primary),'primary monthly rows;',len(allrows),'all-branch rows')

if __name__=='__main__':main()
