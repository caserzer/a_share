import sys,json,hashlib,re
from pathlib import Path
sys.path.insert(0,'topics/02_AFML_BIG_WINNER/experiments/pending/35_industry_rise_mechanisms_and_rotation/src')
from cnequity_fundamental_review import *
cands=json.loads((OUT/'pdf_candidates.json').read_text());receipts=json.loads((OUT/'original_receipts.json').read_text());local=json.loads((OUT/'local_crosscheck.json').read_text())
# Pages selected after reading table labels and units; never promote a bare number hit.
summary={'600236.SH':6,'605123.SH':6,'300411.SZ':7,'300693.SZ':9,'002832.SZ':7,'003021.SZ':7,'600955.SH':5,'002948.SZ':7,'920407.BJ':8,'002406.SZ':7}
balance={'600236.SH':48,'605123.SH':38,'300411.SZ':40,'300693.SZ':71,'002832.SZ':54,'003021.SZ':59,'600955.SH':30,'002948.SZ':8,'920407.BJ':39,'002406.SZ':36}
capex={'600236.SH':55,'605123.SH':45,'300411.SZ':46,'300693.SZ':78,'002832.SZ':61,'003021.SZ':67,'600955.SH':36,'002948.SZ':99,'920407.BJ':44,'002406.SZ':43}
review=[]
for x in cands:
 sym=x['symbol'];key=x['item_code'];p=capex[sym] if key=='capex' else balance[sym] if key in ['total_equity','total_liabilities'] else summary[sym]
 if sym=='605123.SH' and key=='total_assets':p=7
 if sym=='920407.BJ' and key=='total_liabilities':p=8
 h=next(h for h in x['hits'] if h['page']==p)
 review.append({k:v for k,v in x.items() if k not in ['hits','state']}|dict(pdf_page=p,unit_multiplier=h['unit_multiplier'],reported_number=h['number'],context=h['context'],status='matched_after_label_period_unit_review',sign_rule='PDF cash outflow (191125) thousand; compare positive expenditure magnitude' if sym=='002948.SZ' and key=='capex' else 'as reported',visual_scope='all ten principal financial summary pages plus bank unit/sign and selected holder pages; other pages checked by extracted table context'))
assert len(review)==70;dump(OUT/'reviewed_financial_cells.json',review)
# Holder totals: review exact count and the label, not arbitrary numeric occurrence.
counts=json.loads((DATA/'RPT_F10_EH_HOLDERNUM.json').read_text());holder_review=[]
for x in counts:
 sym=x['SECUCODE'];v=int(x['HOLDER_TOTAL_NUM']);hits=[]
 for pg in json.loads((DATA/sym/'pages.json').read_text()):
  text=pg['text']
  for val in [f'{v:,}',str(v)]:
   at=text.find(val)
   if at>=0 and ('股东' in text[max(0,at-100):at]):hits.append(dict(page=pg['page'],context=text[max(0,at-110):at+130]))
 assert hits,sym
 holder_review.append(dict(symbol=sym,holders=v,pdf_page=hits[0]['page'],context=hits[0]['context'],status='matched_report_total',scope='all ordinary shareholders; not necessarily A-only'))
dump(OUT/'reviewed_holder_counts.json',holder_review)
top=json.loads((OUT/'top_holder_crosscheck.json').read_text())
for x in top:
 if x['status']=='unresolved' and x['SECUCODE']=='920407.BJ':
  alias={'郑州戈斯盾企业管理中心(有限合伙)':'戈斯盾','宁波柯力传感科技股份有限公司':'柯力传感'}[x['HOLDER_NAME']]
  x.update(status='manual_alias_and_amount_match',alias=alias,glossary_page=5,table_page=32,review='issuer glossary maps full names; table current holdings checked visually')
