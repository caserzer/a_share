# R184 统一的修复版本地历史重放命令

## 想验证什么
R181/R182是固定日期实验，原R18 CLI仍有旧源默认值。为避免调用者绕过时点修复，本轮提供显式来源清单和截止日的独立历史入口，并通过真实CLI调用而非只测内部函数验证。

## 入口与边界
src/historical_replay.py提供capture、evaluate、verify三个子命令。capture和evaluate必须指定--asof、--sources、--store；evaluate还必须指定capture返回的receipt目录。verify使用--receipt核查封存包与底层结果。

来源清单必须包含daily、assignments、l1、market、catalog五种角色及各文件SHA256，声明Historical-proxy和max_asof。无隐式最新数据、无forward模式。截止日必须是明确日期、不得超过来源上限且必须存在于基准日历；数据读取前后以不可变副本哈希核对，源清单自身变化也被拒绝。

重放使用R181适配与R182评价边界，副本及底层结果之外再保存一个不可变执行收据，绑定来源清单、适配/评分/版本代码、协议及结果manifest。收据验证连同底层源及输出校验，避免只有包装结果而缺少可追溯输入。临时准备目录退出后清理，持久副本在指定store内。旧R18历史入口不删除，推荐使用本入口进行修复数据的历史重放。

## 真实运行结果
9次CLI调用完成：6月30日捕获两次、10月21日评价、7月15日历史回退、收据验证，以及4个预定拒绝场景。重复捕获返回同一收据；回退未改动较晚评价或原观测。全部511条观测与R181逐列相同，两个评价的2044条记录与R182逐列相同。拒绝场景包括缺少asof、超出来源上限、评价早于观测、清单中daily哈希不符。故意错误清单标明intentionally_invalid，原始数据未改。

新命令没有改变评分、收益、成本假设或默认研究发布。原研究来源仍截止2026-10-21，所有记录均为historical_replay，前瞻记录0。来源哈希匹配不证明供应商首次发布时点，成员日期仍是来源快照日期。

## 使用示例
以下路径均为本地冻结材料。先运行capture，将返回JSON的receipt值传给evaluate的--snapshot，而非底层observations目录。

```bash
EP35=/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/35_industry_rise_mechanisms_and_rotation
PYTHON=/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/.venv/bin/python
"$PYTHON" "$EP35/src/historical_replay.py" capture --asof 2026-06-30 --sources "$EP35/outputs/r184/frozen_sources.json" --store "$EP35/data/manual_historical_replay"
```

评价命令为同一脚本的evaluate子命令，指定--asof 2026-10-21、相同--sources/--store，并将捕获收据的绝对目录作为--snapshot。不能用本清单重放超过2026-10-21的日期；补充新源需先核查来源、授权、模式和哈希，不能只修改日期上限。

## 能与不能下结论
本轮补齐可调用工程入口，证明冻结数据上的可复核一致性及明确拒绝条件，不产生新的领先性、独立信息或经济机制证据，也不证明成本后配置价值。缺失、待成熟和失败研究保持原边界。没有自动调度、外部采集、部署或发布。

下一项重新审计剩余目标依赖，区分尚可执行的研究遗漏、必须新增来源的缺口和等待未来样本的事项，不继续为通过工程测试而扩展无必要功能。当前目标入口R183的“单一重放入口”下一任务已由本轮完成，其余未完成项不能据此消失；后续整合时更新该状态。

## 产物
protocols/r184.json；src/historical_replay.py、src/replay_cli_smoke_r184.py；tests/test_historical_replay_r184.py；outputs/r184/frozen_sources.json、cli_calls.json、verification.json及故意错误清单；data/replay_cli_r184为隔离验证存储。整体目标未完成。
