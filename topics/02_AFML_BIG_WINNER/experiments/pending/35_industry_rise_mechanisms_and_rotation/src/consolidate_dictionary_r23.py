"""Current dictionary with explicit supersession; frozen historical dictionaries unchanged."""
import csv
from common import *


def run():
 out=ROOT/'outputs/r23';out.mkdir(exist_ok=True)
 inputs=[ROOT/'outputs/factor_dictionary.csv',ROOT/'outputs/r12/factor_dictionary.csv',ROOT/'outputs/r13/factor_dictionary.csv']
 rows=[]
 for p in inputs:
  for row in csv.DictReader(p.open()):
   row['dictionary_origin']=str(p.relative_to(ROOT));rows.append(row)
 old_macro=next(r for r in rows if r['factor']=='macro_state_x_sensitivity');rows.remove(old_macro)
 for r in rows:
  mod=r['module'];factor=r['factor'];r['strict_pit_certified']=False
  r['implemented']='historical_proxy';r['conclusion']='未确立稳定独立增量';r['mechanism_status']='经济假说；非因果证明'
  r['monitor_scope']='未接入统一监控';r['evidence_refs']=[]
  if mod=='F':
   r.update(publication_date='对应交易日收盘；合成篮子及历史成分仍为代理',source='EP32 forecast_v5 daily_industries；EP35 R05一级合成篮子',aggregation='R01：mom20/mom60秩均值形成动量组；F=(动量组-vol20秩+dd60秩)/3；R02/R16模型使用独立特征',monitor_scope='R18/R21价格观察；R22正式三任务模型',evidence_refs=['src/build_panel.py','protocols/r01.json','protocols/r02.json','reports/R16_一级三任务模型.md'])
   # Report filename is resolved below from the existing R16 prefix.
   r['evidence_refs'][-1]=str(next((ROOT/'reports').glob('R16_*.md')).relative_to(ROOT))
  if mod=='H':
   r['publication_date']='交易日收盘；历史篮子/个股版本修订未认证'
   r['evidence_refs']=['protocols/r01.json','reports/R21_分维度监控与失效检查.md']
   r['monitor_scope']='R21扩散或交易代理；不认定双拥挤'
   if factor.startswith('breadth'):
    r['aggregation']='有效前月成分的正收益比例；R01 D为21/63日广度秩均值，R02/R16分别输入'
   else:r['aggregation']='个股历史换手分位取行业中位数，完整门槛沿用继承源；R01负向秩为交易拥挤代理'
  if mod=='G':
   r['aggregation']='个股正TTM PE历史分位取行业中位数；R01负向中心秩；不使用Forward PE'
   r['monitor_scope']='R21显示分位与原覆盖，一级缺失';r['evidence_refs']=['protocols/r01.json','src/build_panel.py','reports/R21_分维度监控与失效检查.md']
  if mod=='C':
   r['source']='R03恢复all-market fina_indicator_vip原始30页归档；R07延迟/冲突审计'
   r['applicable_industries']='四季度财务资料及前月成员身份齐备，至少5公司且有效覆盖80%；财务行业可比性另审'
   r['conclusion']='仅5个成熟20日月份；延迟共同样本3个月，证据不足，不能认为已证实无效或有效'
   r['evidence_refs']=['protocols/r03.json','protocols/r07.json','outputs/r07/receipt.json']
  if mod=='A':
   r['formula']='state=[(制造业PMI-50)/100, (M2同比_t-M2同比_t-3)/100]；前36月/至少24期Ridge(alpha=1)估计滞后状态对past_excess20的敏感度；conditioned=beta·z(state)'
   r['aggregation']='各行业独立历史标准化；主方案F_macro=(F价格分数+conditioned横截面秩)/2；两时钟配对且同日>=20行业'
   r['evidence_refs']=['protocols/r13.json','src/macro_r13.py','outputs/r13/verification.json','outputs/r13/increments.csv']
   r['conclusion']='主20日增量未通过；共享宏观与行业敏感度交互不构成因果证明'
  if mod=='B':
   r.update(implemented='not_implemented_continuous_series',source='R19五份原文已复核，但未取得连续价差/订单/库存/产能序列',replication_status='序列因子未实现；公司事实另列，不静默替代',aggregation='待按产业链位置及连续变量协议登记；禁止混合上下游方向',conclusion='数据不足，未运行产业领先变量增量检验',evidence_refs=['reports/R19_五份经营原文复核.md','reports/R20_经营事实的身份时点与覆盖.md'])
  if mod=='D' and factor=='fixed_fy_eps_revision':
   r.update(economic_date='explicit fiscal_year',publication_date='max(list date, body date)；来源时间已恢复',available_at='严格早于信号日的公告代理，另保留实际归档时间；份额及修订链未认证',implemented='eps_revision_not_tested',source='R11已恢复明确年度EPS和利润预测；R12/R14/R15实际实验使用固定FY利润，不是EPS',replication_status='EPS来源已定位，EPS修正因子未验证；不得称整个D模块未发现来源',aggregation='EPS份额单位/股份变化及机构样本规则尚需单独协议；不能直接继承利润增量结论',conclusion='EPS专门分支未验证；利润分支另列',evidence_refs=['outputs/r11/receipt.json','reports/R15_完整报告屏障与月末敏感性.md'])
  if mod=='D' and factor=='same_broker_fixed_FY_profit_revision':
   r['missing_rule']='R15完整缓存报告屏障：同机构当前或紧邻前报缺失/冲突则未知，不跨越；最新<=180日、前报间隔<=365日；零分母缺失；行业>=5且>=80%'
   r['source']='R11 EP24原始HTML及回执；R15完整报告屏障修订，R11/R12旧版保留'
   r['evidence_refs']=['protocols/r15.json','src/barrier_sensitivity_r15.py','outputs/r15/data_verification.json','outputs/r15/verification.json']
   r['monitor_scope']='R21下一FY最新不晚于截面的覆盖快照；旧快照单列年龄，不填当期'
   r['conclusion']='屏障修正后覆盖收缩；未确立领先或独立增量，选定报告缓存不等于全市场一致预期'
   r['conclusion']+='；R25隔离3个利润字段后重放：12行业月记录、94预测值改变，未翻转增量结论；R26事件减少1个机构/2个行业，另保留未知对照敏感性；全量来源质量未认证'
   r['evidence_refs']+=['outputs/r24/source_review.json','outputs/r25/impact_receipt.json','outputs/r25/verification.json','outputs/r26/impact_receipt.json','outputs/r26/unknown_control_receipt.json']
  if mod=='E':
   r.update(implemented='not_integrated',aggregation='未登记聚合；不以交易换手替代基金持仓或ETF申赎',conclusion='数据与映射未接入，未检验',evidence_refs=['reports/研究假说与数据缺口.md'],monitor_scope='R21持仓拥挤显式未知')
  if r['horizon'].startswith('主20/次60交易日；未实现'):r['horizon']='已运行代理主20/次60交易日；未实现候选不继承验收'
 template={k:'不适用：公司单期证据，不是连续数值因子' for k in rows[0] if k not in ['evidence_refs','strict_pit_certified']}
 template.update(module='B',factor='reviewed_company_operating_evidence',theory='产业与经营机制证据及反证',formula='13条原文事实按公司/经济期/分部保留，不加总为行业分数',direction='扩张、恶化、水平值及管理层解释可以并存',applicable_industries='五选定公司按历史成员连接；不是业务分部或行业整体映射',economic_date='2026-06-30半年期',publication_date='继承2026-08各报告日期，首次发布/修订链未认证',available_at='公告代理、旧归档2026-10-10、EP35实际取得2026-11-13三时钟分别记录',frequency='单期，不声称连续',source='R19五份PDF，原哈希一致；13条观测复核',historical_revisions='PDF当前字节与旧回执一致不证明完整初发链；汇川分部同比重述已注记',aggregation='不加总；公司事实、行业身份、样本覆盖分别保存',missing_rule='无事实不是零增长；未映射/过时/目录外保留状态',failure_condition='公司选样、业务混合、会计重述、投资收益或现金解释不能外推行业机制',replication_status='公司原文已复核；不是产业领先因子',horizon='不进行单期事实收益预测检验',dictionary_origin='R19/R20证据接口',strict_pit_certified=False,implemented='reviewed_case_evidence',conclusion='原文事实有支持，领先性与独立性未检验',mechanism_status='分维度解释证据，非因果',monitor_scope='R20/R21公司事实连接',evidence_refs=['outputs/r19/review_receipt.json','outputs/r20/verification.json','protocols/r20.json'])
 rows.append(template)
 for factor,formula,theory in [('past_excess20/past_excess60','行业NAV_h期收益-CSI_ALL同h期收益','相对强弱与任务人群控制'),('log_members','log(已识别成员数)','篮子规模控制；不是市值风格因子')]:
  r=next(x for x in rows if x['factor']=='mom20/mom60').copy();r.update(factor=factor,formula=formula,theory=theory,direction='模型估计方向，不预设正向',aggregation='R02/R16按同日同层完整特征母体中心秩，再用训练期标准化与年度模型',dictionary_origin='src/build_panel.py + src/train_r02.py',evidence_refs=['src/build_panel.py','src/train_r02.py','src/train_l1_r16.py','protocols/r02.json'],monitor_scope='R22冻结模型输入，非额外价格排名因子');rows.append(r)
 seen=set()
 for r in rows:
  key=(r['module'],r['factor']);assert key not in seen;seen.add(key)
  assert r['source']!='同上' and not r['applicable_industries'].startswith('同上')
  r['evidence_sha256']={ref:sha(ROOT/ref) for ref in r['evidence_refs']}
 assert set(r['module'] for r in rows)==set('ABCDEFGH')
 js(out/'current_factor_dictionary.json',rows)
 fields=[k for k in rows[0] if k not in ['evidence_refs','evidence_sha256']]+['evidence_refs','evidence_sha256']
 with (out/'current_factor_dictionary.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()})
 js(out/'supersession.json',dict(removed_placeholder=old_macro,replacement='PMI_M2_prior_sensitivity_interaction',preserved_originals={str(p.relative_to(ROOT)):sha(p) for p in inputs},corrections=['A已有PMI/M2交互实验，但信用冲量/利率/汇率等未完整实现','D明确区分EPS来源与实际利润修正实验，完整报告屏障由R15接管','B原文已下载复核，连续产业序列仍未实现','F价格及模型控制公式/聚合分开，移除通用PE时点措辞','C/E/H/G的缺失和代理边界不因目录统一而晋级']))
 js(out/'receipt.json',dict(rows=len(rows),modules=sorted(set(r['module'] for r in rows)),code_sha256=sha(__file__),inputs={str(p):sha(p) for p in inputs},outputs={f:sha(out/f) for f in ['current_factor_dictionary.json','current_factor_dictionary.csv','supersession.json']},limitation='research dictionary completeness across eight headings, not implementation of all candidate factors or original 69 definitions'))
 print('Consolidated',len(rows),'entries across eight modules')

if __name__=='__main__':run()