dump(OUT/'top_holder_reviewed.json',top)
# Preserve descriptive formula checks; these are not automatic corrections.
roe=dict(symbol='002948.SZ',item='roe',api_percent=8.495,pdf_percent=16.99,pdf_page=8,pdf_basis='annualized',relationship='api * 2 == annualized PDF',decision='basis difference; retain both; full provider calculation not certified')
bps=dict(symbol='600236.SH',item='bps',api=2.295190526444,pdf_disclosed=2.62,pdf_page=10,parent_equity=20626849923.22,other_equity=2535291066.22,total_shares=7882377802,decision='basis difference; subtraction of other equity numerically reconciles; do not overwrite original bps')
bps['parent_equity_per_share']=bps['parent_equity']/bps['total_shares'];bps['excluding_other_equity_per_share']=(bps['parent_equity']-bps['other_equity'])/bps['total_shares'];dump(OUT/'ratio_basis_findings.json',[roe,bps])
checks=dict(original_reports=10,reviewed_financial_cells=70,local_comparisons=len(local),local_matches=sum(x['status']=='match' for x in local),holder_count_matches=10,top_holder_name_amount_text_matches=112,top_holder_manual_alias_matches=2,top_holder_percent_rank_fully_validated=False,original_pdf_parser_success=sum('parsed_rows' in x for x in receipts),original_pdf_parser_failure=sum('parser_error' in x for x in receipts),strict_pit_certified=False,asof_date_precision='date-only; source timestamps all midnight; not intraday certified',basis_differences=2)
dump(OUT/'verification.json',checks)
lines=['# CNEquity：10股财报与股东信息实质核对','', '日期：2026-11-14。沿用第一轮随机10股，不换样本。用户补充要求以财报等非行情信息为重点；本轮没有继续测试行情。','','## 结论','','CNEquity的财报数值和股东数据具备作为EP35候选来源的实质依据，已经不止是接口连通。但应通过字段口径映射接入，不能把全部字段直接当作可比较的因子，也不能把本次回填认证为历史严格PIT。','','- 10份2026半年报原始PDF均从巨潮取得，保留证券身份、公告查询分页、下载网址与SHA256。','- 营业收入、归母净利润、总资产、总负债、总权益、经营活动现金净额、资本开支7项×10股，共70项，按当期合并口径、单位和符号核对一致。','- 与EP35既有财务归档比较79个来源字段配对，79项金额一致；这是跨提供商一致性，不证明底层来源独立。','- 10家公司股东总数与原文一致；总股本在补齐桂冠电力窗口前基准后，10股均找到对应披露。','- 前十大股东114行：112行名称和持股数在原文文本对应，另2行通过驰诚股份释义表简称映射及表格视觉核对；未逐项验收全部比例、排序和流通股东字段。','- 原文PDF解析器仅4/10返回非空结果，6/10因版式/字段识别失败；成功的4家也只是部分字段，不能把它当成全自动原文核对完成率。','- 发现ROE年化、BPS权益扣除的口径差异，见下文；尚未建立历史修订完整链。','','## 逐股结果','','金额核对为上述7项。页码均为PDF物理页码，不一定等于印刷页码。股东数为报告披露的普通股股东总数，A+H公司不能直接解释成A股股东数。','','| 股票 | 核心金额 | 股东总数 | 原文解析器 | 原文公告日期 |','|---|---:|---:|---|---|']
for s in sample:
 sym=s['symbol'];rr=next(x for x in receipts if x['symbol']==sym);hc=next(x for x in holder_review if x['symbol']==sym);date=rr['notice']['adjunctUrl'].split('/')[1];lines.append(f"| {sym} {s['name']} | 7/7 | {hc['holders']:,} | {str(rr['parsed_rows'])+'项' if 'parsed_rows' in rr else '未识别'} | {date} |")
