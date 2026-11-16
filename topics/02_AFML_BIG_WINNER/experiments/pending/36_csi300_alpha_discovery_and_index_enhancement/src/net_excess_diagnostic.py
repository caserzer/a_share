"""Fee-inclusive common-period excess vs CSI300 price and total-return closes.

Starts at the first signal close with strategy capital in cash. Execution remains
next-session open, including initial fees. No total-return open is reconstructed.
This post-delivery diagnostic consumes the original frozen account sensitivities.
"""
import json
from pathlib import Path
import numpy as np,pandas as pd
from common import EP,OUT,PRIVATE,sha,save_json,protocol
from summarize import metrics,returns

MODELS=['E1','E2','E3']

def main():
 dest=OUT/'diagnostics/net_excess_20261116';dest.mkdir(parents=True,exist_ok=True)
 raw=PRIVATE/'net_excess_20261116/H00300.CSI.json';receipt=json.loads(raw.with_suffix('.receipt.json').read_text());assert sha(raw)==receipt['sha256']
 body=json.loads(raw.read_text());assert body['code']==0
 tr=pd.DataFrame(body['data']['items'],columns=body['data']['fields']);assert tr.ts_code.eq('H00300.CSI').all();assert not tr.trade_date.duplicated().any()
 tr['date']=pd.to_datetime(tr.trade_date);tr=tr.set_index('date').sort_index();price=pd.read_parquet(PRIVATE/'market.parquet').close
 accounts={};inputs=[]
 for scenario in ['suspend_flat','suspend_haircut20']:
  for path in ['A','B']:
   for model in MODELS+(['EW'] if path=='A' else ['B0']):
    p=OUT/'sensitivity'/scenario/(path+'_'+model+'.csv');r=json.loads(p.with_suffix('.json').read_text());assert sha(p)==r['nav_sha256']
    a=pd.read_csv(p,parse_dates=['date']).set_index('date');accounts[(scenario,path,model)]=(a,r)
    inputs.append(dict(path=str(p),sha256=sha(p),receipt_sha256=sha(p.with_suffix('.json'))))
 # Common end is determined mechanically by coverage of all requested models and controls.
 common_end=min(a.index.max() for a,r in accounts.values())
 first_execution=max(a.index.min() for a,r in accounts.values())
 anchor=price.index[price.index<first_execution][-1]
 assert anchor==pd.Timestamp('2021-01-08') and first_execution==pd.Timestamp('2021-01-11')
 rows=[];annual=[];curves=[]
 for (scenario,path,model),(account,r) in accounts.items():
  for scope,end in [('common',common_end),('available',account.index.max())]:
   a=account.loc[first_execution:end];ix=a.index
   assert price.reindex(ix).notna().all() and tr.close.reindex(ix).notna().all()
   assert a.iloc[0].fees>0 or a.loc[a.buy.gt(0)].fees.gt(0).any()
   for benchmark,series in [('CSI300_PRICE',price),('CSI300_TOTAL_RETURN',tr.close)]:
    b=series.reindex(ix)/series.loc[anchor];m=metrics(a.nav,b)
    row=dict(scenario=scenario,path=path,model=model,scope=scope,benchmark=benchmark,signal_close_anchor=anchor,first_execution=first_execution,end=end,sessions=len(ix),**m)
    row.update(buy_fee_bps=protocol()['costs_bps']['main'][0],sell_fee_bps=protocol()['costs_bps']['main'][1],fees_in_initial_capital_units=a.fees.sum(),gross_buy_over_nav=a.buy.sum(),gross_sell_over_nav=a.sell.sum(),mean_cash=a.cash_weight.mean(),skipped_B_targets=int(a.target_status.fillna('').str.contains('UNKNOWN|MISMATCH|OUTSIDE').sum()),account_data_end=account.index.max(),account_valuation_blocked=bool(r['failures']),quality='HISTORICAL_PROXY_WITH_EXPLICIT_SUSPENSION_MARKS',annualization_sessions=252)
    rows.append(row)
    if scope=='common':
     rr=returns(a.nav);br=returns(b)
     for year,g in rr.groupby(rr.index.year):
      own=(1+g).prod()-1;bench=(1+br.loc[g.index]).prod()-1
      annual.append(dict(scenario=scenario,path=path,model=model,benchmark=benchmark,year=year,start=g.index.min(),end=g.index.max(),sessions=len(g),portfolio_return=own,benchmark_return=bench,return_difference=own-bench,relative_return=(1+own)/(1+bench)-1,partial_calendar_year=(year in [2021,2025])))
     for d in ix:curves.append(dict(scenario=scenario,path=path,model=model,benchmark=benchmark,date=d,net_nav=a.loc[d,'nav'],benchmark_nav=b.loc[d],relative_nav=a.loc[d,'nav']/b.loc[d]))
 summary=pd.DataFrame(rows);summary.to_csv(dest/'summary.csv',index=False);pd.DataFrame(annual).to_csv(dest/'annual.csv',index=False);pd.DataFrame(curves).to_parquet(dest/'common_curves.parquet',index=False)
 # Price vs total-return basis independently recorded, no OHLC imputation.
 binfo=dict(anchor=anchor,end=common_end,price_start=price.loc[anchor],price_end=price.loc[common_end],total_return_start=tr.loc[anchor,'close'],total_return_end=tr.loc[common_end,'close'],total_return_open_missing=int(tr.open.isna().sum()),open_not_used=True,total_return_source_sha256=sha(raw))
 save_json(dest/'benchmark_audit.json',binfo)
 save_json(dest/'manifest.json',dict(post_delivery_diagnostic=True,models_retrained=False,costs_changed=False,mark_rule_changed=False,start_clock='first signal close; capital remains cash until next market open; all initial fees retained',common_end_rule='minimum available end across E1/E2/E3 and EW/B0 in both existing suspension scenarios',common_end=common_end,account_inputs=inputs,total_return_source_receipt=receipt,script_sha256=sha(EP/'src/net_excess_diagnostic.py'),summary_sha256=sha(dest/'summary.csv'),annual_sha256=sha(dest/'annual.csv'),curves_sha256=sha(dest/'common_curves.parquet'),official_index_identity_source='https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/000300factsheet.pdf'))
 selected=summary.loc[summary.scenario.eq('suspend_flat')&summary.scope.eq('common')&summary.model.isin(MODELS)]
 print(selected[['path','model','benchmark','end','cagr','benchmark_cagr','cagr_difference','relative_nav_cagr','information_ratio','active_ci_low','active_ci_high']].to_string(index=False))
 def pct(v):return f'{v:.2%}'
 lines=['# E1/E2/E3 扣费后相对沪深300超额测算','',f'统一起点为 {anchor.date()} 信号日收盘，组合当时持现金；{first_execution.date()} 开盘建仓，初始费用保留。统一终点 {common_end.date()}，共 {len(price.loc[first_execution:common_end])} 个市场交易日。终点由所有模型和对照的可估值范围决定，未按收益选择。','', '主成本：买入 10 bps、卖出 20 bps，包含滑点/冲击代理，按实际成交金额扣费。每周次一市场开盘执行；A 是 Q5 等权长仓，B 是约束增强代理。使用已登记的全天停牌上一报价估值，最长 20 市场日；另列 20% 折价情景。没有改动特征、模型或封存预测。','', '|路径|模型|组合净年化|沪深300价格指数年化|对价格指数年化差|全收益指数年化|对全收益指数年化差|全收益相对净值年化|','|---|---|---|---|---|---|---|---|']
 for path in ['A','B']:
  for model in MODELS:
   q=selected.loc[selected.path.eq(path)&selected.model.eq(model)].set_index('benchmark');pr=q.loc['CSI300_PRICE'];tt=q.loc['CSI300_TOTAL_RETURN']
   lines.append('|'+ '|'.join([path,model,pct(tt.cagr),pct(pr.benchmark_cagr),pct(pr.cagr_difference),pct(tt.benchmark_cagr),pct(tt.cagr_difference),pct(tt.relative_nav_cagr)])+'|')
 lines+=['','“年化差”=组合 CAGR−指数 CAGR；“相对净值年化”=(组合净值/指数净值)^(252/N)−1，两者不同。CAGR 采用固定 252 交易日约定。不是风险调整回归截距 alpha。','', '## 逐年：相对全收益指数的收益率差','', '|年度|A-E1|A-E2|A-E3|B-E1|B-E2|B-E3|','|---|---|---|---|---|---|---|']
 af=pd.DataFrame(annual);af=af.loc[af.scenario.eq('suspend_flat')&af.benchmark.eq('CSI300_TOTAL_RETURN')&af.model.isin(MODELS)];wide=af.pivot(index='year',columns=['path','model'],values='return_difference')
 for year,r in wide.iterrows():lines.append('|'+str(year)+('（部分）' if year in [2021,2025] else '')+'|'+'|'.join(pct(r[(path,model)]) for path in ['A','B'] for model in MODELS)+'|')
 lines+=['','## 解释边界','', '- 主表可以回答在这些已披露代理假设下的扣费后超额，不是对原严格账户阻断的消除。主表所有模型使用相同完整比较区间。','- 沪深300全收益指数 H00300 包含分红再投资；本次新增读取该指数的实际收盘数据。没有使用或虚构其缺失开盘值。价格指数与含分红基准分别列出，避免将分红差异全算成选股贡献。','- 股票端仍是前复权收益与合成单位账户，不是完整现金分红及换股权益账本，不能据此宣称严格同口径实盘收益。','- 2025-03-04 起，E1、EW 及 B 路径涉及海通证券的终值/换股估值缺口。E2/E3 的更长可用区间另存在 summary.csv 的 available 行，不用来替代共同区间比较。','- B 为月度权重重建代理，部分调仓在基准信息缺失时跳过；未证明所有历史权重的发布时间。','- 20% 停牌折价结果、年度收益、IR/TE/时间块区间见同目录 CSV。区间采用日主动收益的 65 个交易日时间块，不能把其区间当成 CAGR 差的区间。','', '[官方指数身份及全收益代码](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/000300factsheet.pdf)。数据由现有 Tushare index_daily 权限取得，原响应与哈希留在 private/net_excess_20261116。']
 (dest/'REPORT.md').write_text('\n'.join(lines)+'\n')
if __name__=='__main__':main()
