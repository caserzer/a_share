# 源、首次版本及覆盖缺口

执行日：2026-10-21，Asia/Shanghai。质量门槛在 P0 冻结；不训练 Alpha，不覆盖 EP01—EP29。

本次登记了 14,669 份直接输入；原始网络响应保留在仓库外内容寻址归档。逐项 SHA、大小、来源域、许可及观测时间见 [input_sources.csv](../outputs/manifests/input_sources.csv)，全部网络成功/失败见 [source_attempts.jsonl](../outputs/audits/source_attempts.jsonl)。公共访问不构成批量再分发许可，新增收费、凭据或权限申请均未发生。

上交所接口本次返回主板 1,700、科创板 618、退市 148 行，分页总数校验通过。现时清单只支持今日观测和矛盾排查，不认证十年前存在/可交易。深交所 XLSX 两次请求 403；HTML 页面可访问但不能替代解析过的完整清单。北交所请求失败。巨潮首次错误查询返回空集，后续按公告检索取得原年报、更正、更新稿及索引，空集未解释成无公告。来源限制是本次材料的限制，不是断言公开历史永久不可取得。

| 旧口径 | 本次精确解释 |
| --- | --- |
| 4,915 | EP01 主板+创业板当前/退市元数据合集，含观察期前已退市；不是全 A 股 |
| 4,819 | 删除首月原点前退市90只、末原点后上市6只，得到 EP28 月度 D1 范围 |
| 318 | EP05 来源缺口：窗口内229、窗口外89，不能说318只当日停牌 |
| 229 | `active_in_requested_window` 表示曾在请求窗口上市，不表示今天正常活跃 |
| 228 | 上述窗口内缺源中的228只恢复了未复权报价；剩余 SZ000748，2017-01-18终止上市 |

| support_state | EP28_recovered_raw | legacy_raw | missing |
| --- | --- | --- | --- |
| missing_active_source | 228 | 0 | 1 |
| missing_inactive_source | 0 | 0 | 89 |
| supported | 0 | 4597 | 0 |

D2 新增可见官方记录625只（科创板618、额外主板4、额外退市3），形成 5,540 条临时身份记录；这仍不含可认证的全历史北交所及所有代码迁移，不称为全 A 股总体。完整集合差见 `universe_4915_4819_bridge.csv`、`official_reconciliation.csv`。

字段×证券×年份×板块见 [field_security_year_coverage.csv.gz](../outputs/audits/field_security_year_coverage.csv.gz)，聚合见 `field_year_board_matrix.csv`。行情覆盖的分母仅为临时清单×旧日历，其他域的分母仅为已缓存记录，真实全市场分母仍 UNKNOWN；不能拿非空比例冒充全市场覆盖率。

上交所[现存清单](https://www.sse.com.cn/assortment/stock/list/share/)与[退市清单](https://www.sse.com.cn/assortment/stock/list/delisting/)为主源；巨潮[原始披露](https://www.cninfo.com.cn/)为财报/权益材料主源；已有 AkShare/Sina 缓存作代理备源。逐字段主备及许可见 `configs/source_registry.yaml`，缺口闭合要求见质量报告。
