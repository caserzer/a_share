# 方法与评价卡

## 当时可执行的规则

每个完整交易周复核全目录，分类制度和行业身份分别处理。仅使用同价格链的已知价格；40日历史支持、近5日和20日收益为正时有准入资格。按20日收益降序及行业代码打破同分，从可入池名单依次新增，数量为5、当前空位和可选行业数的最小值，允许空池。

已有在池行业每周更新：5日上行为继续改善证据，否则标风险/未继续改善。身份或同链数据不可用退出；连续两次周复核20日收益非正退出；入池达到8个观察周退出。退出后至少4个观察周可重新入池。新观察ID不自动等于新价格机会。

相对市场收益作背景，量能、扩散、事件与基本面不是当前入池条件。价格信号不确认订单、盈利或配置价值。当前规则见[清单说明](/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/34_industry_price_observation_radar/outputs/refresh/s02_chain_safe_v2_20261112/delivery/A/latest_review.md)；原始规则代码为本实验src/v2_observation_refresh.py。

## 独立的事后评价

父过程由全目录周内对数价格中位数识别：起点之前8周尺度、可辨上升、连续保持确认、冻结尺度的对称回撤中断。完整数值和反例见[L03-S原型](/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/34_industry_price_observation_radar/reports/R00_v2_L03_path_prototype.md)。强势过程内部新增增强用独立路径斜率变化及持续支持原型，见[H03-R原型](/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/34_industry_price_observation_radar/reports/R00_v2_H03_enhancement_prototype.md)。这些都是研究假设，不应称用户确认的成功定义。

一条有当时价格依据的NEW/UPDATE至多取得一个主过程身份；父子覆盖并集分别计。首次误报不抹去，后来UPDATE仍可首次覆盖；重复新增不增成功。未知保持未知。父过程及时窗为首次可辨周及下一观察周，属于研究代理；迟到与遗漏不同，真实延迟和已有涨幅另外报告。

分成三本账：发现了哪些过程；发现得是否及时；提示后价格如何变化。不能拿第三本账取代第一本，也不能用第一本账保证第三本。详见[冻结E01协议](/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/34_industry_price_observation_radar/protocols/v2_revaluation01/plan.md)。

## 更新和再评价

观察版本不可覆盖，历史观测和后验标签分开。新版标签/价格必须有一致输入哈希，评价范围取已封存观察目录；范围后的新过程不能算旧观察遗漏。20/60/63/126/252日路径按固定事件ID与期限追踪成熟，成熟只指数据窗口足够。

跨标签版本按制度、行业和日期范围寻找关联，不因顺序编号相同就视为同一机会；拆分、合并、跨价格链及定义修订需明确审查。S04展示了63个窗口成熟转移，S05识别了32条由定义修订引起的增强状态变化；二者不混称方法改进。

现有脚本与命令见[版本化流程报告](/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/34_industry_price_observation_radar/reports/V2_S04_versioned_evaluation.md)。未部署、未发送报告、未新增外部行情。若继续使用现存数据重放，输出仍是历史模拟，不会自动变为前瞻验证。