lines+=['','## 实际核对了什么','','### 1. 三张报表的金额、期间和单位','','利润表和现金流量表使用2026年1—6月累计数，资产负债表使用2026年6月30日期末数。没有把半年累计数当作二季度单季，也没有以母公司数字替代合并数字。总权益为包含少数股东权益的合计，不是归母净资产。','','青岛银行以人民币千元列报；其营业收入8,363,577千元，对应接口8,363,577,000元。现金流量表同时有本集团/本行及两年四列，本轮取本集团当期。资本开支在PDF列作现金流出(191,125)千元，接口以正支出金额191,125,000元表示；这是符号约定转换，不能称原始正负号完全一样。','','已审阅10家公司主要财务指标页的完整渲染图；其余核心字段结合报表标签、当前期/比较期列、单位与页码核对，银行符号及部分持股表另作视觉复核。70项不等于整个财报或全部302个解析项已核对。机器对照见reviewed_financial_cells.json，逐股字段表见本报告末尾。','','### 2. 公告日、修订与已取得时间','','CNEquity/东财业绩报表NOTICE_DATE，与10份巨潮半年报公告索引日及PDF路径日均一致。巨潮本批时间戳均为当天00:00，不能当作精确盘前发布时刻。公告查询仅覆盖2026-07-01至09-30，保留完整分页，筛选非摘要、非更正标题；不据此断言以后从未修订。','','驰诚股份的EP35旧归档同时存在8月6日、8月7日版本/日期，金额一致；本轮原始披露索引为8月6日。旧日期记录全部保留，没有覆盖。今天取得旧公告仍是今天取得，不能倒填observed_at。历史PIT完整性、多年修订、披露后下一个可交易时点尚未认证。','','### 3. 两项不能直接混用的比率口径','','**青岛银行ROE：** 接口8.495%，原文PDF第8页为年化16.99%，数值恰为两倍。该差异符合半年数与年化数的关系，但本轮未认证供应商完整计算过程。必须保留年化标记，再做行业比较，不能判成金额错误或默默改值。','','**桂冠电力BPS：** 接口2.295190526444元，经营讨论披露每股净资产约2.62元。归母权益20,626,849,923.22元÷7,882,377,802股≈2.61683；先扣其他权益工具2,535,291,066.22元再除股数≈2.295190526444。两者分母相同、分子口径不同，金额可对上，但不能把BPS一律定义成归母权益直接除总股本。青岛银行原文亦明确其普通股每股净资产扣除其他权益工具。','','### 4. 股本、股东和持仓使用边界','','桂冠电力第一轮2020年以来股本接口为空，新增查询1990—2019后找到了2019-07-10基准7,882,377,802股，与2026半年报一致。因此“本窗口没有变动”不等于“公司没有股本数据”。本次未回写第一轮空结果。','','兆威机电股东总数49,345含49,338名A股股东和7名H股股东，报告第53页有注释；接口股东总数不能冒充A股专属口径。其总股本267,564,250亦包含本轮新增H股等变化。','','维远股份前十大股东接口24行，其中15名持股3,500,000股者并列第10名，原文跨页列示这些名字。不能机械截断成10行，也不能把重复名次当作重复记录。驰诚股份的戈斯盾、柯力传感在表格使用简称，通过第5页释义与第32页持股表确认。','','前十大流通股东也返回114行，本轮只检查返回覆盖，未完成其逐项原文核验。前十大股东接口无NOTICE_DATE，不能把期末日当公告日；要使用本轮原文公告映射并继续保存实际取得时间。股东机构标记、季度持股变化也不等于行业资金净流入，尚不能据此宣布EP35“双拥挤”因子缺口已补齐。','','### 5. 原文解析的工程边界','','CNEquity的parse_report_pdf在桂冠电力、派克新材、维远股份、远东传动取得12/16/20/7项；其余6股报“no unambiguous supported consolidated figures”。成功解析项与东财有59个来源配对，均无超过0.02元差异，但有重复来源项，不能当59个独立字段。','','本轮人工表格核对成功并不修复这些解析器失败；若接入EP35，应把原文下载成功、自动抽取成功、字段一致与PIT资格做成四个独立状态。','','## 对EP35的建议与未完成项','','可以先接入三表原始事实、股本和股东披露证据，保留provider、原文哈希、报告期、公告日期、observed_at、单位与口径。先在这10股做多期稳定性与修订验证，再扩大范围。不要立即用BPS/ROE/股东机构标签生成跨行业排名。','','尚未完成：多年/多期连续覆盖、历史重述与原始版本完整性、全字段发行人核对、全部持股比例/排序及流通股东核验、经营分部/订单/产销、分析师预期、宏观产业、完整申万历史分类。没有更新EP35现有因子、模型或历史结论，没有全市场采集、部署、commit或push。','','## 证据入口','','`outputs/cnequity_fundamental_review_20261114/`保存协议、70项人工确认、79个旧归档对照、股东/股本/公告日对照、verification.json与SHA256清单。`data/cnequity_fundamental_review_20261114/`保存10份PDF、公告分页、股东原始响应、文本、部分解析和渲染图；沿用data忽略规则。第一轮目录不变。','','## 逐股原文及关键字段定位','']
labels={'revenue':'营业收入','net_profit':'归母净利润','total_assets':'总资产','total_liabilities':'总负债','total_equity':'总权益','net_cash_operate':'经营现金净额','capex':'资本开支（正支出额）'}
for s in sample:
 sym=s['symbol'];rr=next(x for x in receipts if x['symbol']==sym);lines += [f"### {sym} {s['name']}",'',f"[巨潮半年报原文]({rr['pdf_url']})；SHA256 `{rr['pdf_sha256']}`。",'','| 核对项 | 标准化金额（元） | PDF页 |','|---|---:|---:|']
 for x in review:
  if x['symbol']==sym:lines.append(f"| {labels[x['item_code']]} | {x['item_value']:,.2f} | {x['pdf_page']} |")
 lines.append('')
report=ROOT/'reports/CNEquity_10股财报与股东信息核对_20261114.md';report.write_text('\n'.join(lines));print(report);print(checks)
