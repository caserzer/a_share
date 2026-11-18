"""Four original-E1 state sleeves: monthly win rates/payoff ratios, fixed 1/60."""
import json
import numpy as np
import pandas as pd
import e1_down_down_cap60 as engine
from common import EP, OUT, PRIVATE, sha, save_json

RUN='e1_four_state_odds_20261117'
D=OUT/'diagnostics'/RUN
L=PRIVATE/RUN
R=EP/'reports'/RUN
STATES={'UP_UP':'中期涨、短期涨','UP_DOWN':'中期涨、短期跌','DOWN_UP':'中期跌、短期涨','DOWN_DOWN':'中期跌、短期跌'}

def stats(x):
    x=np.asarray(x,dtype=float)
    assert np.isfinite(x).all()
    win=x>1e-12; loss=x< -1e-12
    w=x[win].mean() if win.any() else np.nan
    l=-x[loss].mean() if loss.any() else np.nan
    return dict(months=len(x),wins=int(win.sum()),losses=int(loss.sum()),zeros=int((~(win|loss)).sum()),win_rate=win.mean() if len(x) else np.nan,mean_win=w,mean_loss=l,payoff_ratio=w/l if l>0 else np.nan,mean_return=x.mean() if len(x) else np.nan)

def main():
    assert not D.exists(), 'Use a new run to preserve completed evidence'
    D.mkdir(parents=True);L.mkdir(parents=True);R.mkdir(parents=True)
    source=PRIVATE/'e1_down_down_account_20261117/selection.parquet'
    s=pd.read_parquet(source)
    known=np.isfinite(s.trend)&np.isfinite(s['short'])
    s['state']='UNCLASSIFIED'
    for state in STATES:
        a,b=state.split('_')
        mask=known & ((s.trend>0) if a=='UP' else (s.trend<0)) & ((s['short']>0) if b=='UP' else (s['short']<0))
        s.loc[mask,'state']=state
    config=dict(allocation='Each selected stock 1/60 of post-fee NAV at original monthly rebalance; remainder cash with zero return; no intra-month cap reset',classification='medium=close[t-5]/close[t-60]-1, short=close[t]/close[t-5]-1; strictly positive/negative; zeros and missing explicitly unclassified',unclassified_rows=int(s.state.eq('UNCLASSIFIED').sum()),sample='Original E1 Q5 only; never fill up a state to 60 names',costs_bps=[10,20],primary_end='2025-03-03',supplement_end='2026-10-16',main_statistic='Complete calendar months; partial endpoint months shown separately in all-month sensitivity',win_definition='Net monthly account return > 1e-12; zero months remain in denominator and are separately counted',payoff_definition='Mean positive monthly return divided by absolute mean negative monthly return; not total gains/total losses',excess='Account monthly net return minus H00300 full-return index monthly return; exposure unmatched, not risk-adjusted alpha',evidence='Descriptive post-selection historical replay; Historical-proxy; month outcomes dependent; no significance claim')
    save_json(D/'config.json',config)
    inherited=json.loads((OUT/'diagnostics/e1_down_down_cap60_20261117/freeze.json').read_text())['files']
    files=inherited+[dict(path=str(p),sha256=sha(p)) for p in [source,EP/'src/e1_four_state_odds.py',D/'config.json']]
    save_json(D/'freeze.json',dict(files=files))
    # Seal all four target schedules before running any new account.
    for state in STATES:
        dest=D/state;ledger=L/state;dest.mkdir();ledger.mkdir()
        t=s.copy();t['selected']=t.state.eq(state);t['weight']=t.selected.astype(float)/60
        assert np.allclose(t.weight.sum(),t.selected.sum()/60)
        t.to_parquet(ledger/'selection.parquet',index=False)
        t.to_csv(dest/'selection.csv',index=False)
        schedule=t.groupby(['signal_date','execution_date'],as_index=False).agg(selected_count=('selected','sum'),stock_target=('weight','sum'))
        schedule['cash_target']=1-schedule.stock_target
        assert schedule.cash_target.min()>=-1e-12
        schedule.to_csv(dest/'schedule.csv',index=False)
        save_json(dest/'freeze.json',dict(files=files))
        save_json(dest/'selection.json',dict(files=[dict(path=str(p),sha256=sha(p)) for p in [ledger/'selection.parquet',dest/'selection.csv',dest/'schedule.csv']]))
    results=[];periods=[];summaries=[]
    for state in STATES:
        engine.D=D/state;engine.L=L/state;engine.CHECKS=[]
        engine.run()
        val=json.loads((engine.D/'validation.json').read_text())
        assert not val['failures']
        f=pd.read_csv(engine.D/'periods.csv');f['state']=state;periods.append(f)
        summary=pd.read_csv(engine.D/'summary.csv');summary=summary[summary.account.eq('CAP60')].copy();summary['state']=state;summaries.append(summary)
        for scope in ['primary','supplement']:
            m=f[f.scope.eq(scope)&f.frequency.eq('M')]
            for sample,z in [('complete_months',m[~m.partial]),('all_months',m)]:
                for outcome,x in [('net',z.CAP60_return),('excess',z.excess_pp/100)]:
                    results.append(dict(state=state,scope=scope,sample=sample,outcome=outcome,**stats(x)))
    allperiods=pd.concat(periods,ignore_index=True);allperiods.to_csv(D/'periods.csv',index=False)
    allsummary=pd.concat(summaries,ignore_index=True);allsummary.to_csv(D/'accounts.csv',index=False)
    result=pd.DataFrame(results);result.to_csv(D/'win_payoff.csv',index=False)
    # Exact regression against previous double-down execution, not just rounded metrics.
    old=pd.read_csv(OUT/'diagnostics/e1_down_down_cap60_20261117/CAP60_daily.csv')
    new=pd.read_csv(D/'DOWN_DOWN/CAP60_daily.csv')
    pd.testing.assert_frame_equal(old,new)
    for state in STATES:
        a=pd.read_csv(D/state/'CAP60_daily.csv')
        assert np.allclose(a.nav.iloc[1:].to_numpy()/a.nav.iloc[:-1].to_numpy()-1,a.daily_return.iloc[1:])
        assert np.isclose(a.nav.iloc[0]-1,a.daily_return.iloc[0])
        m=allperiods[allperiods.state.eq(state)&allperiods.scope.eq('supplement')&allperiods.frequency.eq('M')]
        assert np.isclose((1+m.CAP60_return).prod(),a.nav.iloc[-1])
    save_json(D/'validation.json',dict(status='PASS',double_down_daily_exact_replay=True,all_four_accounts_completed=True,monthly_compounding_reconciled=True,unclassified_rows=config['unclassified_rows']))
    report(result,allsummary,config)
    save_json(D/'delivery.json',dict(files=[dict(path=str(p),sha256=sha(p)) for p in [R/'REPORT.md',D/'win_payoff.csv',D/'periods.csv',D/'accounts.csv',D/'validation.json']]))
    print(result.to_string(index=False),flush=True)

