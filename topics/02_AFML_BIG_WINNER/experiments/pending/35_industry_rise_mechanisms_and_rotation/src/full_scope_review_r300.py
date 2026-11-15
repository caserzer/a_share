from common import *
import pandas as pd
from copy import deepcopy

def run():
 out=ROOT/'outputs/r300';src=ROOT/'outputs/cnequity_fundamental_review_20261114';manifest=json.loads((src/'manifest.json').read_text());checks=0
 for name,h in manifest.items():assert sha(ROOT/name)==h;checks+=1
 cells=json.loads((src/'reviewed_financial_cells.json').read_text());receipts={x['symbol']:x for x in json.loads((src/'original_receipts.json').read_text())};anomalies=json.loads((ROOT/'outputs/r249/negative_years.json').read_text());overlap=set(receipts)&{x['ts_code'] for x in anomalies}
 assert len(cells)==70 and len(receipts)==10;facts=[]
 for c in cells:
  receipt=receipts[c['symbol']];facts.append(dict(symbol=c['symbol'],report_period=c['report_period'],item_code=c['item_code'],value=c['item_value'],statement_type=c['statement_type'],announce_date=c['announce_date'],observed_at=receipt['fetched_at'],unit='CNY',unit_multiplier=c['unit_multiplier'],sign_rule=c['sign_rule'],pdf_url=receipt['pdf_url'],pdf_sha256=receipt['pdf_sha256'],pdf_page=c['pdf_page'],review_status=c['status'],strict_pit=False,quality='Previously reviewed local source fact; not independently re-read PDF this round',period_semantics='2026-06-30 balance-sheet point' if c['statement_type']=='balance' else '2026H1 cumulative; not Q2 standalone',source_review_sha256=sha(src/'reviewed_financial_cells.json')))
 js(out/'local_fact_bridge.json',facts)
 branches=deepcopy(json.loads((ROOT/'outputs/r238/branch_decisions.json').read_text()));assert len(branches['branches'])==16
 extension={'core_three_tasks':'R253–258及R286–299已补齐日频启动/反转、校准、过程和行动；无独立未来，不继续参数搜索。','battery':'R273–285生产/出口/季节性与修订核对已执行；原统计差异仍未解释，未来样本不足。','financing':'R260–272分母与双时钟对照已执行，无稳定增量。','financial_dual_clock':'新增10股原文与公告日期证据可用于修订口径核查；不增加训练历史。','capital_accounting':'新增10股与154个资本支付异常公司无交集，不能解决原异常；同报告比较期仍可核查。','early_financial':'新增单期原文不等于新增季度序列；既有六期资格失败保留。','eps_expectations':'R141/R197固定FY及覆盖/股本上下文已处理；新财报不是分析师预测，不可替代。','profit_expectations':'新财报是已实现数据，不补齐八期预期历史。'}
 for b in branches['branches']:
  for ref in b['evidence']:assert sha(ROOT/ref['path'])==ref['sha256']
  b['current_review']=extension.get(b['family'],'保留原实验与失败及重开条件；本批10股单期财报没有直接补齐该分支样本，未据此重训。')
 js(out/'family_review.json',branches)
 audit=deepcopy(json.loads((ROOT/'outputs/r298/requirements_audit.json').read_text()));audit['revision']='R300';audit['next_local']=[dict(task='核对新增本地10份2026半年报中的2025同期利润/现金流/资本支付比较列，连接旧2025归档并区分原值与重述；仅本地原文，先识别列和期间，未知保留。',acceptance='每个字段独立页码/单位/期间/来源版本；不把2026披露比较值当成2025已知值，不追加训练资格')]
 for item in audit['items']:
  if item['id']=='R04':item['verified_scope']+=' R295—R299反转概率/不确定性/行动等价与只读展示已完成。'
  if item['id']=='R15':item['verified_scope']+=' R299显式日期月频/日频概率对照已完成；不输出未来目标。'
  if item['id'] in ['R01','R03','R10','R12','R13']:
   item['verified_scope']+=' R300新本地10股原文70项既核事实已作来源桥接；不冒充新增独立季度。'
   item['unresolved']+=' 可执行新证据核查：2026报告所列2025比较期与旧归档的版本差异，尚未逐项审阅。'
 assert len(audit['items'])==16 and not audit['full_completion_proven'];js(out/'requirements_audit.json',audit)
 summary=dict(status='PASS',new_manifest_hash_checks=checks,reviewed_facts=len(facts),issuers=len(receipts),report_periods=sorted({c['report_period'] for c in cells}),anomaly_cases=len(anomalies),anomaly_issuer_overlap=sorted(overlap),new_model_training_periods_certified=0,original_families=16,requirements=16,next=audit['next_local'],adoption=False,goal_complete=False);js(out/'summary.json',summary)
 inputs=['outputs/r238/branch_decisions.json','outputs/r298/requirements_audit.json','outputs/r249/negative_years.json','outputs/cnequity_fundamental_review_20261114/manifest.json','protocols/r300.json','src/full_scope_review_r300.py'];js(out/'receipt.json',dict(inputs={p:sha(ROOT/p) for p in inputs},outputs={p:sha(out/p) for p in ['local_fact_bridge.json','family_review.json','requirements_audit.json','summary.json']}));print(summary)
if __name__=='__main__':run()
