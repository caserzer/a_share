# P27：已检查本地版本未提供缺价补充证据

2026-11-11。只读本地源盘点，不进行网络采集、价格拼接或收益实验。该轮没有新预测模型。

## 行业指数资料

检查EP32 industry_v1、extension_v2/sources、source_probe内receipt，发现index_member 407、index_member_all 62、index_classify 5、index_basic 2、index_daily 3，以及1个批量receipt。3个index_daily请求分别是000985.CSI、000300.SH、000985.SH，属于已有市场基准/其代码请求，不是三级行业指数历史。

名称类似行业行情的L1.parquet实际是31条行业分类目录；EP30 proxy/industry抽查文件实际是行业分类表（code/name/sector/sub/发布日期等），并无价格字段。因此不能把这些文件当作可替代自建行业NAV的行情。receipt统计是接口请求存档，不代表每次请求均成功，也不证明全盘不存在其他行情。

## 缺价日期的多版本检查

P23的22条记录去掉行业审计案例重复后为20个唯一instrument/date，涉及11只股票。按已有身份表连接security_id，在4个已找到的价格根目录检查：

|版本|目标身份日期检查|文件存在|目标日记录|
|---|---:|---:|---:|
|ep30_d2/prices旧价|20|20|0|
|backfill_v2/normalized/prices|20|20|0|
|pit_v5/normalized/prices_qfq|20|20|0|
|EP32实际使用的封存release qfq|20|20|0|

多个版本并非独立供应商证据，不能以存在4份文件提升置信度。所有目标日期仍缺行，不能据缺行认证停牌或零收益。没有找到可核对复权链并直接补入的报价，因此没有修改P24未知状态。

## 边界与研究决策

这次检查限定于上述EP30/EP32目录和P23案例；还查看了缓存根目录、回填acquired目录结构，未穷尽整台机器、所有原始对象、外部系统或每个缺失日期。不能写成“本地绝无可用数据”。也没有从缺少替代源推导泛行业高胜率池不可能。

可据此停止的是“已有另一个价格版本可直接修复这些样本”的假设，以及基于无证据停牌填值的重建方案。继续保留P24的已知/未知区分和P25的缺失分解，不用回退旧重归一价格恢复表面覆盖。

P26仍是未达标基线，目录分数不得作为准入概率发布。下一项研究必须有明确尚未检验的信息依据或可核验的新本地数据线索；当前审计本身不提供这种预测信息，不据此自动发起新模型或超参搜索。原目标保持active、未完成，量化标准未改。

## 产物

industry_source_receipts.csv为接口与路径清单；index_daily_identity.json为3次请求身份；candidate_schemas.json为抽查文件字段；missing_date_source_checks.csv为80次身份日期查找；receipt.json为读取源哈希和检查边界。首轮遇到一个JSON批量receipt为list，改为显式BATCH_RECEIPT记录，未丢弃或误当单次接口。
