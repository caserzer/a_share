"""Add financing evidence while preserving the prior dictionary and open gaps."""
import copy
from common import *

def run():
 out=ROOT/'outputs/r49';out.mkdir(exist_ok=True);source=ROOT/'outputs/r43/current_factor_dictionary.json';rows=copy.deepcopy(json.loads(source.read_text()));row=copy.deepcopy(next(x for x in rows if x['module']=='E'))
 row.update(factor='industry_financing_balance_intensity',theory='融资余额相对规模代理杠杆需求，也可能只是规模/融资资格及追涨的结果',formula='前月行业成员的融资余额(T前2交易日)/总市值(T)中位数',direction='不预设正向配置价值，模型估计及反证',applicable_industries='行业分类/层级分别构建；严格覆盖子样本；实际收益拟合仅SW2021 L2/L3、分类仅L3主20日',economic_date='融资快照与信号日分母分别记录，2018-12至2026-04',publication_date='继承交易所次日披露的历史代理；本地回执下载日不是首次公开日',available_at='相隔两市场交易日余额与当日收盘市值；股本只有生效日，非严格PIT',frequency='月末采样',source='EP24既有交易所原始响应356份，R44只读核验；R45因子',historical_revisions='原始快照字节可追溯，首次披露和后续修订链未知',aggregation='公司比值等权中位数；模型同日同层共同样本中心秩，训练期标准化',missing_rule='>=5有效公司且占前月全部成员>=80%；缺记录/分母不补0，披露0保留',failure_condition='融资资格与规模偏向、价格分母、杠杆追涨、股本时点及历史修订；不等同ETF申赎或公募持仓',replication_status='EP35 E模块扩展代理，非方正完整复现',horizon='主20/次60收益；固定启动反转20/60，退出仅合格L3 20日',dictionary_origin='R44-R48',implemented='historical_proxy_tested_partial_coverage',conclusion='R46主收益增量未建立；R47分类Brier变差且仅16月；R48成本后退出不如持有、融资版比FS差；不再搜索本分支参数',mechanism_status='杠杆需求假说，未证明因果或独立前瞻能力',monitor_scope='本地研究与冻结结果，未接入生产或替换价格模型',strict_pit_certified=False,evidence_refs=['protocols/r45.json','outputs/r45/verification.json','protocols/r46.json','outputs/r46/increments.json','outputs/r46/verification.json','outputs/r47/verification.json','outputs/r47/selection_verification.json','outputs/r48/verification.json','reports/R48_融资反转提示退出代价.md'])
 row['evidence_sha256']={ref:sha(ROOT/ref) for ref in row['evidence_refs']};rows.append(row);js(out/'current_factor_dictionary.json',rows)
 audit=copy.deepcopy(json.loads((ROOT/'outputs/r43/requirements_evidence.json').read_text()))
 for item in audit['items']:
  if item['requirement'] in ['基准因子增量优先实验','何时启动：领先与及时性','何时结束：风险和错误退出','经济假说与完整因子字典交付']:
   item['financing_progress']='R44-R48数据/收益/分类/固定退出已实际检验，未建立增量或配置价值；覆盖选择偏大规模，未外推全行业'
   item['evidence'] += [dict(path=ref,exists=True,sha256=sha(ROOT/ref)) for ref in ['outputs/r46/verification.json','outputs/r47/verification.json','outputs/r48/verification.json']]
  item['completion_proven']=False
 js(out/'requirements_evidence.json',audit)
 current=json.loads((ROOT/'outputs/current_sources.json').read_text());current['selected']['current_factor_dictionary']=dict(path='outputs/r49/current_factor_dictionary.json',sha256=sha(out/'current_factor_dictionary.json'));current['selected']['financing_industry_factor']=dict(path='data/r45_financing_intensity.parquet',sha256=sha(ROOT/'data/r45_financing_intensity.parquet'));current['pending']='Battery and financing partial-data experiments completed without stable primary increment; ETF/fund allocations, other industry mechanisms, original release/revision histories, full styles, tradability, prospective validation and consolidated monitoring remain open';js(ROOT/'outputs/current_sources.json',current)
 js(out/'receipt.json',dict(previous_dictionary_sha256=sha(source),dictionary_sha256=sha(out/'current_factor_dictionary.json'),entries=19,code_sha256=sha(__file__),overall_status='active_not_complete'))
 print('R49 reconciled 19 factors')

if __name__=='__main__':run()