def report(result,summary,config):
    parts=['# E1四种价格状态：每股1/60账户的月度胜率和赔率',
    '本报告统计四个独立账户的自然月表现，不是个股交易胜率，也不是H10事件胜率。每类仅取原E1月初Q5内对应股票，每只配置总资产1/60，剩余留现金，现金收益0；沿用买10/卖20bps及原交易限制。调仓时约束上限，月内允许价格漂移。',
    '中期收益为close[t−5]/close[t−60]−1，短期为close[t]/close[t−5]−1；正为涨、负为跌，恰好零或缺失不硬塞入四类。未分类记录：'+str(config['unclassified_rows'])+'。',
    '胜率=正收益月数/全部纳入月份；零收益月保留分母、单独列出。赔率=盈利月份平均收益/亏损月份平均亏损绝对值，不是总盈利/总亏损。超额使用同月账户净收益减沪深300全收益指数收益，正负同样计算。',
    '主表排除边界不完整自然月：2021年1月；主区间还排除2025年3月（截至3日），延伸区间还排除2026年10月（截至16日）。含部分月结果保留作敏感性对照。']
    for sample in ['complete_months','all_months']:
        for scope in ['primary','supplement']:
            for outcome in ['net','excess']:
                x=result[result['sample'].eq(sample)&result.scope.eq(scope)&result.outcome.eq(outcome)].copy()
                x['state']=x.state.map(STATES)
                for c in ['win_rate','mean_win','mean_loss','mean_return']:x[c]*=100
                parts+=['## '+ ' / '.join([sample,scope,outcome]),x[['state','months','wins','losses','zeros','win_rate','mean_win','mean_loss','payoff_ratio','mean_return']].rename(columns={'state':'类型','months':'月数','wins':'正收益月','losses':'负收益月','zeros':'零收益月','win_rate':'胜率%','mean_win':'平均盈利%或pp','mean_loss':'平均亏损绝对值%或pp','payoff_ratio':'赔率','mean_return':'月均收益%或pp'}).to_markdown(index=False,floatfmt='.3f')]
    z=summary.copy();z['state']=z.state.map(STATES)
    for c in ['total_return','cagr','max_drawdown','average_stock_weight']:z[c]*=100
    parts+=['## 连续账户结果（包含边界部分月）',z[['scope','state','end','total_return','cagr','max_drawdown','average_stock_weight']].to_markdown(index=False,floatfmt='.3f'),
    '## 解释边界','四个账户股票仓位不一样，不能把相对满仓指数的胜率全部解释为选股能力。月胜率/赔率不直接决定复利终值；月份序列、仓位和极端行情都会影响结果。四个独立账户各有自己的净值、现金和交易成本，其收益不能直接相加还原原E1。结果为历史描述，未进行参数搜索，不构成新独立确认。Historical-proxy及停牌估值代理、公司行动边界沿用原实验。',
    '## 文件','- [胜率赔率明细](../../outputs/diagnostics/'+RUN+'/win_payoff.csv)\n- [逐月逐年收益](../../outputs/diagnostics/'+RUN+'/periods.csv)\n- [账户汇总](../../outputs/diagnostics/'+RUN+'/accounts.csv)\n- [核验](../../outputs/diagnostics/'+RUN+'/validation.json)']
    (R/'REPORT.md').write_text('\n\n'.join(parts)+'\n')

if __name__=='__main__':main()
