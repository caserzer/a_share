from statistics43 import *
from fund_fit import F,A,N
import json
def funds(register,write,contrasts,bp,table):
    pref='outputs/fundamental/';sm='outputs/summary/'
    x=pd.read_csv(F/'strict/issuer_status.csv');m=pd.read_csv(F/'acquisition.csv')
    docs=[json.loads(p.read_text()) for p in (F/'primary_cells').glob('*.json')]
    good=sum(i['status']=='parsed' for i in docs);cells=sum(len(i['cells']) for i in docs)
    write('F1','财报版本与日市值来源','补取2013Q1至2026Q3共55个财季的利润表、资产负债表和现金流量表，并获取逐股历史总市值。历史合格成员目录查询覆盖 '+str(len(x))+' 家，其中 '+str(x.index_status.eq('complete_index').sum())+' 家取得完整目录，其余返回403。已解析 '+str(good)+' 份原始披露，核对 '+str(cells)+' 个原件金额；二次公告索引检查更正与重述。\n\n供应商历史截面按两个公告日期的较晚者、下一交易日收盘生效；同版本冲突置缺，超过180天的报告过期。严格子集另核发布日期、公司、报告期、金额、单位和字段，市值同时要求原件股数乘未复权价格与逐日总市值一致。对可能影响历史单季、TTM或八季波动的未消解更正，保守隔离三年。可用目录和解析成功率限定了严格样本。\n\nEP35原归档只有四个财期。复核了原10家半年报的PDF指纹、已审核科目和历史取得记录，以及EP30的版本事实与索引。每个字段按历史代码×55个财季输出供应商和原件可用性。','取得局部原件，严格全池数据不足',[('按成员的来源状态',pref+'strict/issuer_status.csv'),('每个证券财期的字段缺口',pref+'F1_field_inventory.parquet'),('原值修订、新股、缺期与过期样本',pref+'F1_asof_examples.csv'),('公告更正隔离区间',pref+'strict/revision_exclusions.csv'),('原始响应时间及指纹',pref+'acquisition.csv'),('原件与历史来源交叉核对',pref+'original_crosscheck.csv')])
    ds=pd.read_csv(F/'strict/F2_coverage.csv',parse_dates=['signal_date'])
    g=pd.read_parquet(F/'F2_daily.parquet');g=g[g.date.isin(ds.signal_date)];vals=[]
    zh=['盈利收益率','账面市值比','ROE_TTM','ROE稳定性','经营现金流/净利','毛利率同比变化','六项联合']
    for a,desc in zip(A+['joint_raw'],zh):
        field='valid_'+a if a in A else a;nr='n_'+a if a in A else 'joint_neutral'
        ss=g[g.field==a];nn=g[g.field==nr];v=ds[field].sum()
        vv=(ss.groupby(ss.date.dt.year).valid.sum()/ss.groupby(ss.date.dt.year).rows.sum())*100
        vals.append([desc,int(v),100*v/ds.denom.sum(),100*ss.valid.sum()/ss.rows.sum(),100*nn.valid.sum()/nn.rows.sum(),100*(ss.valid/ss.rows).quantile(.1),vv.min(),100*ss.valid_top.sum()/ss.top.sum()])
    write('F2','六个锚的实际覆盖率','对 '+f'{int(ds.denom.sum()):,}'+' 个800历史合格股票日逐日核算。六项严格联合覆盖为零；公告日代理也未达到登记的95%联合覆盖门槛。\n\n'+table(['锚','严格有效股票日','严格覆盖%','代理原值%','代理行业中性%','代理逐日覆盖P10%','代理最差年份%','代理原头部席覆盖%'],vals)+'\n\nTTM要求四个连续单季，稳定性需要八个连续ROE_TTM，金融业缺可比营业成本时毛利率留空。以实际可分析股票日为分母，缺失填补不计覆盖。按年度、行业和逐日的分子、分母可下载。','严格及代理联合覆盖未达标',[('严格覆盖逐日',pref+'strict/F2_coverage.csv'),('严格年度行业覆盖',pref+'strict/F2_year_industry.csv'),('代理年度行业覆盖',pref+'F2_industry_year.csv'),('代理逐日覆盖和头部席数',pref+'F2_daily.parquet'),('实际目标和买入资本覆盖',pref+'F2_funded_support.csv')])
    cr=pd.read_csv(F/'F3_price_corr.csv',index_col='anchor');info=pd.read_parquet(F/'F3_information.parquet').groupby('anchor')[['raw_IC','neutral_IC','residual_IC','residual_head_excess_logH10']].mean()
    ic=[]
    for a,desc in zip(A,zh):
        c=cr.loc[a,COL].dropna().abs();r=info.loc[a];ic.append([desc,c.idxmax(),f'{c.max():.3f}',f'{cr.at[a,"R"]:.3f}',f'{r.raw_IC:.3f}',f'{r.neutral_IC:.3f}',f'{r.residual_IC:.3f}',r.residual_head_excess_logH10*10000])
    write('F3','新锚与原有78项的独立性','六个代理锚分别做行业内平均秩，再对同日78项输入和对数总市值残差化。下表将低相关性同H10排序信息量分别列出。共同市场列在同日恒定时排除，回归支持不足则残差未知。\n\n'+table(['锚','最相关原特征','最大绝对日均ρ','对R78的ρ','原值RankIC','行业中性RankIC','残差RankIC','残差头部超额对数bp/H10'],ic)+'\n\n低相关描述界值是0.30。小幅正RankIC是否覆盖真实换手成本由F4检验。严格样本在行业内不足10只，行业中性和残差的严格结果缺少观测。','代理信息量已测；严格支持不足',[('逐日原78项相关',pref+'F3_pairwise.parquet'),('年度最高相关',pref+'F3_by_year.csv'),('行业与年度、全部78项的中位数及极值',pref+'F3_sector_year_extrema.parquet'),('逐行业相关',pref+'F3_industry_corr.parquet'),('残差与H10收益',pref+'F3_information.parquet')])
    pairs=[(800,'Fstrict/neutral minus W/R','严格主臂回退R78')]+[(800,'Fproxy/'+a+' minus W/R',n) for a,n in zip(['neutral','raw','residual','missing','value','quality']+A,['代理行业中性六锚','代理全池秩六锚','代理残差','仅缺失标志','仅估值','仅质量']+zh[:6])]+[(800,'Fcommon/neutral minus Fcommon/R','共同支持同预算'),(800,'Fproxy/lock minus W/R','锁住无覆盖席位'),(800,'Fstrict_raw/raw minus W/R','原件可见原值六锚')]
    write('F4','800基本面增量账户','严格的行业中性六锚在全部季度触发R78回退，66个完整月资金路径与原账户相同。可识别的严格行业中性增量月份为0。公告日代理主臂为 '+bp(800,'Fproxy/neutral minus W/R')+' bp/月，残差臂为 '+bp(800,'Fproxy/residual minus W/R')+'。\n\n'+contrasts(pairs)+'\n\n原件可见原值另有六个单锚账户。严格行业中性单锚、缺失标志、残差和质量门控的代数等价及共同支持空集列于等价表。训练周按当时全部周候选计算横截面变换，评分日按当日实际合格池重算；训练标签成熟后再入折。','主项无可识别严格增量；代理未达标',[('严格分支和等价证明',pref+'strict/strict_equivalence.csv'),('原件可见原值打分',pref+'strict/raw_scores.parquet'),('训练与交易股票池校验',pref+'universe_audit.csv'),('目标资本的规模之外风格与估值',pref+'F4_value_style.csv'),('各基准与费用',sm+'annual.csv')])
    gc=pd.read_csv(F/'gate_changes.csv');gates=gc[gc.arm=='gate'];h=gc.pivot(index='date',columns='arm',values='replacements')
    assert (h.gate==h['hash']).all()
    write('F5','低位股质量门控与机械替换','代理主门控共改变 '+f'{int(gates.replacements.sum()):,}'+' 个目标席次，同日同行业的机械对照逐日匹配退出席位和替换数。门控相对R78为 '+bp(800,'Fgate/gate minus W/R')+' bp/月，相对机械替换为 '+bp(800,'Fgate/gate minus Fgate/hash')+'。严格质量行业秩没有满足最低覆盖的股票，实际触发0次。\n\n'+contrasts([(800,'Fgate/'+a+' minus W/R',n) for a,n in [('gate','低位×低质量'),('hash','同业同席数哈希'),('price','仅价格低位'),('pos','仅pos60定义低位'),('dd','仅dd60定义低位')]]+[(800,'Fgate/gate minus Fgate/hash','质量对机械'),(800,'Fgate/gate minus Fgate/price','质量对纯低位')])+'\n\n质量四锚至少三项可见且排名后20%才可触发；原股未知或无候补就保留。单股实际增减资本及后续两腿收益见逐票文件。','代理门控已执行，严格门控无触发',[('低位股票的可评分覆盖',pref+'F5_low_support.parquet'),('真实增减资金的H10尾部',pref+'F5_tail_cash.csv'),('每日触发与替换数',pref+'gate_changes.csv'),('真实成交与标的后续收益','outputs/accounts/800/Fgate/gate/1/capital_vs_W_R.parquet'),('年度与基准',sm+'annual.csv')])
