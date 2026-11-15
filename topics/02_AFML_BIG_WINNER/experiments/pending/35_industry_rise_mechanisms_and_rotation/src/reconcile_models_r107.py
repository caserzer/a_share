"""Register executable update and numerical evidence without success promotion."""
import copy
import pandas as pd
from common import *
REFS=['outputs/r101/verification.json','outputs/r102/verification.json','outputs/r103/verification.json','outputs/r104/verification.json','outputs/r105/model_verification.json','outputs/r105/metric_verification.json','outputs/r106/model_verification.json','outputs/r106/metric_verification.json','outputs/r106/drift_verification.json']
AMENDED=['mom20/mom60','vol20','dd60','breadth21/breadth63','past_excess20/past_excess60','log_members']
ROUTES={'current_factor_dictionary':'outputs/r107/current_factor_dictionary.json','current_requirements_evidence':'outputs/r107/requirements_evidence.json','latest_stage_requirements_audit':'outputs/r107/requirements_evidence.json','versioned_historical_inference':'outputs/r102/bundles.json','three_task_model_explanations':'outputs/r103/receipt.json','rank_redundancy_audit':'outputs/r104/verification.json','fixed_penalty_precision_comparison':'outputs/r106/drift_summary.json','next_local_mechanism_source_audit':'outputs/r107/next_path_source_audit.json'}
UPDATES={
 '行业监控与更新流程':'R101三任务不可变推断、R102截止日纯特征重算及R103模型分项均已验证；历史511行业网格保留缺失。仍非新行情采集、上游股票篮子增量更新、调度部署或真实前瞻。',
 '三类任务冻结协议和时序验证':'R104两组秩重复在全部历史F/FD母体确认；R105/R106唯一方向惩罚及数值精度比较完成，近期调整区间均跨零，原模型未替换。稳定增量、可靠前瞻校准仍缺。',
 '基准因子增量优先实验':'R104重复秩没有新增信息；R105等惩罚变化未建立稳定改善，R106三组微小差异变号，不能将数值变化解释为信息增量。其它非价格机制与独立前瞻仍缺。',
 '经济假说与完整因子字典交付':'24条定义保留，6条价格/广度项追加模型应用和冗余/精度边界。原69项完整复现、其它机制和首次修订记录仍缺。',
 '多模型完整结果与消融成本交付':'R101—R106补齐冻结推断、分项、等价表示、固定惩罚及精度配对；没有采用新模型，未建立成本后可交易价值或独立期稳定增量。',
 '数据可追溯与PIT补充':'R101/R102封存模型和纯特征及日频前缀，R103—R106可重建。截止当前缓存不恢复首次发布版本；成分、市值、复权与成交可得性仍为历史代理边界。',
 '失败尝试及持续研究记录':'近期实现修正、排名冗余与数值敏感结果保留；惩罚/精度分支停止搜索。下一项先审计事前龙头与跟随者的本地来源可用性，不依赖新采集。'
}

