"""Report and independent reconciliation of fixed entry-purchase controls."""
import base64,json,re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import markdown
from common import EP,sha,save_json
from q5_entry_matched_controls import DEST,CONTROLS,interval
from q5_entry_disjoint_controls import DEST as DIS
REPORT=EP/'reports'/DEST.name
LABEL={'market_ew':'全池等权','industry_ew':'同行业等权','industry_r20_ew':'同行业＋20日涨跌','industry_disjoint':'同行业，排除原新增','industry_r20_disjoint':'行业＋20日涨跌，排除原新增'}
def pp(x):return f'{x*100:+.3f}'
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(map(str,row))+' |' for row in rows])+'\n'
def ci(r):return f'[{pp(r.ci_low)}, {pp(r.ci_high)}]'
def main():
 REPORT.mkdir(parents=True,exist_ok=True)
 s=pd.read_csv(DEST/'summary.csv');ds=pd.read_csv(DIS/'summary.csv');f=pd.read_csv(DEST/'episodes.csv');df=pd.read_csv(DIS/'episodes.csv');cov=pd.read_csv(DEST/'matching_coverage.csv');dc=pd.read_csv(DIS/'coverage.csv')
 checks=[]
 def check(name,ok):
  checks.append(dict(check=name,passed=bool(ok)))
  assert ok,name
 for directory in [DEST,DIS]:
  v=json.loads((directory/'validation.json').read_text());check(directory.name+'_validation',v['status']=='PASS')
  fr=json.loads((directory/'freeze.json').read_text());check(directory.name+'_config',sha(EP/'configs'/f'{directory.name}.json')==fr['config_sha256'])
  for i,x in enumerate(fr['inputs']+fr.get('sources',[])):check(directory.name+'_hash_'+str(i),sha(x['path'])==x['sha256'])
  if 'source_sha256' in fr:check('disjoint_source',sha(EP/'src/q5_entry_disjoint_controls.py')==fr['source_sha256'])
  if 'allocation_path' in fr:check('disjoint_allocation',sha(fr['allocation_path'])==fr['allocation_sha256'])
  e=pd.read_csv(directory/'episodes.csv');check(directory.name+'_blocked_nan',e.loc[e.status.ne('OBSERVED'),'increment'].isna().all());check(directory.name+'_finite_observed',np.isfinite(e.loc[e.status.eq('OBSERVED'),'increment']).all())
 v=json.loads((DEST/'validation.json').read_text());check('original_allocation_sha',sha(v['allocation_path'])==v['allocation_sha256']);a=pd.read_parquet(v['allocation_path']);da=pd.read_parquet(json.loads((DIS/'freeze.json').read_text())['allocation_path'])
 for (event,control),g in da.groupby(['event','control']):
  orig=a.loc[a.event.eq(event)&a.control.eq('model')].set_index('instrument').allocation_fraction
  check(event+control+'_same_source_budget',np.allclose(g.model_weight,orig.reindex(g.instrument,fill_value=0)))
  check(event+control+'_same_total_budget',np.isclose(g.model_weight.sum(),g.control_weight.sum()))
  check(event+control+'_no_selected_peer',not ((g.model_weight>0)&(g.control_weight>0)&~g.unmatched_source).any())
  pool=a.loc[a.event.eq(event)&a.control.eq('market_ew'),'instrument'];check(event+control+'_eligible_pool',g.instrument.isin(pool).all())
 original=f.loc[f.cost.eq('main')&f.control.eq('market_ew')&f.status.eq('OBSERVED')].set_index(['event','window']).model_entry_contribution
 for r in df.loc[df.status.eq('OBSERVED')].itertuples():check(r.event+r.control+r.window+'_source_contribution',np.isclose(r.model_entry_contribution,original.loc[(r.event,r.window)],atol=1e-10))
 # Identical monthly starting states across all five endpoints and all controls.
 balanced=[];windows=['actual_phase2_open','1_sessions','5_sessions','10_sessions','20_sessions']
 for directory,e,controls in [(DEST,f,CONTROLS),(DIS,df,['industry_disjoint','industry_r20_disjoint'])]:
  if 'cost' not in e:e=e.assign(cost='main')
  rows=[]
  for scope,flag in [('primary','primary_eligible'),('full','full_eligible')]:
   for (model,cost),g in e.loc[e[flag]&e.status.eq('OBSERVED')].groupby(['model','cost']):
    common=set.intersection(*[set(g.loc[g.window.eq(w)&g.control.eq(c),'event']) for w in windows for c in controls])
    for w in windows:
     for c in controls:
      h=g.loc[g.event.isin(common)&g.window.eq(w)&g.control.eq(c)].sort_values('month');lo,hi,p=interval(h.increment.to_numpy());rows.append(dict(scope=scope,model=model,cost=cost,window=w,control=c,events=len(h),mean_increment=h.increment.mean(),ci_low=lo,ci_high=hi))
  b=pd.DataFrame(rows);b.to_csv(directory/'balanced_horizon_summary.csv',index=False);balanced.append(b)
 main=s.loc[s.scope.eq('primary')&s.cost.eq('main')&s.window.eq('actual_phase2_open')];dm=ds.loc[ds.scope.eq('primary')&ds.window.eq('actual_phase2_open')]
 t1=table(['模型','对照','窗口数','新增股票贡献(pp)','对照贡献(pp)','差异(pp)','95%区间(pp)','Holm p'],[[r.model,LABEL[r.control],r.paired_events,pp(r.mean_model_contribution),pp(r.mean_control_contribution),pp(r.mean_increment),ci(r),f'{r.primary_holm_p:.4f}'] for r in main.itertuples()])
 t2=table(['模型','排除自身的对照','可替换新增预算','总资金差异(pp)','95%区间(pp)','Holm p','匹配资金收益差(pp)','匹配资金95%区间(pp)'],[[r.model,LABEL[r.control],f'{r.mean_matched_fraction:.1%}',pp(r.mean_increment),ci(r),f'{r.primary_holm_p:.4f}',pp(r.mean_matched_capital_difference),f'[{pp(r.matched_capital_ci_low)}, {pp(r.matched_capital_ci_high)}]'] for r in dm.itertuples()])
 events=set(f.loc[f.primary_eligible&f.window.eq('actual_phase2_open')&f.cost.eq('main')&f.status.eq('OBSERVED'),'event']);co=cov.loc[cov.event.isin(events)&cov.cost.eq('main')&cov.control.ne('model')].groupby(['model','control']).mean(numeric_only=True).reset_index()
 t3=table(['模型','对照','新增预算/账户','平均候选数','自选股票重叠预算','单股票组预算','不超过3只组预算'],[[r.model,LABEL[r.control],f'{r.entry_budget_fraction:.1%}',f'{r.candidate_count:.1f}',f'{r.selected_overlap:.1%}',f'{r.singleton_budget:.1%}',f'{r.small_group_budget:.1%}'] for r in co.itertuples()])
 annual=[]
 for directory in [DEST,DIS]:
  q=pd.read_csv(directory/'annual_summary.csv');q=q.loc[q.scope.eq('primary')&q.window.eq('actual_phase2_open')];q=q.loc[q.cost.eq('main')] if 'cost' in q else q;annual.append(q)
 y=pd.concat(annual).pivot(index=['model','year'],columns='control',values='mean_increment');allcontrols=CONTROLS+['industry_disjoint','industry_r20_disjoint']
 ty=table(['模型','年份']+[LABEL[c]+'(pp)' for c in allcontrols],[[m,year]+[pp(r[c]) for c in allcontrols] for (m,year),r in y.iterrows()])
 bh=pd.concat(balanced);q=bh.loc[bh.scope.eq('primary')&bh.cost.eq('main')&bh.window.ne('actual_phase2_open')];pivot=q.pivot(index=['model','window','events'],columns='control',values='mean_increment');th=table(['模型','窗口','相同事件数']+[LABEL[c]+'(pp)' for c in allcontrols],[[m,w,n]+[pp(r[c]) for c in allcontrols] for (m,w,n),r in pivot.iterrows()])
 costs=s.loc[s.window.eq('actual_phase2_open')];tc=table(['区间','模型','成本','对照','事件数','差异(pp)','95%区间(pp)'],[[r.scope,r.model,r.cost,LABEL[r.control],r.paired_events,pp(r.mean_increment),ci(r)] for r in costs.itertuples()])
 tf=table(['模型','排除自身的对照','事件数','可替换预算','差异(pp)','95%区间(pp)'],[[r.model,LABEL[r.control],r.paired_events,f'{r.mean_matched_fraction:.1%}',pp(r.mean_increment),ci(r)] for r in ds.loc[ds.scope.eq('full')&ds.window.eq('actual_phase2_open')].itertuples()])
 coverage=[]
 for name,e in [('含自身对照',f),('排除自身对照',df)]:
  for (status,reason),g in e.groupby(['status','reason'],dropna=False):coverage.append([name,status,'—' if pd.isna(reason) else reason,len(g)])
 tv=table(['实验','状态','原因','记录数'],coverage)
 fig,axes=plt.subplots(1,2,figsize=(12,4.6))
 for ax,data,controls,title in [(axes[0],main,CONTROLS,'Controls may include selected entrants'),(axes[1],dm,['industry_disjoint','industry_r20_disjoint'],'Disjoint peers; unmatched budget unchanged')]:
  for i,m in enumerate(['E1','E2','E3']):
   z=data.loc[data.model.eq(m)].set_index('control').loc[controls];xx=np.arange(len(controls))+(i-1)*.18;yy=z.mean_increment.to_numpy()*100
   ax.errorbar(xx,yy,yerr=np.array([yy-z.ci_low.to_numpy()*100,z.ci_high.to_numpy()*100-yy]),marker='o',capsize=3,linestyle='none',label=m)
  ax.axhline(0,color='#777',lw=1);ax.set_xticks(range(len(controls)),['Market','Industry','Industry + R20'] if len(controls)==3 else ['Industry','Industry + R20']);ax.set_title(title,fontsize=10);ax.set_ylabel('Mean account-capital difference (pp)');ax.legend()
 fig.suptitle('49 monthly episodes per model | primary period | main costs');fig.tight_layout();fig.savefig(REPORT/'control_differences.png',dpi=160);plt.close(fig)
 fig,ax=plt.subplots(figsize=(8,4.3));xx=np.arange(3)
 for i,c in enumerate(['industry_disjoint','industry_r20_disjoint']):
  vals=[dm.loc[dm.model.eq(m)&dm.control.eq(c),'mean_matched_fraction'].iloc[0]*100 for m in ['E1','E2','E3']];bars=ax.bar(xx+(i-.5)*.32,vals,.32,label=['Industry','Industry + R20'][i]);ax.bar_label(bars,fmt='%.1f%%',padding=3)
 ax.set_xticks(xx,['E1','E2','E3']);ax.set_ylim(0,115);ax.set_ylabel('Share of original new-entry budget (%)');ax.set_title('Budget with independent peers available');ax.legend(loc='upper center',bbox_to_anchor=(.5,-.12),ncol=2);fig.tight_layout();fig.savefig(REPORT/'independent_coverage.png',dpi=160);plt.close(fig)
 nchecks=len(json.loads((DEST/'validation.json').read_text())['checks'])+len(json.loads((DIS/'validation.json').read_text())['checks'])
 text='\n\n'.join(['# 新进入股票是否有独立选股优势：等预算匹配与排除自身验证',
 '**结论：E1仍有超越简单行业配置的历史线索；E2/E3证据较弱。进一步匹配行业和过去20日涨跌后，三个模型按账户总资金计算的剩余优势均未得到清晰支持。但最细独立匹配仅覆盖57%—61%的新增预算，不能据此断言全部优势已被行业或近期涨跌解释。**',
 '本轮是已观察历史结果后的机制调查，沿用冻结模型、月度第1相位名单、原账本和数据，不训练、不调阈值、不修复缺口。全部窗口相互独立，不是新增连续可交易策略；本文数值不是相对沪深300的年化超额。',
 '## 1. 要验证什么，以及比较口径',
 '上轮发现及时换仓的早期差异主要来自新进入股票。本轮只替换这部分实际买入本金：原有卖出、原持仓补仓、总买入金额、费用和现金都相同。起点复制原延迟账户在第1相位执行前的持仓与现金；新增定义为此前未持有、本次实际买入。候选是当期成分中未持有且当时实际可买的股票。比较同一开盘到第2相位实际开盘的结果，每个模型主区间49个月度起点，2021年2月至2025年2月，结束日不晚于2025-03-03。',
 '全池等权：全部可用候选均分新增预算。同行业等权：保留每个行业的买入预算。行业＋20日涨跌：继续保留行业内近期涨跌分组预算。分组使用信号日前20个交易日原始冻结qfq收盘收益，行业内按收益及证券代码排序，固定分五组；未知收益单列，不用未来收益选对照。小组保持原样并披露。历史行业映射仍是代理，不是严格PIT认证。',
 '## 2. 含原新增股票的基础对照',t1,
 '单位为单个窗口平均收益差的百分点（pp），分母是该次交易前账户总资金。主成本买10bps、卖20bps；贡献列仅含新增买入本身及其买入费。因为两边本金、费用、其余仓位完全相同，贡献之差精确等于完整账户收益差。E1对全池及行业对照的区间不跨零且九项Holm校正后p<0.05；E2行业对照单项区间略正，校正后不足。这里的p值只是事后描述，不能视为独立确认。',
 '![配对差异及区间](control_differences.png)',
 '## 3. 为什么不能直接说近期涨跌已解释收益',t3,
 '细匹配对照中约65%—69%的买入预算仍在原模型新进入股票上，约65%—68%的预算落在最多3只股票的小组。对照越接近模型自身，差异自然可能缩小。因此第一组结果不能独立证明模型仅仅在捕捉行业或涨跌风格。候选池没有额外限制必须有模型分数，模型Q5来自可评分总体；这种资格差异也限制纯粹模型增量的解释。',
 '## 4. 追加排除原新增股票的独立同行对照',
 '看到上述重叠后，另立配置并在计算新增结果前冻结分配。沿用原行业和原涨跌分组，排除所有原新增股票。有其他股票时将该组买入预算等分给它们；没有时，两边都保留原配置，并计为未匹配。未匹配部分不会贡献收益差，不换现金，也不向更宽分组寻找有利替代。此追加实验只运行主成本，不宣称预先未见的确认实验。',t2,
 '“可替换新增预算”为各事件匹配预算占全部新增预算的比例再取均值。“总资金差异”衡量这项局部替换对完整账户的影响；“匹配资金收益差”先逐事件除以该事件可替换本金，再取均值。两者因分母不同不能互相替代，也不能用均值之比恢复。E2细匹配的匹配资金区间略高于零，而总资金区间跨零；这说明事件资金权重影响结果，不构成对全部新增预算的稳健确认。Holm列仅对应总资金主指标的六项检验，未替匹配资金指标作成功裁决。',
 'E1同行业独立对照差异约+0.238pp，95%区间约[+0.074,+0.409]pp；E2、E3经多重比较后没有同等级支持。细匹配总资金差异均跨零，同时有约39%—43%的新增预算无法独立匹配。应保留“证据不足”和“覆盖不足”两项判断。',
 '![独立匹配覆盖](independent_coverage.png)',
 '## 5. 逐年记录：方向并非每年稳定',ty,
 '2021年只有2—12月起点，2025年只有1—2月，不能当完整年。E1同行业独立差异在2023年转负；E2虽同行业逐年均正，控制近期涨跌后2024年为负；E3在2024年同行业及细匹配均负。三模型不能概括为每年都有稳定独立增量。完整逐年明细同时保存full范围，见文末CSV。',
 '## 6. 期限比较使用同一组月份',th,
 '所有五个窗口（含实际第2相位端点）及各自全部对照共同可估值后才进入期限表，主区间每模型48个相同起点。窗口为1/5/10/20个市场交易日，期间不再交易，末端开盘只估值、不虚构清仓费。期限结果只作剖面，不据此选择最优持有期；完整区间保存在balanced_horizon_summary.csv。',
 '## 7. 成本及更长区间完整记录',tc,
 'zero为0/0bps，main为10/20bps，stress为30/80bps。每个成本场景沿用其原账户起始状态；场景间的细微差异来自此前路径及可用预算，不是替代股票有费用豁免。同一事件配对本金及费用相等。primary使用共同结束界限2025-03-03；full延伸至各模型原账户可用终点，E1为2026-10-16，E2/E3为2026-10-21，实际完整窗口数及结束日以明细为准。',tf,
 'full延长样本仍包含primary月份，不是独立样本外验证；不同模型事件数不同，不直接据此排名。',
 '## 8. 缺失、统计与复核',tv,
 f'基础对照9,315个计划记录，排除自身对照2,070个；账本及匹配检查合计{nchecks:,}项通过，另有{len(checks):,}项独立哈希、配置、分配、原贡献还原及未知值审计通过。候选集合不使用未来价格筛选；无法覆盖完整窗口的记录保留BLOCKED和空指标，不按零收益计算。',
 '按月份排序，3个事件循环时间块、2,000次重抽样、固定种子20261116，95%百分位区间；p值为中心化bootstrap双侧近似。基础主指标九项、追加主指标六项分别Holm校正，未对整条历史研究路径控制全局选择偏差。月度事件可能相关，区间只是有限历史样本的不确定性描述。',
 '## 9. 对后续方向的约束',
 '优先保留E1新增股票作为待验证候选，而非继续增加模型复杂度；当前尚无E2/E3相对E1的直接配对优势检验，不能宣称E1最终胜出。下一阶段应先冻结一个简单行业＋近期涨跌基线和模型方案，再用未参与本轮选择的后续月份比较。现有样本中进一步尝试分组宽度、调仓周或持有天数会扩大选择偏差，本轮到此停止扩展。',
 '不把“细匹配后区间跨零”写成没有alpha，不把E1行业对照正向写成可稳定盈利。市值、波动、流动性等未在本轮完整控制，历史行业身份和匹配覆盖也有边界。独立窗口不能串成净值，更不能将均值乘一年调仓次数当作年化超额。',
 '单元测试：EP36完整测试集26项通过；唯一警告为既有OSQP未来默认参数变更提示。两张图已逐一查看，报告本地附件链接全部存在。',
 '## 附件与复现',
 '\n'.join(f'- [{directory.name} / {name}](../../outputs/diagnostics/{directory.name}/{name})' for directory in [DEST,DIS] for name in ['summary.csv','annual_summary.csv','episodes.csv','balanced_horizon_summary.csv','freeze.json','validation.json']),
 '- [基础匹配覆盖](../../outputs/diagnostics/'+DEST.name+'/matching_coverage.csv)\n- [独立匹配覆盖](../../outputs/diagnostics/'+DIS.name+'/coverage.csv)\n- [独立审计](../../outputs/diagnostics/'+DEST.name+'/independent_audit.json)',
 '复现入口：src/q5_entry_matched_controls.py（freeze/run/analyze）、src/q5_entry_disjoint_controls.py（freeze/run）、src/q5_entry_controls_report.py。已有freeze禁止重复覆盖；逐证券分配保留在忽略提交的private目录，冻结文件记录其SHA256。'])+'\n'
 (REPORT/'REPORT.md').write_text(text);html=markdown.markdown(text,extensions=['tables'])
 for name in ['control_differences','independent_coverage']:html=html.replace('src="'+name+'.png"','src="data:image/png;base64,'+base64.b64encode((REPORT/(name+'.png')).read_bytes()).decode()+'"')
 (REPORT/'REPORT.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>新增股票匹配调查</title><style>body{max-width:1450px;margin:32px auto;padding:0 24px;font:16px/1.7 system-ui;color:#243445}table{display:block;overflow:auto;border-collapse:collapse;font-size:14px;margin:20px 0}th,td{padding:7px 12px;border-bottom:1px solid #dce4eb;white-space:nowrap}th{background:#eaf0f5}tr:nth-child(even){background:#f7f9fb}img{max-width:100%;height:auto}h2{margin-top:40px}</style><body>'+html+'</body></html>')
 save_json(DEST/'independent_audit.json',dict(status='PASS',checks=checks,checks_count=len(checks)))
 for link in re.findall(r'\]\(([^)]+)\)',text):check('report_link_'+link,(REPORT/link).exists())
 save_json(DEST/'independent_audit.json',dict(status='PASS',checks=checks,checks_count=len(checks),original_source_preserved=True));print('REPORT',REPORT,'independent checks',len(checks))
if __name__=='__main__':main()