def overview(prim,register,table):
    ss=pd.read_csv(SUM/'contrasts.csv');de=pd.read_csv(SUM/'details.csv')
    def net(k):return ss[(ss.comparison==k)&(ss['pool']==800)&(ss.segment=='all')&(ss.multiple==1)].iloc[0].net_bp
    def reduction(s):
        a=de[(de.pool==300)&(de.fee==1)&(de.segment==s)].set_index('arm').one_fee
        return 100*(1-a['B/D']/a['W/R'])
    op=pd.read_csv(F/'strict/F2_coverage.csv');c=pd.read_parquet(F/'F2_daily.parquet');c=c[c.date.isin(pd.to_datetime(op.signal_date))]
    v=c[c.field=='joint_raw'];n=c[c.field=='joint_neutral']
    names={'B2':'合分＋缓冲 − R78','L3':'校准双Ridge − 同样本总秩','W3':'集中度＋L1 − 比例缓冲','F4':'严格六锚 − 原R78'}
    rows=[]
    for t in prim.itertuples():
        y=ss[(ss.pool==t.pool)&(ss.comparison==t.comparison)&(ss.multiple==1)&(ss.segment!='all')].sort_values('segment')
        rows.append([t.item,t.pool,names[t.item],int(t.months),' / '.join(f'{x:+.2f}' for x in y.net_bp),f'{t.net_bp:+.2f}',f'[{t.lo:.2f}, {t.hi:.2f}]',f'{t.p_holm:.3f}'])
    docs='## 20项逐项结果\n\n'+'\n'.join('- '+' · '.join('['+x[0]+' '+x[1]+']('+x[4]+')' for x in register[i:i+5]) for i in range(0,20,5))
    body=f"""# EP43 执行报告

2026-11-27 完成四个方向、20个子实验的历史执行与可用数据核验。四个预登记主检验均未达到历史推进条件。300池单独采用比例排名缓冲最稳定；800池集中持仓有历史收益，但换手惩罚在相同集中度之上的独立贡献较小。

{table(['编号','主池','配对账户','完整月','逐段净差','合计 bp/月','95%区间','Holm p'],rows)}

F4的66个月是回退账户的共同月份，有严格行业中性基本面增量的月份为0。按登记将该项以p=1保留在四项Holm校正中。

## 实验改变了哪些判断

- **树合分与缓冲。** 60项浅树本身相对普通69项树在300和800分别改善17.32、19.34 bp/月。300单独加缓冲获得8.43 bp/月，缓冲上再合分为−2.44 bp/月。合体的一轮FIFO费用两段分别下降{reduction(1):.2f}%、{reduction(2):.2f}%，均低于30%；删去各段三个最好月后变为−2.35、−9.47 bp/月。冻结300迁移800为−2.22 bp/月，800本池合体为+0.62 bp/月。[四格及交互](reports/B2.md) · [逐批费用](reports/B3.md)
- **训练标签。** 300校准双Ridge前后段日内贡献为+67.82%、+29.68%，基线为+68.83%、+37.27%。隔夜贡献从−19.23%、−14.90%变为−32.81%、−19.03%。保持同一交易时点，拆腿校准同时损失日内收益并扩大隔夜亏损。树替换隔夜Ridge相对该弱基线在300修复29.19 bp/月，800修复2.60 bp/月。[分时资金归因](reports/L5.md)
- **连续权重。** 800的LP比缓冲多赚22.14 bp/月，毛差+27.64、实付费差+5.49 bp/月。相同5%上限，单独增加L1惩罚的增量为+4.20 bp/月，95%区间[−2.22, 11.23]。第一段LP落后缓冲0.64 bp/月，第三段去掉最强三月后落后36.86 bp/月。QP减少边界全卖，同池净收益落后LP 27.84 bp/月。[集中度与惩罚](reports/W3.md) · [同起点反事实](reports/W4.md)
- **基本面。** 在{int(op.denom.sum()):,}个800合格股票日上，严格六项联合覆盖为0。公告日代理的六项原值联合覆盖为{100*v.valid.sum()/v.rows.sum():.2f}%，行业中性后为{100*n.valid.sum()/n.rows.sum():.2f}%。代理六锚账户相对R78为{net('Fproxy/neutral minus W/R'):+.2f} bp/月；低位质量门控相对原账户为{net('Fgate/gate minus W/R'):+.2f}，相对同席数机械替换为{net('Fgate/gate minus Fgate/hash'):+.2f} bp/月。[来源覆盖](reports/F2.md) · [主账户](reports/F4.md) · [低位替换](reports/F5.md)

## 样本、费用与复核

300分两段，2021-01-11至2025-03-03、2025-03-03至2026-10-12；800在2023年6月缺估值处分账。各段从单位本金起算，三段末月不拼接。实际资本分成十袖，t收盘出分、t+1开盘入场、计划t+11开盘退出。买10 bp、卖20 bp，按真实可成交净订单计费。双费另开账户回放。完整月配对均值使用段内连续3个月的区块抽样，10,000次，种子4301。drop3为各段各自删掉最有利三个配对月后的均值。正的净月差与独立前瞻验证分开记录。

每池31个季度模型覆盖2019Q1至2026Q3，其中8季用于最初内折历史，23季用于外层。实际交易前的选参按回放时钟只使用已成熟历史。EP42普通69树和浅69树在407,372个外层股票日逐分复现；300 R78和800原生K、同比席数账户另按日核对。费用、现金和头寸可从每段目标权重、份额变动及十袖现金重建。完整对照含每年收益、同期指数全收益、同池等权、回撤、双倍成本，以及估值提前截止日。[基线核平](outputs/summary/baseline_parity.csv) · [年度与基准](outputs/summary/annual.csv) · [全部月差](outputs/summary/contrasts.csv)

登记文本与配置指纹先于训练保存。执行代码及新增来源在本次工作中形成，完整指纹在交付时复核。基本面排名复核中发现训练与实际评分股票池在部分周日期有差异，最终训练与评分各按当时对应的完整合格池重新算秩，并补齐了132个仅出现在2019年前训练周的历史成员，修订前账户另行保留。巨潮对1,319家成员的目录请求返回403，可取得的15家共解析881份原件；严格分支只使用完成核验的日期与字段。历史登记时间晚于回放终点，12与24个非重叠H10的独立前瞻样本尚未成熟。

{docs}

[机器执行登记册](run_register.csv) · [四个主检验](outputs/summary/primary.csv) · [核验收据](verification.json) · [本地复核说明](REPRODUCE.md)
"""
    (ROOT/'REPORT.md').write_text(body.replace('；','。'))
