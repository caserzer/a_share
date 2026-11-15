"""Register valuation diagnostic evidence without certifying historical availability."""
import copy
from common import *
REFS=[f'outputs/r{x}/verification.json' for x in range(113,119)]
ROUTES={'current_factor_dictionary':'outputs/r119/current_factor_dictionary.json','current_requirements_evidence':'outputs/r119/requirements_evidence.json','latest_stage_requirements_audit':'outputs/r119/requirements_evidence.json','valuation_basis_and_financial_timing':'outputs/r119/branch_evidence.json'}

def run():
    out=ROOT/'outputs/r119';out.mkdir(exist_ok=True)
    results={p:json.loads((ROOT/p).read_text()) for p in REFS}
    assert all(x['status']=='PASS' for x in results.values())
    rows=copy.deepcopy(json.loads((ROOT/'outputs/r112/current_factor_dictionary.json').read_text()))
    common=dict(direction='诊断变量，不设统一正负收益预测方向',applicable_industries='各分类/层级分别统计；不能外推未覆盖行业',frequency='月末',publication_date='最终历史缓存；首次发布版本未恢复',historical_revisions='保留历史代理和双时钟；不按匹配率选择时钟',missing_rule='未知不填零；完整母体保留，子集不冒充全行业',implemented='historical_diagnostic_verified',mechanism_status='未证明领先性、独立预测、因果机制或配置价值',replication_status='EP35扩展诊断，不是方正完整复现',dictionary_origin='R113-R118',monitor_scope='研究诊断；未替换冻结模型',strict_pit_certified=False,evidence_refs=REFS,evidence_sha256={p:sha(ROOT/p) for p in REFS})
    rows.append(dict(common,factor='price_pe_implied_earnings_decomposition',module='G/C',theory='资产定价的盈利与估值区分；代数分解只能提出解释问题',formula='Δlog(raw)=Δlog(PE)+Δlog(raw/PE)；Δlog(cap)=Δlog(PE)+Δlog(cap/PE)；另列股本变化和复权调整差额',economic_date='相邻完整月末，固定上月行业成员',available_at='精确日期历史价格/PE/股本代理；不是当时发布版本证明',source='R112精确PE股票面板；R113口径审计；R114固定成员聚合',aggregation='正PE/原价双端点；>=5成员且>=80%完整分母为子集诊断；仅100%完整可填全篮子算术量。平均对数分解不等于算术收益贡献',failure_condition='非正PE不可取对数；股本/复权变化、缺失成员和Jensen效应可破坏朴素经济解释',conclusion='恒等式与聚合核验通过，隐含盈利不等于独立披露利润；不能由恒等式推出盈利驱动'))
    rows.append(dict(common,factor='reported_ttm_vs_pe_implied_profit_diagnostic',module='C/G',theory='经营盈利与估值分母应区分，报告期选择和历史修订可能制造表观背离',formula='非年末TTM=当期YTD+上一年年报−上年同期YTD；年末取年报；比较cap/PE与TTM，对称距离2|a-b|/(|a|+|b|)，零零为0',economic_date='财务报告所属期；比较日期为完整月末',available_at='公告代理取全部组成NOTICE；修订代理取全部NOTICE/UPDATE最大值，均下一交易日；先选最新可见报告期再检验组成，不退旧成功值',source='R115本地1647财务分区；R116最新期；R117历史代码/上市；R118双时钟比较',aggregation='股票月诊断先月内等权再跨月等权；同样本并列两时钟和同/不同报告期；非正利润保留，不用PE一致度筛样本',failure_condition='财务分区不足、组成冲突、旧报告、缺首发版本、共享供应商谱系；较高一致率不认证PIT或领先性',conclusion='93530共同对中10078同报告期值完全一致；83452不同期，主要体现选期差异。公告匹配较好不能用于选钟或首发认证'))
    js(out/'current_factor_dictionary.json',rows)
    req=copy.deepcopy(json.loads((ROOT/'outputs/r112/requirements_evidence.json').read_text()))
    updates={
      '为什么上涨：经济机制与反证':'R113-R118完成价格/PE/股本/复权与财务TTM口径诊断，代数和一致性不证明经济驱动；下一项实际披露盈利变化的固定母体覆盖。',
      '经济假说与完整因子字典交付':'保留25条，新增2条估值/财务诊断共27条；不代表27个有效因子，完整69项及缺失机制仍未完成。',
      '数据可追溯与PIT补充':'R113-R118组成、身份、月末及双时钟全量核验；首次披露值未恢复，PE与财务可能共享来源。部分覆盖可继续探索，不认证严格PIT。',
      '失败尝试及持续研究记录':'R113-R118未据匹配率选择时钟或删差异样本；恒等式不升级成经济证据。下一项固定前月成员、双时钟财务变化覆盖审计，不再调匹配阈值。'}
    for item in req['items']:
        item['completion_proven']=False
        if item['requirement'] in updates:
            item['unresolved_at_R112']=item['unresolved'];item['unresolved']=updates[item['requirement']]
            known={e['path'] for e in item['evidence']}
            item['evidence'] += [dict(path=p,exists=True,sha256=sha(ROOT/p)) for p in REFS if p not in known]
    req['interpretation']='R119:27 definitions including2 diagnostics;16 overall requirements unproven';req['overall_status']='active_not_complete';js(out/'requirements_evidence.json',req)
    js(out/'branch_evidence.json',dict(status='diagnostics_verified_no_predictive_claim',results=results,refs={p:sha(ROOT/p) for p in REFS},strict_pit=False,clock_selected=False,matching_filter_for_prediction=False,next='fixed-prior-member dual-clock consecutive financial TTM change coverage, including negative profits; no PE-agreement eligibility filter'))
    cur=json.loads((ROOT/'outputs/current_sources.json').read_text())
    for k,p in ROUTES.items():cur['selected'][k]=dict(path=p,sha256=sha(ROOT/p))
    cur['pending']='R113-R118 diagnostics integrated; next actual TTM change industry coverage under both clocks, no clock selection. Full factors, independent increment, costs and forward evidence remain incomplete.'
    js(ROOT/'outputs/current_sources.json',cur)
    js(out/'receipt.json',dict(code_sha256=sha(__file__),protocol_sha256=sha(ROOT/'protocols/r119.json'),prior_dictionary_sha256=sha(ROOT/'outputs/r112/current_factor_dictionary.json'),prior_requirements_sha256=sha(ROOT/'outputs/r112/requirements_evidence.json'),routes=ROUTES,outputs={n:sha(out/n) for n in ['current_factor_dictionary.json','requirements_evidence.json','branch_evidence.json']},entries=27,requirements=16,completed=0))
    print('REGISTERED 27 definitions; 16 overall requirements unproven')
if __name__=='__main__':run()
