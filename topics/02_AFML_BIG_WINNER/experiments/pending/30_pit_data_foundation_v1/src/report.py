"""Generate evidence-bounded EP30 reports from local audit results."""

import json
import pandas as pd
from archive import EP, write_json


def table(f, columns=None):
    f = f[columns] if columns else f
    lines = [
        "| " + " | ".join(map(str, f.columns)) + " |",
        "| " + " | ".join(["---"] * len(f.columns)) + " |",
    ]
    for r in f.itertuples(index=False, name=None):
        lines.append(
            "| "
            + " | ".join(
                "UNKNOWN"
                if pd.isna(x)
                else f"{x:.8g}"
                if isinstance(x, float)
                else str(x)
                for x in r
            )
            + " |"
        )
    return "\n".join(lines)


def main():
    a = EP / "outputs/audits"
    reports = EP / "reports"
    reports.mkdir(exist_ok=True)
    summary = json.loads((a / "summary.json").read_text())
    status = json.loads((a / "status_summary.json").read_text())
    vintage = json.loads((a / "financial_vintage_example.json").read_text())
    validation = json.loads((a / "validation.json").read_text())
    identity, quotes, domains, bridge = [
        summary[k] for k in ["identity", "quotes", "domains", "bridge"]
    ]
    expanded = json.loads((a / "expanded_bridge_summary.json").read_text())
    gap = pd.read_csv(a / "source_gap_318_229_228_bridge.csv")
    shares = pd.read_csv(a / "share_history_audit.csv")
    fin = pd.read_csv(a / "domain_file_inventory.csv")
    bounds = pd.read_csv(a / "population_event_bounds.csv")
    old_bounds = pd.read_csv(
        EP.parent
        / "28_literature_guided_tail_risk/outputs/audits/population_event_bounds.csv"
    )
    header = "执行日：2026-10-21，Asia/Shanghai。质量门槛在 P0 冻结；不训练 Alpha，不覆盖 EP01—EP29。\n\n"

    def report(name, title, text):
        (reports / name).write_text("# " + title + "\n\n" + header + text + "\n")

    report(
        "source_gap_audit.md",
        "源、首次版本及覆盖缺口",
        f"""本次登记了 {validation["source_files_hashed"]:,} 份直接输入；原始网络响应保留在仓库外内容寻址归档。逐项 SHA、大小、来源域、许可及观测时间见 [input_sources.csv](../outputs/manifests/input_sources.csv)，全部网络成功/失败见 [source_attempts.jsonl](../outputs/audits/source_attempts.jsonl)。公共访问不构成批量再分发许可，新增收费、凭据或权限申请均未发生。

上交所接口本次返回主板 1,700、科创板 618、退市 148 行，分页总数校验通过。现时清单只支持今日观测和矛盾排查，不认证十年前存在/可交易。深交所 XLSX 两次请求 403；HTML 页面可访问但不能替代解析过的完整清单。北交所请求失败。巨潮首次错误查询返回空集，后续按公告检索取得原年报、更正、更新稿及索引，空集未解释成无公告。来源限制是本次材料的限制，不是断言公开历史永久不可取得。

| 旧口径 | 本次精确解释 |
| --- | --- |
| 4,915 | EP01 主板+创业板当前/退市元数据合集，含观察期前已退市；不是全 A 股 |
| 4,819 | 删除首月原点前退市90只、末原点后上市6只，得到 EP28 月度 D1 范围 |
| 318 | EP05 来源缺口：窗口内229、窗口外89，不能说318只当日停牌 |
| 229 | `active_in_requested_window` 表示曾在请求窗口上市，不表示今天正常活跃 |
| 228 | 上述窗口内缺源中的228只恢复了未复权报价；剩余 SZ000748，2017-01-18终止上市 |

{table(pd.crosstab(gap.support_state, gap.source).reset_index())}

D2 新增可见官方记录625只（科创板618、额外主板4、额外退市3），形成 {identity["provisional_inventory"]:,} 条临时身份记录；这仍不含可认证的全历史北交所及所有代码迁移，不称为全 A 股总体。完整集合差见 `universe_4915_4819_bridge.csv`、`official_reconciliation.csv`。

字段×证券×年份×板块见 [field_security_year_coverage.csv.gz](../outputs/audits/field_security_year_coverage.csv.gz)，聚合见 `field_year_board_matrix.csv`。行情覆盖的分母仅为临时清单×旧日历，其他域的分母仅为已缓存记录，真实全市场分母仍 UNKNOWN；不能拿非空比例冒充全市场覆盖率。

上交所[现存清单](https://www.sse.com.cn/assortment/stock/list/share/)与[退市清单](https://www.sse.com.cn/assortment/stock/list/delisting/)为主源；巨潮[原始披露](https://www.cninfo.com.cn/)为财报/权益材料主源；已有 AkShare/Sina 缓存作代理备源。逐字段主备及许可见 `configs/source_registry.yaml`，缺口闭合要求见质量报告。""",
    )
    recon = (
        pd.read_csv(a / "official_reconciliation.csv")
        .groupby("official_source", as_index=False)
        .agg(
            rows=("instrument", "size"),
            legacy_present=("legacy_present", "sum"),
            listing_date_match=("listing_date_match", "sum"),
            delisting_date_match=("delisting_date_match", "sum"),
        )
    )
    report(
        "universe_status_pit.md",
        "证券身份、历史状态与交易资格",
        f"""已建立稳定的 D2 上市事件 ID 与代码映射。ID 用交易所、代码、上市日确定生成；转板、重新上市、代码变更的跨事件连续性尚待原公告核对，旧代码不自动合并。别名区间与元数据 schema 已定义。现时简称不回填历史，今日 ST 不决定历史成员。`universe_asof` 只返回指定质量级别的已证存在记录，交易资格单独返回 UNKNOWN。严格查询空集表示证据阻断，不表示当时没有股票。

{table(recon)}

三条旧/新上市日期不一致与退市日期差异逐行保留在 `official_reconciliation.csv`；没有静默采用对历史收益有利的日期。当前名单也不能发现全部过往代码重用。

深市有 {status["sz_name_event_rows"]:,} 条有日期的更名记录，其中 {status["sz_ST_transition_rows"]:,} 条变更后简称含 ST。使用历史的“变更后简称”，不用当前“证券简称”。它们缺原风险警示公告发布时间，不升级为完整 ST/退市整理状态。沪市 {status["sh_undated_name_files"]:,} 份更名缓存中，仅119份有 name 列，其余1,587份只是 `no_tables_found` 被旧采集解释为无更名的占位；不能据此证明从未 ST。119份历史名中34只含 ST，但没有可信日期。旧终身 ST 排除仅用于偏差审计。

缺价拆成未上市、退市、经公告证明的停牌、来源失败和 UNKNOWN。现有缺 bar 不直接推断停牌；成交记录也不能证明涨跌停队列能成交。全市场逐日停复牌、价格限制制度和可成交开盘仍 BLOCKED。日期/月报样例存在，尚无证券×交易日完整对账。

科创板从[2019-07-22实际开市](https://www.sse.com.cn/aboutus/mediacenter/conference/c/c_20191213_4965555.shtml)、北交所从[2021-11-15实际开市](https://www.bse.cn/company/introduce.html)开始适用；精选层挂牌日不能代替北交所上市日。逐层范围见 `quality_by_domain_year_board.csv`。

按冻结规则选择的6条证券时间线见 `representative_timelines.csv`。这是机器辅助证据核查；完整公告链、独立人工审核尚缺，一致率保持 UNKNOWN。补齐要求：每段历史上市成员/状态原公告、有效时刻、源码/原文哈希及人工签核；不得从今天名单倒填。""",
    )
    report(
        "corporate_actions_total_return.md",
        "公司行动、终止权益与三种收益",
        f"""已规范化 {quotes["raw_source_securities"]:,} 只证券的 {quotes["rows"]:,} 条有效未复权报价；7条异常记录保留隔离清单。股本历史 {quotes["share_history_files"]:,} 份，支持原中文字段和显式 shares 单位的规范缓存。无未来股本向前填充。冲突日期 {int(shares.conflicting_dates.sum())} 个，非法/不能解析行 {int(shares.invalid_rows.sum())} 条；这些数值只审计现存缓存，不证明历史首次版本。

旧 EP24 公司行动缓存包含现金/送转及配股表，但公告/方案/实施、登记、到账、股数权利与退市终值未形成同一持仓事件账。71份 Parquet 含分页与 all/probe 重叠，66,026是读取行数，绝不是66,026个独立行动。两份 all 表分别为32,680条分红/送转记录与70条配股记录；均需独立审核去重、实施状态和支付日期。

冻结新标签：D收盘决策；D之后第一个有明确买入可执行证据的开盘；目标为D+6日历月后首交易日或D+20/60/120交易日；到目标后首个明确卖出可执行开盘退出。买入延迟至目标以后则 UNKNOWN。结果可见前一律 CENSORED。MFE/MAE 为持有期间收盘权益价值路径（不是盘中 high/low），包含入场零点与实际退出值。

- price：未复权开盘价比值，单独标记非总收益，拆股可使其经济解释失真。
- total：毛现金股息持有、不再投资；包含已获现金应收和已验证股份权利。
- executable：实际到账现金与可交付股份，显式往返成本；退出后尚未支付的现金权利保持CENSORED，到账后才成熟，不能当即时可用现金。

`LabelBuilder` 已实现现金分红、简单拆分、执行延迟、明确停牌路径、未成熟/缺源阻断及 MFE/MAE。配股、重整、跨代码换股和退市终止权益缺完整持仓账时明确阻断；settlement不默认0或−100%。当前真实数据的 can_buy/can_sell 均未知，所以三套正式 D2 标签均无已认证结果；测试夹具可算不代表真实数据 READY。

{table(bounds)}

D2 [0,1]界仅以D1原点为条件；全历史真实证券总体仍未知，不能宣称无条件发生率界已识别。缺退市清算时没有依据选0、最后价格或全损为可信点场景；只能保留全范围逻辑界。补齐要求：原实施/登记/支付/股份交付/换股/终止结算公告与回执，按持仓计算逐笔权益、现金及订阅流出。""",
    )
    report(
        "financial_vintage_audit.md",
        "财报首次版本和修订",
        f"""完整财务表仍 BLOCKED，但取得并重建了一个真实财务附注项目的首次/更正链，未把整个域一概视为原版不可获得。

SZ000584 的2023年年报其他应收款“往来款期末余额”，原始文件第168页为91,685,852.54元；2024-07-31更正公告第1页改为37,014,048.62元。两份巨潮原文与公告检索索引均存档并验证 SHA；首次报告的供应商镜像与巨潮原文 SHA 相同。原公告日期为2024-04-30，更正为2024-07-31；无可信小时，保守于下一交易日开盘可用。严格 as-of 结果：

{table(pd.DataFrame([dict(time=k, **v) for k, v in vintage["values"].items()]))}

该单字段以 PIT-reconstructed 保存，两次披露分版本并以 supersedes 相连。删除更正来源后，2024-07-31之前结果不变；2024年的 Archived as-of 仍为空，因为本系统2026年才保存这些材料。证据见 `financial_vintage_example.json`。此例按修订机制取样，不按模型得分取样，不能推断市场整体修订率。

现存1,647份财务供应商缓存共122,947条记录，其中 {int(fin.loc[fin.domain.eq("financials"), "update_after_notice"].sum()):,} 条 UPDATE_DATE 晚于 NOTICE_DATE；不等同于85,473次经济意义上的重述。UPDATE_DATE不能代替首次披露，历史利润、ROE等数值也可能已修改。独立 proxy 分区保留原 NOTICE/UPDATE/REPORT_DATE；代理读取显式标记其日期只是供应商提示。

PIT基础层可保存任何经原文审核的首次与更正，proxy层接受供应商历史表但不升级。单字段样例不等于完整三表、审计报告、预告/快报全覆盖。首次报告原文字节可得率仅在本次靶向样例中验证1/1，不能外推为122,947条缓存记录的认证率；独立人工审核0，整体认证率UNKNOWN。

原文：[首次年报]({vintage["original_source"]})、[更正公告]({vintage["correction_source"]})。源码按页和行唯一匹配；没有批量公布PDF或供应商原文。""",
    )
    report(
        "valuation_industry_pit.md",
        "估值、行业及宏观历史版本",
        """估值代理1,646份、3,313,649条；财报和股本须按可知版本、真实生效日、相同未复权价格日期重建市值与 PE/PB/PS。接口保留负盈利、非正权益、缺分母为UNKNOWN，不能用当今股本或未来重述补过去。原供应商历史估值留在proxy层；不将历史 TRADE_DATE 当当日数据库版本证明。

行业19份历史表、82,897条解析观察值及对应PDF/页面/解析回执均登记，旧分类不被当前概念替代。EP24—EP29已有按发布日期选择快照的约束值得复用，但检索脚本、PDF哈希与发布时间都需要进一步逐表复核；陈旧分类与2021—2023版本空档保留。新官方科创板证券加入身份盘点，不意味着补齐了它们的历史行业。

宏观 public_yields 有10份缓存、7,050条观察值；观察日不是首次发布/修订时间。分析师预测及概念等没有认证首次版本，均列BLOCKED，不因已有proxy就擅自接入严格特征。

`reconstruct_valuation` 提供单位明确的确定性计算；调用前须对价格日期、有效股本和财务报告期/可知时间逐项审核。Qlib 适配同时返回每个特征值的来源记录ID/质量/缺失原因，不移除 provenance 后冒充认证输入。补齐要求：首次与更正分母原件、历史行业官方版本和生效日、宏观首次发布与修订、预测原始发布时间。""",
    )
    report(
        "D0_D1_D2_bridge.md",
        "D0、D1、D2桥接及重大亏损敏感性",
        f"""冻结 D0 43,960行、D1 452,846行。逐股票月外连接仍452,846行，重合43,960行，重合且可比较的旧六个月收益最大差0、差异数0。旧标签口径为月末收盘到目标日后首交易日收盘的前复权代理；新 D2 开盘执行与权益账口径不同，不能直接比较模型分数或把旧收益复制成新标签。

旧口径兼容投影逐证券见 `bridge_by_security.csv`，逐月见 `bridge_by_month.csv`，逐期限/收益合同见 `bridge_by_label_contract.csv`；逐股票月完整桥表存在受控外部Parquet，SHA见缓存清单。D2严格成员值false只是未获准进入认证层，原因列明确阻断，不宣称历史上不存在该证券。

另提供扩展D2临时身份桥表 `security_month_labels_expanded.parquet`：同一旧已核验窗口共有{expanded["rows"]:,}个候选股票月，比D1新增{expanded["added_provisional_origins"]:,}个，新增证券的旧收益及新收益均保持UNKNOWN。逐证券覆盖完整临时清单见 `bridge_expanded_by_security.csv`，逐月见 `bridge_expanded_by_month.csv`。新增成员不被旧兼容投影静默丢弃；更新窗口、北交所及身份真实性仍保持阻断。

{table(bounds)}

下表从原EP28保留的子总体审计重现，不作模型比较：

{table(old_bounds, ["population", "mature", "known", "missing", "events", "rate_lower", "rate_upper"])}

恢复报价子集有30.61%已知重大亏损率，旧报价子集14.22%；总体、成员和缺失机制不同，这不是新增模型的信息增量。退市恢复子集1,128个成熟缺失让界仍约24.61%—44.21%。旧D0有25个成熟缺失；即使旧D0上缺失敏感性较小，不能忽略池外证券及公司行动。

因此足以改变旧结论的缺口包括：沪市终身ST未来排除、缺源/退市总体、换股及终止结算、现金与股份权利、修订财报和供应商回填行业。当前只能识别这些偏差可能改变结论，不能在D2未知时声称已经算出纠偏后的收益/风险或推翻旧研究。旧实验原始结论完整保留。""",
    )
    gates = []
    reasons = {
        "identity": "历史成员/跨代码连续性/官方历史对账未闭合",
        "raw_prices": "首次报价版本未认证；新增板块和2026-05-29后OHLCV未补齐",
        "status": "ST/停复牌/整理期/价格限制/可执行开盘缺逐日公告链",
        "shares": "有生效日代理，缺首次披露版本与全证券覆盖",
        "corporate_actions": "缺完整实施、支付、股份权利及终止结算持仓账",
        "financials": "仅一个附注字段原始/更正重建；非完整财报覆盖",
        "valuation": "价格、股本、财务分母首次版本未全闭合",
        "industry": "历史快照存在；完整历史分类与版本认证不足",
        "macro_forecasts": "宏观首次发布/修订及预测原件未认证",
        "labels": "可执行时点/权利账阻断，不能借前复权代理充数",
    }
    for domain, reason in reasons.items():
        for board in ["main_board", "chinext", "star", "bse"]:
            for year in range(2017, 2027):
                applicable = not (
                    board == "star" and year < 2019 or board == "bse" and year < 2021
                )
                gates.append(
                    dict(
                        domain=domain,
                        board=board,
                        year=year,
                        period="2017-01-03_to_2026-10-21_intersect_year",
                        strict_gate="BLOCKED" if applicable else "NOT_APPLICABLE",
                        proxy_gate="PARTIAL"
                        if applicable and board in ["main_board", "chinext"]
                        else "BLOCKED"
                        if applicable
                        else "NOT_APPLICABLE",
                        reason=reason,
                        allowed_downstream="diagnostics_only_no_new_Alpha"
                        if applicable
                        else "none",
                    )
                )
    pd.DataFrame(gates).to_csv(a / "quality_by_domain_year_board.csv", index=False)
    decision = pd.DataFrame(
        [
            dict(
                domain=k,
                strict="BLOCKED",
                available="PARTIAL_PROXY_OR_ONE_FIELD_RECONSTRUCTION",
                reason=v,
            )
            for k, v in reasons.items()
        ]
    )
    report(
        "quality_gate_report.md",
        "质量指标、下游准入与阻断范围",
        f"""质量门槛见冻结配置。READY要求原始版本、完整分母、源哈希/快照重建、独立人工核验及零泄漏共同满足。代码能跑不发READY。

{table(decision)}

| 强制指标 | 本次结果 | 分母和限制 |
| --- | --- | --- |
| 历史全市场元数据/退市对账 | BLOCKED | 临时5,540条，非认证全市场 |
| 原始行情覆盖 | 4,825只、9,091,310条 | 各板块年份及代理分母逐格列示 |
| ST/停复牌覆盖 | 深市7,398更名事件，完整日状态0认证 | 不能将0认证解释成0次停牌 |
| 股本冲突/缺失 | 冲突日期{int(shares.conflicting_dates.sum())}，非法行{int(shares.invalid_rows.sum())}；临时清单缺源{identity["provisional_inventory"] - quotes["share_history_files"]}只 | 仅现存4,597个文件；首次版本仍未认证 |
| 退市最终权益未知率 | 100%未认证 | D1范围229只退市证券；不是断言其权益为0 |
| D1到期6月价格代理 | 256,637已知 / 2,411缺失 | 另22,926尚未成熟，按旧截止 |
| D2总收益/执行收益 | 0获准、原点条件下全部UNKNOWN/CENSORED | 不将其填入模型 |
| 财报原版/首次时间 | 1个字段、2个版本可重建 | 不外推完整三表覆盖；小时未知用次日规则 |
| 历史行业版本 | 19份可追溯代理快照 | 认证全市场历史版本覆盖仍UNKNOWN |
| 泄漏测试 | 见adversarial_validation.json及tests.json | 同时包含合成机制与真实财报回放 |
| 独立人工核查一致率 | UNKNOWN，0独立人工样本 | 6条机器辅助时间线不冒充人工 |
| 原始快照重建 | SHA/Parquet与as-of往返回放 | 验证报告列出实际分子分母 |

各域×板块×年份详见 `quality_by_domain_year_board.csv`；各字段×证券×年份×板块见压缩矩阵。科创板/北交所开市前NOT_APPLICABLE；开市当年的起点按真实日期，不能把全年当作已经上市。2017之前不扩展。本次2026-05-30至2026-10-21未复权OHLCV、状态与权益不是已验证数据，日历不自动生成事实。

关闭受阻域的补齐条件：可验证的历史成员总清单、真实状态公告区间、公司行动与退市现金/股份结算、首次财报原件和修订链、历史分类、原版宏观/预测及独立抽查。现有授权下已进行了缓存普查、官方名单与原文可达性调查；不作新增付费订阅或权限申请。受阻裁决仅对应当前证据范围，后续可以新增D2版本，不覆盖本版。

允许：源核验、显式proxy诊断、原财务样例as-of验证、补录原文及契约测试。禁止：认证全市场特征/标签训练、正式Alpha验证、部署、把D0/D1旧分数当D2表现。""",
    )
    report(
        "final_conclusion.md",
        "EP30 本轮交付与裁决",
        f"""本轮完成了P0源/口径普查、D2版本化基础接口、全缓存规范化、分域阻断证据、对抗性机制验证与D0/D1/D2桥接。按GOAL允许的“可复现结果或明确受阻证据”关闭本轮；全历史全市场PIT数据与正式可执行总收益仍BLOCKED。

具体结果：

1. 4,915与4,819差额为90只早已退市+6只末期新上市；原229是窗口内上市过，不是229只今日正常活跃股。228只恢复报价，不等于权益和结算恢复。
2. 旧4,915主板/创业板清单新增625条当前官方观察记录，临时身份5,540条，北交所及跨代码历史仍不全。现存名单没有倒填为认证历史成员。
3. 4,825只、9,091,310条有效未复权报价与4,597份股本缓存进入仓库外Parquet；7条异常记录保留隔离。数据行情截止仍2026-05-29，不能冒称已更新至运行日。
4. 提供historical/archived as-of、执行/现金权利标签引擎、Parquet与Qlib适配。严格层不接收proxy；有日期无时刻采用次交易日可用；冲突与缺结算fail closed。
5. 真实巨潮年报首次/更正的一个附注字段实现PIT-reconstructed回放，显示历史首次版本有局部可取得路径；不将此推广为完整财务认证。
6. 原D0共43,960行与D1重合收益最大差0，旧原始实验{validation["prior_files_checked"]:,}文件哈希未变；无新Alpha模型。新标签执行口径不同，未将旧前复权收益冒充D2。
7. 旧D1成熟结果仍缺2,411个；真正总收益、终止权益、原始版本和全市场分母的未知足以改变历史研究解释，目前不能计算可信纠偏模型表现。

运行与重建见[README](../README.md)，逐域质量及补齐条件见[质量报告](quality_gate_report.md)。本次没有独立人工审核、付费采购、模型训练、生产发布或Git提交。证据和机器验证通过只说明本版工程与审计自洽，不能发放完整PIT READY。

本轮最终状态：`D2_foundation_and_gap_audit_delivered`; `full_market_PIT=BLOCKED`; `total_return_and_execution_labels=BLOCKED`; `alpha_training_authorized=false`。""",
    )
    write_json(
        a / "final_decision.json",
        dict(
            delivery="D2_foundation_and_gap_audit_delivered",
            closure_basis="GOAL_DoD_reproducible_results_or_precise_blocked_evidence",
            full_market_PIT="BLOCKED",
            total_return_and_execution_labels="BLOCKED",
            alpha_training_authorized=False,
        ),
    )
    print("reports generated", flush=True)


if __name__ == "__main__":
    main()
