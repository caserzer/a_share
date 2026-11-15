"""Attach tested realization and tradability limits to the current research registry."""
import copy
from common import *
ROUTES={'current_factor_dictionary':'outputs/r92/current_factor_dictionary.json','current_requirements_evidence':'outputs/r92/requirements_evidence.json','forecast_realization_common_events':'outputs/r90/summary.json','forecast_horizon_price_comparison':'outputs/r91/summary.json','stock_path_partial_bounds':'outputs/r83/summary.json'}
def run():
 out=ROOT/'outputs/r92';out.mkdir(exist_ok=True);old=ROOT/'outputs/r75/current_factor_dictionary.json';rows=copy.deepcopy(json.loads(old.read_text()));refs=[f'outputs/r{n}/verification.json' for n in range(84,92)]
 for x in rows:
  if x['factor']=='same_broker_fixed_FY_profit_revision':
   x['realization_evidence']='R84—R90最终年度财务缓存兑现实验；R90共同1718对，当前年五年均缩小平均固定尺度误差，次年四年缩小、2021年扩大；595对尚未成熟保留未知'
   x['price_horizon_evidence']='R91全2313报告对不按实际成熟筛选；4247行业事件，4031/3909有后20/60日价格；SW2021两期限整体方向得分均负，期限差异跨年不稳定，非独立增量'
   x['realization_formula']='|F_after-A|-|F_before-A|，同一分母|F_before|+|A|；公司年度内平均再公司等权；实际缓存仅用于事后评价，不进入信号'
   x['realization_limit']='最终缓存不是首次披露；财务修订、共同样本选择、短期信息吸收和重复事件不提供因果或配置证明'
   x['branch_decision']='停止无新依据的期限/窗口搜索；保留兑现证据，未接受为预测或配置能力'
   x['evidence_refs']=list(dict.fromkeys(x['evidence_refs']+refs));x['evidence_sha256'].update({p:sha(ROOT/p) for p in refs})
 js(out/'current_factor_dictionary.json',rows);a=copy.deepcopy(json.loads((ROOT/'outputs/r75/requirements_evidence.json').read_text()))
 changes={
 '上涨持续性':('R84—R90已评价盈利预期向最终实际收敛；未建立持续行情或机制因果证据。仍缺首次披露实际、长时序产业兑现与独立前瞻。',range(84,92)),
 '预期与价格先后关系优先实验':('R84—R91补齐当年/次年兑现与同母体价格比较；当年误差改善不能推导价格领先。既有月末及事件研究未建立稳定独立增量；完整风格、源语义与前瞻仍缺。',range(84,92)),
 '配置价值与风险':('R76已算目标股票权重距离，非真实换手；R77—R82仅4完整每日路径区间、5完整端点区间，不能拼完整策略曲线；R83未覆盖权重保留未知及条件下界。成交、退市/停牌处置、全风格与执行成本仍未证明。',range(76,84)),
 '一级二级三级分别研究':('一级股票路径核验仅少量区间完整；二三级R91价格期限比较分层且未建立稳定增量；SW2014一级、一级校准与全层实际执行仍缺。',range(76,92)),
 '经济假说与完整因子字典交付':('保留24条原字典，更新预期修正的兑现/价格边界，不新增或认证成功因子。原69项定义、其它产业机制、首次版本与独立验证仍缺。',range(84,92)),
 '数据可追溯与PIT补充':('R76—R91已追溯股票路径缺失、报告配对、年度实际及原NAV窗口；没有修复未覆盖路径，也没有认证最终缓存为初发PIT。原始版本链、其它语义与完整可投资身份仍缺。',range(76,92))}
 for x in a['items']:
  x['completion_proven']=False
  if x['requirement'] in changes:
   message,rounds=changes[x['requirement']];x['unresolved_at_R75']=x['unresolved'];x['unresolved']=message
   existing={e['path'] for e in x['evidence']}
   for n in rounds:
    p=f'outputs/r{n}/verification.json'
    if p not in existing:x['evidence'].append(dict(path=p,exists=True,sha256=sha(ROOT/p)))
 a['interpretation']='R92: 24 evidence entries; realization is not price leadership, synthetic returns are not executable returns; all16 requirements remain incomplete';js(out/'requirements_evidence.json',a)
 current=json.loads((ROOT/'outputs/current_sources.json').read_text())
 for k,p in ROUTES.items():current['selected'][k]=dict(path=p,sha256=sha(ROOT/p))
 current['pending']='Realization and same-population horizon price evidence registered; tradability gaps retained. Three-task calibration and update engineering require current-state audit; full PIT, reference replication, other mechanisms, execution and forward validation remain unresolved.';js(ROOT/'outputs/current_sources.json',current)
 js(out/'receipt.json',dict(previous_dictionary_sha256=sha(old),dictionary_sha256=sha(out/'current_factor_dictionary.json'),amended=['same_broker_fixed_FY_profit_revision'],routes=ROUTES,code_sha256=sha(__file__),status='active_not_complete'));print('R92 registered24 entries; one amended, no predictive promotion')
if __name__=='__main__':run()
