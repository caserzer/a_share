"""Register accounting evidence without promoting it to predictive factors."""
import copy
from common import *
ROUTES={'current_factor_dictionary':'outputs/r75/current_factor_dictionary.json','current_requirements_evidence':'outputs/r75/requirements_evidence.json','accounting_historical_monitor':'outputs/r74/evidence_matrix.parquet','accounting_monthly_evidence':'outputs/r73/industry_evidence.json','accounting_source_clock':'outputs/r72/coverage.json','accounting_contemporaneous_controls':'outputs/r71/summary.json'}
SPECS=[('long_asset_cash_spending_yoy_direction','B','两期购建固定资产、无形资产和其他长期资产支付现金严格比较大小；不同比例化、不年化','资本投入与未来供给/需求的候选机制，方向不预设为利好','R67/R68覆盖较高；R69—R71同期兑现分歧，不能等同产能或未来收益','负现金支付排除；同日冲突含缺失保持未知'),('inventory_turnover_days_yoy_evidence','B','同报告期存货周转天数配对；仅来源覆盖审计，未形成当前有效行业信号','库存与收入成本周转的会计代理，不是实物库存数量','R67半年报3573个当期发行人同日冲突；R68半年报各层0行业通过覆盖门槛，不回退一季报','非正值与冲突保留未知；极大正值未截尾，需分母核验'),('capital_cashflow_profit_joint_evidence','B/C','共同六值：两期资本支付、经营现金流、归母利润；支出增加者分利润现金流同升、同降或分歧，比例分母明确','检验投资活动是否同期兑现，并保留反证；非阶段概率','R70/71非金融同期诊断：增加者存在反证但不比非增加者更差；无因果或领先预测证据','现金流/利润负值有效；利润两期报表类型1且公司类型1；最新冲突不回退')]
def run():
 out=ROOT/'outputs/r75';out.mkdir(exist_ok=True);source=ROOT/'outputs/r66/current_factor_dictionary.json';rows=copy.deepcopy(json.loads(source.read_text()));refs=[f'outputs/r{n}/verification.json' for n in range(67,75)]
 for factor,module,formula,theory,conclusion,missing in SPECS:
  rows.append(dict(factor=factor,module=module,theory=theory,formula=formula,direction='无统一收益排序方向，仅分维度会计证据',applicable_industries='SW2021各层分开；原始覆盖保留全目录，交叉经营解释排除同月银行/非银金融；非金融不等于实物生产行业',economic_date='2025/2026一季报和半年报，只有四经济期；六个月快照不独立',publication_date='归档提供商ann_date/f_ann_date代理，首次发布/修订未认证',available_at='最大公告日期的下一交易日；实际归档时间单列，历史截面归档可用为0',frequency='季度/半年累计会计口径，月末观察',source='R03本地provider_responses.zip和冻结历史成员，R67—R74核验',historical_revisions='同截止日重新选最新版本，同日冲突未知；禁止9月版本倒填',aggregation='行业至少5共同成员且>=80%完整分母；同比同季末；统计各层独立不相加',missing_rule=missing,failure_condition='仅短期同期样本；行业口径/会计分母/支付节奏/首发版本缺失；不得外推配置能力',implemented='historical_accounting_evidence_not_predictive_factor',conclusion=conclusion,mechanism_status='同期机制线索和反证，不证明因果',replication_status='EP35扩展；不是方正69项完整复现',dictionary_origin='R67-R74',monitor_scope='R74保守自然季度切换；新期未知不回填，旧快照不当当前；无部署',strict_pit_certified=False,evidence_refs=refs,evidence_sha256={p:sha(ROOT/p) for p in refs}))
 js(out/'current_factor_dictionary.json',rows);a=copy.deepcopy(json.loads((ROOT/'outputs/r66/requirements_evidence.json').read_text()))
 for x in a['items']:
  x['completion_proven']=False
  revisions={
   '为什么上涨：经济机制与反证':'宏观代理与产业/会计同期诊断已执行，因果机制未证实；仍缺更长供需、价差、库存、产能及首发修订证据。',
   '何时结束：风险和错误退出':'R33/R48/R57固定退出代价已核查，未建立改善；真实成交、完整风格与独立前瞻仍未证明。',
   '基准因子增量优先实验':'R31规模与R55市场控制收益、R32/R56独立分类已执行，未建立稳定增量；完整风格、非价格覆盖、严格时点与独立样本仍缺。',
   '预期与价格先后关系优先实验':'R24源错误隔离及R25/R26重放完成；R27固定规则审计、R28样本门槛、R29自身同样本收益已执行且主20日无改善。原始版本链、其它语义错误、完整风格与前瞻仍缺。',
   '行业监控与更新流程':'R74已接入会计证据及最新期/旧快照状态；仍仅冻结历史重放，实时来源、完整阶段识别、前瞻与另行授权的生产部署未完成。'
  }
  if x['requirement'] in revisions:
   x['unresolved_at_R66']=x['unresolved'];x['unresolved']=revisions[x['requirement']]

  if x['requirement'] in ['为什么上涨：经济机制与反证','产业领先变量优先实验','数据可追溯与PIT补充','经济假说与完整因子字典交付','行业监控与更新流程']:
   x['accounting_progress']='R67—R74会计代理来源、成员、同期对照与逐月时钟/过期规则完成；仅机制观察，未建立预测或配置价值'
   x['evidence'] += [dict(path=p,exists=True,sha256=sha(ROOT/p)) for p in refs]
  if x['requirement']=='经济假说与完整因子字典交付':x.update(status='24_entry_dictionary_with_accounting_evidence',unresolved='24条不等于24个已验证预测因子；原69项定义、其它产业序列、首发修订与独立验证仍缺')
 a['interpretation']='R75: all16 overall requirements unproven; accounting evidence progress is not full goal completion';js(out/'requirements_evidence.json',a)
 current=json.loads((ROOT/'outputs/current_sources.json').read_text())
 for key,path in ROUTES.items():current['selected'][key]=dict(path=path,sha256=sha(ROOT/path))
 current['pending']='Accounting mechanisms observed with contemporaneous controls and proxy clocks only; longer independent periods, first releases, other industrial supply/demand, complete styles, tradability, reference replication and forward validation remain open.';js(ROOT/'outputs/current_sources.json',current)
 js(out/'receipt.json',dict(previous_dictionary_sha256=sha(source),dictionary_sha256=sha(out/'current_factor_dictionary.json'),old_entries=21,new_entries=3,routes=ROUTES,code_sha256=sha(__file__),status='active_not_complete'));print('R75 registered24 entries,21 unchanged')
if __name__=='__main__':run()
