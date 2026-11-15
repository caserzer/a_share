"""Versioned current dictionary and completion evidence audit; no model fitting."""
import copy
from common import *

def run():
 out=ROOT/'outputs/r34';out.mkdir(exist_ok=True);source=ROOT/'outputs/r23/current_factor_dictionary.json';rows=copy.deepcopy(json.loads(source.read_text()));by={x['factor']:x for x in rows}
 eps=by['fixed_fy_eps_revision'];eps.update(implemented='historical_proxy_tested_partial_coverage',formula='同公司同机构固定FY EPS对称修正(new-old)/(abs(new)+abs(old))；公司机构中位数再行业成员中位数',source='R24来源隔离、R28完整缓存报告屏障、R29 EPS独立行业聚合',aggregation='R29 EPS自身覆盖母体，FY0/FY1分开；不能与R25不同利润母体比较归因',missing_rule='最新报告<=180日；紧邻前报告间隔<=365日；缺失/冲突中间报告不跨越；零分母未知；严格>=5公司及80%，部分覆盖单列',conclusion='R28共同EPS/利润样本训练不足；R29一级部分覆盖两版本各8拟合，主20日MSE未改善、未建立稳定增量，停止参数扩展',monitor_scope='研究输入；未替换现行利润监控',evidence_refs=['protocols/r28.json','outputs/r28/verification.json','protocols/r29.json','outputs/r29/verification.json','outputs/r29/paired_increments.csv'])
 h=by['breadth21/breadth63'];h['conclusion']+='；R31加入规模控制的收益增量未建立；R32分类未达预定标准，二级反转有限正证据月份不足；R33固定退出未建立价值';h['evidence_refs']+=['outputs/r31/verification.json','outputs/r31/increments.csv','outputs/r32/verification.json','outputs/r32/increments.csv','outputs/r33/verification.json','outputs/r33/paired_policy.csv']
 s=copy.deepcopy(by['log_members']);s.update(factor='typical_member_log_market_cap',theory='典型成员规模风格可能混淆扩散与收益/反转关系',formula='前月行业成员中，当月正有效总市值自然对数的中位数',direction='控制变量，模型估计方向',source='EP32 extension_v2股票月末未复权价格乘生效日股本；R30聚合',economic_date='月末股票市值',publication_date='价格收盘；股本只有生效日，首次披露未知',available_at='Historical-proxy；股本known_at缺失，不能认证严格PIT',historical_revisions='股本/成员初始版本和修订链未知',aggregation='先成员log市值中位数，再同日同行业层完整母体中心秩；训练期标准化',missing_rule='当月精确日期、正价/股本、在市；至少5有效公司和80%覆盖，否则未知，不带值',failure_condition='股本时点、成员修订和选择性覆盖；单一规模不能替代全风格',implemented='historical_proxy_control',conclusion='R30覆盖核查；R31/R32同样本控制已运行，无稳定新增预测能力声明',replication_status='EP35必要控制，不是方正69项完整复现',monitor_scope='R31/R32研究模型输入，未替换生产或现有监控',dictionary_origin='R30-R33',evidence_refs=['protocols/r30.json','outputs/r30/verification.json','outputs/r31/verification.json','outputs/r32/verification.json'])
 rows.append(s)
 for row in rows:row['evidence_sha256']={ref:sha(ROOT/ref) for ref in row['evidence_refs']}
 js(out/'current_factor_dictionary.json',rows)
 audit=json.loads((ROOT/'outputs/completion_audit.json').read_text());items=[]
 for item in audit['items']:
  refs=[]
  for ref in item['evidence']:
   path=ROOT/ref;refs.append(dict(path=ref,exists=path.exists(),sha256=sha(path) if path.is_file() else None))
  items.append(dict(requirement=item['requirement'],status=item['status'],evidence=refs,unresolved=item['remaining'],completion_proven=False))
 js(out/'requirements_evidence.json',dict(overall_status='active_not_complete',items=items,interpretation='existence and hashes confirm traceability, not scientific completion; each unresolved scope remains open'))
 current=json.loads((ROOT/'outputs/current_sources.json').read_text());current['selected']['current_factor_dictionary']={'path':'outputs/r34/current_factor_dictionary.json','sha256':sha(out/'current_factor_dictionary.json')};current['pending']='R28-R33 EPS/size/exit comparisons completed without established stable increment; original release history, continuous industry variables, complete styles, investability and prospective validation remain open';js(ROOT/'outputs/current_sources.json',current)
 js(out/'receipt.json',dict(previous_dictionary_sha256=sha(source),dictionary_sha256=sha(out/'current_factor_dictionary.json'),entries=len(rows),changes=['EPS tested status corrected','diffusion size-control/exit evidence added','size control factor added'],no_new_performance_claim=True,code_sha256=sha(__file__)))
 assert len(rows)==17 and len({(x['module'],x['factor']) for x in rows})==17 and set(x['module'] for x in rows)==set('ABCDEFGH')
 assert all(x['exists'] for i in items for x in i['evidence'])
 js(out/'verification.json',dict(status='PASS',entries=17,requirements=len(items),evidence_links=sum(len(i['evidence']) for i in items),strict_pit_promotions=0))
 print('R34 reconciled',len(rows),'dictionary entries,',len(items),'requirements')
if __name__=='__main__':run()
