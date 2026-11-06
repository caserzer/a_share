# EP32发布记录：2026-11-06

[最新报告入口](LATEST.md) · [最终汇总验收](extensions/v28_aggregate_acceptance/reports/accepted_method.md) · [发布前审计](publication_audit.json)

本次提交包含行业轮动观察、完整历史复查、RD-Agent及后续探索、冻结证据、测试和历史名单。原README及各阶段报告保留当时状态，最新结论以LATEST和V28为准。

按用户确认的历史汇总门槛，precision24.65%、周期recall44.39%达标；年度/频率回退、未知标签和延迟完整保留。严格PIT仍BLOCKED_DATA，独立前瞻FORWARD_PENDING，未部署生产。

发布前验证：29份清单、1131个不同清单文件及1146项前序哈希均匹配；12组既有测试共65项通过，124个Python文件语法检查通过；最终验收原有302项检查记录核对通过。初次测试启动器错误地解析了虚拟环境解释器软链接，保留虚拟环境路径后全部测试通过，研究源文件未改动。

凭证扫描包括23个压缩研究表，未发现匹配项。单文件最大约17MB；Parquet、pickle、Python缓存和私有大表不纳入提交。复跑依赖本地缓存或按各阶段方案重建输入，缓存本身不上传。
