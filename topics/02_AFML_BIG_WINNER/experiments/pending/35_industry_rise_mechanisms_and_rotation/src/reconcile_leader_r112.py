"""Register stopped leader branch and audit a local valuation attribution source."""
import copy
import pandas as pd
from common import *
REFS=['outputs/r108/verification.json','outputs/r109/model_verification.json','outputs/r109/metric_verification.json','outputs/r110/verification.json','outputs/r111/verification.json']
ROUTES={'current_factor_dictionary':'outputs/r112/current_factor_dictionary.json','current_requirements_evidence':'outputs/r112/requirements_evidence.json','latest_stage_requirements_audit':'outputs/r112/requirements_evidence.json','leader_diffusion_branch':'outputs/r112/branch_evidence.json','next_local_mechanism_source_audit':'outputs/r112/valuation_source_audit.json'}

def run():
    out=ROOT/'outputs/r112';out.mkdir(exist_ok=True)
    for ref in REFS:assert json.loads((ROOT/ref).read_text())['status']=='PASS'
    rows=copy.deepcopy(json.loads((ROOT/'outputs/r107/current_factor_dictionary.json').read_text()))
    rows.append(dict(factor='prior_ranked_leader_follower_return_spread',module='H',theory='信息缓慢扩散：事前规模龙头领先可能先于其余成员追赶；规模并非信息领导力',formula='上月固定成员按有效总市值降序/证券ID升序取前三；本月同复权链端点等权收益，龙头均值减其余成员均值',direction='正差为候选先行，不自动代表行业启动、追赶或反转',applicable_industries='SW2014二/三级、SW2021一/二/三级分别研究；全目录缺失保留',economic_date='精确相邻月末；排名使用上月成员和市值',publication_date='价格/股本历史缓存，首次发布和修订链未认证',available_at='信号月末历史代理；非真实归档当时可得证明',frequency='月末',source='EP32 extension_v2 monthly panel/assignments与EP35一级成员；R108逐成员核验',historical_revisions='当前历史缓存；旧版本不覆盖，不声称严格PIT',aggregation='至少5成员、无未解决身份、全成员有效前月市值；3龙头全有效，跟随者至少2且>=80%；另列100%敏感性',missing_rule='未知市值不删除后排名；价格/上市/复权链缺失保留未知，不填零；未来追赶要求全部原成员端点完整',failure_condition='共同市场/风格、规模而非领导力、未来缺价选择偏差；跨年/分类不稳定或同母体无增量',implemented='historical_feature_and_matched_experiments_complete',conclusion='R109三任务与R111直接追赶控制比较均未达到稳定支持；R110描述混合，停止固定价差分支参数搜索',mechanism_status='未证明独立预测、因果扩散或配置价值',replication_status='EP35扩展，不是方正完整复现',dictionary_origin='R108-R111',monitor_scope='研究候选与负结果；未替换冻结模型、无生产部署',strict_pit_certified=False,evidence_refs=REFS,evidence_sha256={p:sha(ROOT/p) for p in REFS}))
    js(out/'current_factor_dictionary.json',rows)
    req=copy.deepcopy(json.loads((ROOT/'outputs/r107/requirements_evidence.json').read_text()))
    updates={'为什么上涨：经济机制与反证':'R108事前规模价差、R110直接延迟追赶及R111控制比较完成；混合关联不证明因果，固定价差分支停止参数搜索。价格/估值/隐含盈利解释仍需核验，非实际现金流归因。','上涨持续性':'R110固定原名单追赶与R111同样本控制已完成，未建立稳定独立增量；等待期不调优，成本和独立前瞻仍缺。','三类任务冻结协议和时序验证':'R109新增龙头变量三任务同母体比较完成，140参数组、77538配对，无稳定支持；原冻结模型不替换，原有校准和前瞻限制仍保留。','经济假说与完整因子字典交付':'保留原24条，追加事前龙头价差及失败证据，共25条定义，不代表25个有效因子；完整69项/其它机制/首发修订仍缺。','数据可追溯与PIT补充':'R108-R111成员端点、完整未来覆盖、成熟标签和同母体比较可复核；历史代理不能恢复首次发布，PE与股本价格口径还需单独审计。','多模型完整结果与消融成本交付':'R109行业三任务与R111追赶控制比较已完成，均未采用；无稳定增量、可执行成本后价值或独立前瞻证明。','失败尝试及持续研究记录':'R108-R111完整来源、覆盖、负结果与独立核验已登记；固定价差分支停止。下一项审计本地原始PE/价格精确端点及盈利隐含量口径，不采集新数据。'}
    for item in req['items']:
        item['completion_proven']=False
        if item['requirement'] in updates:
            item['unresolved_at_R107']=item['unresolved'];item['unresolved']=updates[item['requirement']]
            known={x['path'] for x in item['evidence']};item['evidence'] += [dict(path=p,exists=True,sha256=sha(ROOT/p)) for p in REFS if p not in known]
    req['interpretation']='R112:25 evidence definitions,16 full requirements remain unproven';req['overall_status']='active_not_complete';js(out/'requirements_evidence.json',req)
    js(out/'branch_evidence.json',dict(status='stopped_parameter_search_not_adopted',refs={p:sha(ROOT/p) for p in REFS},r109=json.loads((ROOT/REFS[2]).read_text()),r110=json.loads((ROOT/REFS[3]).read_text()),r111=json.loads((ROOT/REFS[4]).read_text()),next='Different grounded source/attribution question; no new leader window search'))
    stock=CACHE/'extension_v2/products/panel.parquet';pepath=CACHE/'joint_pe_v35/stock_pe_panel.parquet'
    s=pd.read_parquet(stock,columns=['month','date','security_id','raw_close','cap','total_shares','share_effective_date','listed'])
    pe=pd.read_parquet(pepath);assert pe.index.is_unique and pe.columns.is_unique and not s.duplicated(['month','security_id']).any()
    ri=pe.index.get_indexer(s.date);ci=pe.columns.get_indexer(s.security_id);matched=(ri>=0)&(ci>=0);values=np.full(len(s),np.nan);values[matched]=pe.to_numpy()[ri[matched],ci[matched]]
    s['pe_exact_identity_date']=matched;s['vendor_pe_ttm']=values;s['positive_pair_ready']=s.listed.eq(True)&np.isfinite(s.raw_close)&s.raw_close.gt(0)&np.isfinite(values)&(values>0)
    s=s.sort_values(['security_id','month']).reset_index(drop=True);old=s.groupby('security_id').shift(1);consecutive=s.month.eq(old.month+1)
    s['consecutive_positive_pair']=s.positive_pair_ready&old.positive_pair_ready.eq(True)&consecutive
    s.to_parquet(out/'valuation_monthly_coverage.parquet',index=False)
    sources=[stock,pepath,EP32/'extensions/v35_pe_activity_joint/src/build35.py',EP32/'extensions/v35_pe_activity_joint/outputs/feature_receipt.json']
    source_receipt=json.loads(sources[-1].read_text());assert sha(pepath)==source_receipt['stock_panel_sha256']
    js(out/'valuation_source_audit.json',dict(status='local_exact_endpoint_path_exists_not_earnings_verified',stock_rows=len(s),months=int(s.month.nunique()),pe_dates=len(pe),pe_securities=len(pe.columns),exact_identity_date=int(matched.sum()),finite_pe=int(np.isfinite(values).sum()),nonpositive_pe=int((np.isfinite(values)&(values<=0)).sum()),positive_endpoint=int(s.positive_pair_ready.sum()),consecutive_positive_pairs=int(s.consecutive_positive_pair.sum()),sources={str(p):sha(p) for p in sources},coverage_sha256=sha(out/'valuation_monthly_coverage.parquet'),limits=['vendor known_at absent per upstream code','PE positive selection must not delete loss-making members from full denominator','raw price / PE is implied per-share earnings, not independently observed actual earnings','corporate actions, changing shares, dilution and vendor basis can move implied earnings','No price outcome model or causal attribution run'],next='Register exact two-endpoint algebra with raw prices and vendor PE, separate share changes and coverage; reconcile corporate-action basis before economic interpretation'))
    current=json.loads((ROOT/'outputs/current_sources.json').read_text())
    for k,p in ROUTES.items():current['selected'][k]=dict(path=p,sha256=sha(ROOT/p))
    current['pending']='R108-R111 leader branch stopped without stable increment/adoption. Next exact PE/raw-price/implied-earnings source and basis diagnostic; full factors, PIT, execution and forward validation remain unproven.';js(ROOT/'outputs/current_sources.json',current)
    js(out/'receipt.json',dict(prior_dictionary_sha256=sha(ROOT/'outputs/r107/current_factor_dictionary.json'),prior_requirements_sha256=sha(ROOT/'outputs/r107/requirements_evidence.json'),code_sha256=sha(__file__),routes=ROUTES,outputs={p.name:sha(p) for p in out.iterdir() if p.name not in ['receipt.json','verification.json','integration_receipt.json'] and p.suffix in ['.json','.parquet']},entries=25,requirements=16,completed=0));print(json.loads((out/'valuation_source_audit.json').read_text()))
if __name__=='__main__':run()
