# 四组消融合同与统计口径

固定2021Q4原模型含训练中位数、均值、标准差和Ridge系数。每期使用信号时点原工程特征，未来收益不参与选择。原历史输入可用时间仍未认证，故只称历史模拟。

1. 令完整分数作截面标准化、行业去均值为y，13风格同样截面标准化并行业去均值为X。
2. 对位置组和波动回撤组分别计算原系数×变换后特征的贡献，除以完整分数标准差并行业去均值，再取对X的线性投影残差p和v；rcond=1e-12。
3. NONE=y−p−v，POS=y−v，RISK=y−p，BOTH=y。四组分数共享全部其他信息；STYLE=projection(X,y)，E1为原季度更新参照。
4. 每组使用同一股票池、行业配额、ceil(n/5)只等权、同日原月初相位、下一交易日开盘执行。无阈值调整、无组合权重优化。

| feature   | formula                                                             | group   | availability                             | mechanism_group     |
|:----------|:--------------------------------------------------------------------|:--------|:-----------------------------------------|:--------------------|
| vol5      | return rolling5 std ddof0                                           | core    | signal close; retrospective source proxy | volatility_drawdown |
| amp5      | rolling5 mean(high/low-1)                                           | core    | signal close; retrospective source proxy | volatility_drawdown |
| dd5       | close/rolling5 max(close)-1                                         | core    | signal close; retrospective source proxy | volatility_drawdown |
| pos5      | (close-rolling5 min(low))/(rolling5 max(high)-rolling5 min(low))    | core    | signal close; retrospective source proxy | range_position      |
| vol20     | return rolling20 std ddof0                                          | core    | signal close; retrospective source proxy | volatility_drawdown |
| amp20     | rolling20 mean(high/low-1)                                          | core    | signal close; retrospective source proxy | volatility_drawdown |
| dd20      | close/rolling20 max(close)-1                                        | core    | signal close; retrospective source proxy | volatility_drawdown |
| pos20     | (close-rolling20 min(low))/(rolling20 max(high)-rolling20 min(low)) | core    | signal close; retrospective source proxy | range_position      |
| vol60     | return rolling60 std ddof0                                          | core    | signal close; retrospective source proxy | volatility_drawdown |
| amp60     | rolling60 mean(high/low-1)                                          | core    | signal close; retrospective source proxy | volatility_drawdown |
| dd60      | close/rolling60 max(close)-1                                        | core    | signal close; retrospective source proxy | volatility_drawdown |
| pos60     | (close-rolling60 min(low))/(rolling60 max(high)-rolling60 min(low)) | core    | signal close; retrospective source proxy | range_position      |

NONE含其余工程特征残差及全部风格投影；STYLE不含任何工程残差。STYLE依赖当日固定完整模型的分数，是压缩诊断，不是独立的收益训练模型。

主检验以日净收益为r：
- position = ((rBOTH−rRISK)+(rPOS−rNONE))/2；
- risk = ((rBOTH−rPOS)+(rRISK−rNONE))/2；
- interaction = rBOTH−rPOS−rRISK+rNONE。
- joint = rBOTH−rNONE等其余比较预先列为辅助，不能事后升级为主检验。

823日共同时间轴，65交易日循环块Bootstrap5000次、种子20261117。近似双侧p使用中心化Bootstrap分布；三个主检验Holm校正。普通95%区间为点对点描述区间。自相关、非平稳、少数年度与长期重复探索限制仍存在，校正不能消除先前研究选择偏差。

H10每个原月初信号独立现金入场、固定股票单位、10交易日后独立尝试卖出，沿用主成本与交易限制；3个月块5000次。缺失腿使整个相应配对缺失；41期中STYLE一例无法完成退出。不能将事件收益机械串为账户收益。

辅助RankIC使用173期原周信号，其中171期具有截至终点成熟的H10标签，13周日历块5000次，缺周保留。BOTH用行业去均值分数，与上一轮原始FIXED78跨行业分数的0.0306不同；两者行业内排序与本轮选股相同，不应把本轮BOTH约0.0250误读为模型变了。

股票归因：每日账本组件先用log(1+r)/r链接，BOTH减NONE，各组件之和等于两账户终值比的对数；再用终值差/对数差缩放为初始100元的财富差分配。费用和现金作为独立组件保留。逐年逐月和逐股票各自闭合；不是个股简单持有收益，也不是因果配对。

冻结记录：[输入与代码](../../outputs/diagnostics/e1_engineered_ablation_20261117/freeze.json)、[收益读取前名单封存](../../outputs/diagnostics/e1_engineered_ablation_20261117/selection_complete.json)、[账户与交易单封存](../../outputs/diagnostics/e1_engineered_ablation_20261117/accounts_complete.json)、[分析封存](../../outputs/diagnostics/e1_engineered_ablation_20261117/analysis_complete.json)。所有原模型和原报告只读复用。
