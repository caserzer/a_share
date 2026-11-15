"""Preserve research evidence and record bounded fund/ETF source discovery."""
import copy,re,subprocess
from common import *
REFS=[f'outputs/r{x}/verification.json' for x in range(120,124)]
ROUTES={'current_factor_dictionary':'outputs/r124/current_factor_dictionary.json','current_requirements_evidence':'outputs/r124/requirements_evidence.json','latest_stage_requirements_audit':'outputs/r124/requirements_evidence.json','financial_change_branch':'outputs/r124/branch_evidence.json','fund_etf_source_search':'outputs/r124/source_audit.json'}
def run():
    out=ROOT/'outputs/r124';out.mkdir(exist_ok=True)
    result={p:json.loads((ROOT/p).read_text()) for p in REFS};assert all(x['status']=='PASS' for x in result.values())
    rows=copy.deepcopy(json.loads((ROOT/'outputs/r119/current_factor_dictionary.json').read_text()))
    rows.append(dict(factor='consecutive_reported_ttm_bounded_change',module='C',theory='披露盈利改善可能支持持续性；需排除已有价格、规模、市场和广度解释',formula='固定前月成员；股票2*(TTM_t-TTM_t-1)/(|TTM_t|+|TTM_t-1|)，零零为0；已知子集等权平均',direction='正值候选盈利改善，亏损缩窄保留；不是利润增长百分比或收益承诺',applicable_industries='全目录保留；仅SW2021三级main80收益部分年度有训练资格',economic_date='连续完整月末选取报告所属期，先选最新可见报告再验组成',publication_date='最终财务缓存NOTICE/UPDATE，首发值版本未恢复',available_at='公告/修订两代理分别下一交易日，组成全部可用；不择优时钟',frequency='月末',source='R115-R117本地财务TTM及历史身份，R108前月成员，R120完整分母',historical_revisions='Historical-proxy；同报告期稳定值不是新披露事件；非严格PIT',aggregation='至少5成员且>=80%完整分母可给子集均值；100%完整单列；双时钟共同母体另验',missing_rule='缺前月/最新组成/身份保留未知；不按PE或利润正负筛选；仅两端已知稳定值填0',failure_condition='覆盖少数行业、公告滞后、共因子、月度重复值、时钟母体或组成变化；无稳定同母体增量',implemented='historical_feature_and_matched_ridge_verified',conclusion='R121三任务仅7收益折合格；R122/R123无稳定支持，IC样本不足；停止固定分支参数搜索，未采用',mechanism_status='未证明领先、独立稳定预测、因果或成本后配置价值',replication_status='EP35扩展，非方正原报告完整复现',dictionary_origin='R120-R123',monitor_scope='研究与失败证据，不是生产信号',strict_pit_certified=False,evidence_refs=REFS,evidence_sha256={p:sha(ROOT/p) for p in REFS}))
    js(out/'current_factor_dictionary.json',rows)
    req=copy.deepcopy(json.loads((ROOT/'outputs/r119/requirements_evidence.json').read_text()))
    updates={'为什么上涨：经济机制与反证':'R120-R123完成财务变化及同母体比较；无稳定增量，不能认证盈利驱动。','三类任务冻结协议和时序验证':'R121840候选折仅7收益折合格；二元/严格覆盖不足。R12214模型及R123共同母体9模型已核验；无稳定支持。','经济假说与完整因子字典交付':'原27条保留，新增财务变化候选及失败证据共28条；不是28有效因子，完整复现仍缺。','数据可追溯与PIT补充':'R120-R123覆盖、成熟边界、身份与共同母体可复核；最终缓存和有限行业不能升级PIT。资金配置连续来源与历史映射尚未定位。','失败尝试及持续研究记录':'固定财务变化分支停止参数搜索；全量负结果及样本不足保留。资金来源搜索限定目录，缺口不等于整体受阻。'}
    for item in req['items']:
        item['completion_proven']=False
        if item['requirement'] in updates:
            item['unresolved_at_R119']=item['unresolved'];item['unresolved']=updates[item['requirement']]
            known={e['path'] for e in item['evidence']};item['evidence'] += [dict(path=p,exists=True,sha256=sha(ROOT/p)) for p in REFS if p not in known]
    req['interpretation']='R124:28definitions,16overall requirements unproven';req['overall_status']='active_not_complete';js(out/'requirements_evidence.json',req)
    js(out/'branch_evidence.json',dict(status='stopped_parameter_search_not_adopted',results=result,refs={p:sha(ROOT/p) for p in REFS},strict_pit=False,clock_selected=False))
    roots=[str(CACHE),'/home/xiaolv/code/golden_loop','/home/xiaolv/code/golden_loop_artifacts']
    cmd=['rg','--files','--hidden','--no-ignore']+roots+['-g','!**/.git/**','-g','!**/.venv/**','-g','!**/node_modules/**','-g','!**/__pycache__/**']
    completed=subprocess.run(cmd,capture_output=True,text=True,check=True)
    candidates=sorted(p for p in completed.stdout.splitlines() if re.search(r'(^|[_/.-])(etf|fund|holding)([_/.-]|$)',p.lower()))
    code=Path('/home/xiaolv/code/golden_loop/a_share_market_radar/production/long_opportunity_report_v2.py')
    js(out/'source_audit.json',dict(status='bounded_inventory_not_ready_for_prediction',roots=roots,command=cmd,listed_files=len(completed.stdout.splitlines()),candidates=[dict(path=p,sha256=sha(p),bytes=Path(p).stat().st_size) for p in candidates],producer=dict(path=str(code),sha256=sha(code)),structured_filename_candidates=[p for p in candidates if Path(p).suffix in ['.csv','.parquet','.json','.sqlite','.db']],limits=['filename search cannot establish global absence of financial datasets','research reports and query implementation are not a continuous historical panel','initial publication times, ETF existence, split adjustments and historical industry mapping remain unverified'],next='Inspect producer storage references and actual retained artifacts before any flow factor; no external retrieval authorized by this audit'))
    cur=json.loads((ROOT/'outputs/current_sources.json').read_text())
    for k,p in ROUTES.items():cur['selected'][k]=dict(path=p,sha256=sha(ROOT/p))
    cur['pending']='Financial change fixed branch stopped without stable increment; fund/ETF bounded inventory lacks a verified continuous panel. Next inspect actual source storage references and remaining grounded mechanisms; full scope remains incomplete.'
    js(ROOT/'outputs/current_sources.json',cur)
    names=['current_factor_dictionary.json','requirements_evidence.json','branch_evidence.json','source_audit.json']
    js(out/'receipt.json',dict(code_sha256=sha(__file__),protocol_sha256=sha(ROOT/'protocols/r124.json'),prior_dictionary_sha256=sha(ROOT/'outputs/r119/current_factor_dictionary.json'),prior_requirements_sha256=sha(ROOT/'outputs/r119/requirements_evidence.json'),routes=ROUTES,outputs={n:sha(out/n) for n in names},entries=28,requirements=16,completed=0))
    print('Registered28; bounded candidate files',len(candidates))
if __name__=='__main__':run()
