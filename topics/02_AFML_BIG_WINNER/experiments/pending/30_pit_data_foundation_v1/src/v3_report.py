"""Evidence-bounded v3 coverage, unresolved domains, and reproducible handoff."""

import json
import pandas as pd
from archive import EP, write_json
from v3_core import V3, PUBLIC3, V2_RELEASE, documents


def read(name):
    return json.loads((PUBLIC3 / (name + ".json")).read_text())


def build():
    status = read("historical_qualification_summary")
    rights = read("terminal_rights_summary")
    actions = read("original_action_summary")
    prices = read("exchange_overlay_summary")
    bridge = read("full_bridge_summary")
    finance = read("financial_chain_summary")
    parsing = read("financial_parsing_summary")
    ocr = read("retirement_ocr_summary")
    inv = pd.read_parquet(V3 / "normalized/securities.parquet")
    labels = pd.read_csv(PUBLIC3 / "strict_label_counts.csv")
    counts = []
    recovered_pairs = set()
    for group in ["core", "retirement", "financial"]:
        rows = documents(group)
        good = [r for _, r in rows if r["status"] == "ORIGINAL_PDF_RECOVERED"]
        counts.append(
            dict(
                group=group,
                attempted_unique_announcements=len(rows),
                recovered_pdfs=len(good),
                unresolved=len(rows) - len(good),
            )
        )
        if group == "financial":
            recovered_pairs = {
                (r["announcement"]["security_id"], r["announcement"]["report_period"])
                for r in good
            }
    pd.DataFrame(counts).to_csv(PUBLIC3 / "combined_document_coverage.csv", index=False)
    comparisons = []
    for p in (V2_RELEASE / "acquisition/documents/financial").glob("*.json"):
        r = json.loads(p.read_text())
        year = r["report_year"]
        pair = (r["security_id"], str(year) + "-12-31")
        comparisons.append(
            dict(
                instrument=r["instrument"],
                security_id=r["security_id"],
                report_year=year,
                v2_original_pdf_recovered=r["status"] == "ORIGINAL_DOCUMENT_RECOVERED",
                v3_original_pdf_recovered=pair in recovered_pairs,
            )
        )
    old = pd.DataFrame(comparisons)
    old.to_csv(PUBLIC3 / "v2_selected_financial_recovery_bridge.csv", index=False)
    recovered_old_gaps = int(
        (~old.v2_original_pdf_recovered & old.v3_original_pdf_recovered).sum()
    )
    sources = pd.read_parquet(V3 / "normalized/status_facts.parquet")
    sources["year"] = sources.effective_time.dt.year
    sources = sources.merge(
        inv[["security_id", "board_bucket"]],
        on="security_id",
        how="left",
        validate="many_to_one",
    )
    sources.groupby(["board_bucket", "year", "field"]).size().reset_index(
        name="original_event_fact_rows"
    ).to_csv(PUBLIC3 / "status_fields_by_board_year.csv", index=False)
    chains = pd.read_parquet(V3 / "normalized/financial_version_chains.parquet")
    chains["year"] = chains.report_period.str[:4].astype(int)
    chains = chains.merge(
        inv[["security_id", "board_bucket"]],
        on="security_id",
        how="left",
        validate="many_to_one",
    )
    chains.groupby(["board_bucket", "year", "form", "is_revision"]).size().reset_index(
        name="indexed_disclosures"
    ).to_csv(PUBLIC3 / "financial_versions_by_board_year.csv", index=False)
    gate_rows = [
        (
            "historical_membership",
            "PARTIAL",
            "BLOCKED",
            "原始离场事件和临时身份可读；全市场每日资格和完整上市身份链未认证",
        ),
        (
            "unadjusted_quotes",
            "PARTIAL",
            "BLOCKED",
            "交易所站点与供应商观察可诊断；历史首次版本和开盘可执行不可由日线推定",
        ),
        (
            "corporate_actions",
            "PARTIAL",
            "BLOCKED",
            "逐条公告合同字段已恢复；持有区间全事件独立完整性和实际现金到账未认证",
        ),
        (
            "terminal_equity",
            "PARTIAL",
            "BLOCKED",
            "确权代码与继受权益保留；最终财富、余股、锁定和真实清算未核验",
        ),
        (
            "financial_versions",
            "PARTIAL",
            "BLOCKED",
            "定期披露索引和选定年报原文、三版五字段回放；不是全市场逐字段全部修订认证",
        ),
        (
            "valuation_industry_macro",
            "BLOCKED",
            "BLOCKED",
            "本轮未接入新的历史行业版本、财务分母、宏观首次发布及预期版本",
        ),
    ]
    pd.DataFrame(
        gate_rows,
        columns=["domain", "evidence_delivery", "full_downstream_admission", "reason"],
    ).to_csv(PUBLIC3 / "domain_quality_gates.csv", index=False)
    summary = dict(
        version="D2-v3",
        inventory_securities=len(inv),
        retired_since_2017=rights["retired_since_2017"],
        combined_documents=counts,
        v2_financial_missing_periods_recovered=recovered_old_gaps,
        strict_label_rows=int(labels.rows.sum()),
        strict_known=0,
        full_daily_eligibility_ready=False,
        terminal_wealth_ready=False,
        full_financial_field_vintages_ready=False,
        independent_human_review=False,
        old_research_and_v1_v2_not_overwritten=True,
        scanned_ocr_candidates=ocr["code_link_candidates"],
        scanned_ocr_candidate_securities=ocr["candidate_securities"],
    )
    write_json(PUBLIC3 / "delivery_summary.json", summary)
    table = "\n".join(
        f"| {r['group']} | {r['attempted_unique_announcements']:,} | {r['recovered_pdfs']:,} | {r['unresolved']:,} |"
        for r in counts
    )
    six = labels[
        labels.horizon.eq("6_calendar_months") & labels.return_policy.eq("total")
    ]
    unknown = int(six.loc[six.status.eq("UNKNOWN"), "rows"].sum())
    censored = int(six.loc[six.status.eq("CENSORED"), "rows"].sum())
    report = f"""# EP30 D2-v3：历史资格、退市权益、严格标签与财报版本链

本轮已实际补取和重放原始数据。数据观察窗口固定至2026-10-21，完整月份原点截至2026-09-30。旧EP01—EP29、D2-v1和v2独立冻结版保持原样。**完整历史PIT、全部可执行收益和退市终值仍未认证，不能据此恢复Alpha训练准入。**

临时身份仍为{len(inv):,}个；通过正式摘牌原文补正旧元数据中7个2026年退市漏标，目标窗口离场身份现为{rights["retired_since_2017"]}个。原文、采集日、保守可知日及转换字节分别保留；当前查到的历史字段未改名为当年真实归档。

## 新取得的证据

| 公告组 | 唯一公告记录 | PDF已归档 | 原附件仍缺 |
|---|---:|---:|---:|
{table}

指数分页逐条验证请求证券和日期、总数、重复及缺页。退市板块完整枚举400000—400999语法空间，取得58,722条披露；该空间检索不等于历史成员或每家公司真实退市的证明。终止上市前后另对254个重点身份进行跨分类窗口检索，防止只查风险公告漏掉重大事项类别的最终摘牌公告。H2路径失败后按详情接口的真实附件地址另存恢复记录，原失败收据不覆盖；H22等镜像不是系统历史前瞻归档。

交易所站点新增264份历史观察，合并覆盖{prices["overlay_securities"]}个身份，补回{prices["previously_missing_fields_recovered"]:,}个原先未知字段，新增证券日{prices["new_security_dates"]}。{prices["new_unresolved_field_conflicts"]:,}个新字段冲突保留双方数值，对冲突字段返回UNKNOWN。其他证券继续引用不可变v2来源。官方当前历史服务不等于首次历史版本；正成交量不生成开盘可执行标记。

## 历史资格与股东权益

已提取{status["original_status_event_facts"]:,}条明确日期状态事件，涉及{status["securities_with_original_status_events"]}个身份；有{status["unique_original_termination_dates"]}个身份取得唯一的原文离场日期。决定终止上市与最终摘牌分开：乐视等公告中的决定日之后仍有退市整理交易，不能据决定日提前移出证券总体。子公司事件不冒充母公司离场。原始日期冲突、原上市身份冲突及可疑区间保留，不因取得一条离场事件就清空其他身份问题。

恢复{actions["original_contracts"]}份分红送转合同字段，其中{actions["original_contracts_since_2017"]}份的除权日在2017年起窗口；恢复{actions["explicitly_recovered_cash_payment_schedules"]}个计划现金支付日和{actions["explicitly_recovered_gross_cash_values"]}个明确税前每股现金金额。每10股口径显式转换；没有提及的送转比例不补0。支付安排保留代派/自派条款，不能当作所有账户已经到账。

有{rights["linked_securities"]}个稳定身份找到旧A股代码到退市板块代码的原文对应。另保留两条已复核换股合同：旧长城信息每股对应625/339股新长城电脑、旧武钢每股对应14/25股宝钢；比例、计划上市、账户余股、锁定、实际交付和出售分别处理。新权益账本对未核验认购、余股、实付现金和终值返回UNKNOWN。{rights["retired_since_2017"]}个目标离场身份的完整终值仍未知，没有默认清零或记作-100%。

229份扫描确权文件完成本地OCR，另得到{ocr["code_link_candidates"]}条代码对应候选、涉及{ocr["candidate_securities"]}个身份。模型、原图像素哈希、文本框与置信度保存，候选保持UNKNOWN/BLOCKED，未自动进入已核验对应表。上述已核验对应包含单独对中弘、众和、海润原扫描页1—2阅读确认的3例，核对者仍为agent，独立人工验收为false。

事件记录可查询，并不代表从一个停牌/撤销警示事件可以无限向后推定连续状态。`D2V3Dataset.get_asof`对完整每日状态不足处返回UNKNOWN；`latest_status_event`单列原文事件，避免把局部证据冒充全历史资格。

## 严格收益标签与全量桥接

本轮候选月度总体为{bridge["securities_with_candidate_months"]:,}个身份、{bridge["candidate_month_rows"]:,}个证券月份，范围{bridge["first_origin"]}—{bridge["last_origin"]}。没有完整月份的身份另列原因，不静默删除；旧桥接{bridge["legacy_rows_preserved"]:,}行的全部原列按值校验保持一致，合并表保留旧行与新总体的成员差异。新增月份或身份行{bridge["new_month_or_identity_rows"]:,}。

四个期限（6日历月、20/60/120交易日）乘三种口径（价格、含息、实际可执行）共重建{summary["strict_label_rows"]:,}条标签。六个月含息口径：到期未知{unknown:,}，未到期截断{censored:,}，严格已知0。未核验开盘执行、全持有期公司行动完整性、复杂权益和真实结算仍阻断数值；未知与截断均未填0。原点之前可知的原文事件行数单列，并保留生效与可知双重截断。

各行另存计划交易日开盘价差的Historical-proxy诊断；它不是首个真实可成交开盘、总收益、MFE/MAE或严格损失事件。由于正执行标记仍全缺，批量入口使用经断言验证的未知执行分支；出现任何明确执行标记时拒绝该快捷路径，必须回到完整顺序执行引擎。独立完整公司行动和实际权益账本仍是另行门槛。

诊断价差也屏蔽已知供应商停牌留价及跨摘牌终点，不能借留存报价暗代退市终值。状态事实和身份主表的输入SHA随桥接产物保存，校验防止读取旧一代资格输入。仅有停牌日期而无可靠日内时间的事件保守置于该日结束后；明确13:30等时点保留，不把下午停牌提前成上午不可交易。

## 财报版本链

完整索引整理出{finance["logical_report_chains"]:,}条报告链、{finance["classified_disclosure_rows"]:,}条可归属版本记录，其中{finance["revision_rows"]:,}条带修订标志。旧北交所代码及新三板披露分别补查后去重；原报、摘要、财务报表、更正公告分开，同日未知先后不按公告号伪造顺序。元数据无法确定主体或报告期的行另存，不能用供应商UPDATE_DATE填首次披露。

按事先确定规则归档{finance["annual_original_queue"]:,}份候选年报，恢复原v2缺失队列中的{recovered_old_gaps}个公司年度。提取{parsing["original_value_candidates"]:,}个原页数值候选；候选仍为UNKNOWN/BLOCKED，不能自动进入PIT特征。

泰鹏智能2020年年报的2021-04-20原版、2021-06-23更正版、2023-04-04更正版另作5字段×3版本的原页复核。原经营现金流4,456,443.98元，2023版为-4,549,865.76元。核对原页第9页及财务报表重复列示，明确本期列和CNY单位，按保守下一验证交易日追加supersedes链。`financial:reviewed_reported_*:2020-12-31`仅表示已复核版本集合，不声称所有补充公告已逐字段闭合；规范化财务全量准入仍受阻。2023-04-04收盘仍读旧值，2023-04-06 09:30后读新值；删除未来版本不改变过去结果。系统归档时间未倒填为2021或2023。

## 验证、封存与剩余门槛

运行顺序：`v3_announcements.py --phase core`、财报完整索引、`v3_terminal_windows.py`、`v3_retirement.py`、`v3_financial.py`、`v3_recover_attachments.py`；生产者全部结束后执行`v3_parse_core.py`、`v3_parse_financial.py`、`v3_status.py`、`v3_prices.py`、`v3_actions.py`、`v3_rights.py`、`v3_financial_review.py`、`v3_bridge.py`、测试、`v3_validate.py`、本报告及`v3_freeze.py`。所有补数过程可恢复到已验证分区；附件恢复记录追加，不覆盖失败尝试。

`outputs/pit_v3/validation.json`记录原字节离线重放、旧研究保护哈希、v1/v2冻结字节及标签空值校验。`outputs/pit_v3/release.json`为独立封存入口，包含原始响应、旧版本实际转换字节、规范化Parquet、完整v2基线、代码配置与全文件SHA。缓存和原PDF仅在本地私有目录，不提交到Git。本轮未训练模型、购买数据、申请凭据或提交/推送仓库。

附件详情接口出现持续HTTP 567和代理断连后已停止该主机的新请求；恢复50份附件，剩余267条当前文档缺口保留失败或停止后未请求的原因。2012页披露索引、264份交易所站点历史、11,737个原始响应摘要和受保护旧产物已离线核验。格式检查限本轮新增文件；旧backfill_freeze.py已有格式差异且与v2封存字节相同，未为格式改写旧版本。

仍阻断：全市场每日历史成员和资格、全部原始交易状态/限价与开盘执行；真实现金到账及配股、锁定、余股和退市最终权益；全部财务三表逐字段首次版本与修订完整性；历史行业、财务估值分母、宏观及预期版本。独立人工验收为false。按域、板块和年份的计数另列CSV；有事件或有PDF不等于该域已经READY。
"""
    (EP / "reports/pit_v3.md").write_text(report)


if __name__ == "__main__":
    build()