def source_audit(out):
    stock=CACHE/'extension_v2/products/panel.parquet';assign=CACHE/'extension_v2/products/assignments.parquet';l1=ROOT/'data/l1_assignments.parquet'
    cols=['month','date','security_id','qfq_close','close_chain','raw_close','total_shares','share_effective_date','cap','listed']
    s=pd.read_parquet(stock,columns=cols)
    assert not s.duplicated(['month','security_id']).any()
    cap=s.listed&np.isfinite(s.cap)&s.cap.gt(0)&s.raw_close.gt(0)&s.total_shares.gt(0)&s.share_effective_date.notna()&s.share_effective_date.le(s.date)
    price=np.isfinite(s.qfq_close)&s.qfq_close.gt(0)&s.close_chain.notna()
    members=pd.concat([pd.read_parquet(p,columns=['month']+KEY+['security_id','unresolved']) for p in [assign,l1]],ignore_index=True)
    assert not members.duplicated(['month']+KEY+['security_id']).any()
    z=members.merge(s[['month','security_id']].assign(cap_valid=cap,price_valid=price),on=['month','security_id'],how='left',validate='many_to_one')
    groups=z.groupby(['month']+KEY).agg(members=('security_id','size'),cap_known=('cap_valid','sum'),price_known=('price_valid','sum'),unresolved=('unresolved','max')).reset_index()
    groups['ranking_candidate']=groups.members.ge(5)&groups.cap_known.eq(groups.members)&groups.unresolved.eq(0)
    groups.to_parquet(out/'leader_source_coverage.parquet',index=False)
    counts=groups.groupby(['era','level']).agg(industry_months=('month','size'),ranking_candidates=('ranking_candidate','sum')).reset_index().to_dict('records')
    sources=[stock,assign,l1,ROOT/'src/size_control_r30.py',EP32/'extensions/v2_full_history_benchmark/src/core.py']
    result=dict(status='local_source_path_exists_not_factor_validated',stock_rows=len(s),stock_months=s.month.nunique(),first_date=str(s.date.min().date()),last_date=str(s.date.max().date()),valid_cap_rows=int(cap.sum()),valid_price_rows=int(price.sum()),source_columns=cols,source_hashes={str(p):sha(p) for p in sources},coverage=counts,limitations=['month-end capitalization is a proxy for economic leadership','share effective date is not initial known_at','all prices are current historical caches, not certified vintage data','ranking candidate count does not establish lagged common-chain return coverage','future next_return and entry price columns not read'],next_action='Register prior-month top3 cap versus remaining-member prior-price lead proxy; audit exact consecutive months and chain consistency before outcome comparison; preserve unknown rank members and full industry catalogue')
    js(out/'next_path_source_audit.json',result)

def run():
    out=ROOT/'outputs/r107';out.mkdir(exist_ok=True)
    for p in REFS:assert json.loads((ROOT/p).read_text())['status']=='PASS'
    prior=ROOT/'outputs/r92/current_factor_dictionary.json';rows=copy.deepcopy(json.loads(prior.read_text()))
    for x in rows:
        if x['factor'] not in AMENDED:continue
        x['model_application_evidence']='R101/R102冻结模型、精确日期输入和截止日前缀可重放；R103分项是回归值或校准logit，不是因果/概率百分点'
        x['model_application_limit']='R104两组动量/过去超额秩重复；R105/R106惩罚与精度比较未建立SW2021稳定改善；默认容差可能影响微小分类结论，未替换模型'
        x['numerical_research_rule']='后续模型比较显式登记精度并核查惩罚梯度；不将相同截面秩算作独立信息；禁止靠重复列暗增权重'
        x['evidence_refs']=list(dict.fromkeys(x['evidence_refs']+REFS));x['evidence_sha256'].update({p:sha(ROOT/p) for p in REFS})
    js(out/'current_factor_dictionary.json',rows)
    oldreq=ROOT/'outputs/r100/requirements_evidence.json';a=copy.deepcopy(json.loads(oldreq.read_text()))
    for item in a['items']:
        item['completion_proven']=False
        if item['requirement'] in UPDATES:
            item['unresolved_at_R100']=item['unresolved'];item['unresolved']=UPDATES[item['requirement']]
            known={e['path'] for e in item['evidence']}
            item['evidence'] += [dict(path=p,exists=True,sha256=sha(ROOT/p)) for p in REFS if p not in known]
    a['interpretation']='R107: local inference and numerical diagnostics completed;16 full requirements remain unproven';a['overall_status']='active_not_complete';js(out/'requirements_evidence.json',a)
    source_audit(out)
    current=json.loads((ROOT/'outputs/current_sources.json').read_text())
    for k,p in ROUTES.items():current['selected'][k]=dict(path=p,sha256=sha(ROOT/p))
    current['pending']='Historical update and model explanations runnable; rank-duplication/penalty/precision branch stopped without adoption. Next inspect local prior-leader/follower diffusion data; strict PIT, full reference factors, other mechanisms, execution and forward validation remain unproven.';js(ROOT/'outputs/current_sources.json',current)
    js(out/'receipt.json',dict(prior_dictionary_sha256=sha(prior),prior_requirements_sha256=sha(oldreq),dictionary_sha256=sha(out/'current_factor_dictionary.json'),requirements_sha256=sha(out/'requirements_evidence.json'),code_sha256=sha(Path(__file__)),amended=AMENDED,routes=ROUTES,entries=24,requirements=16,completed=0));print('R107 registered; source path audited, no predictive promotion')

if __name__=='__main__':run()
