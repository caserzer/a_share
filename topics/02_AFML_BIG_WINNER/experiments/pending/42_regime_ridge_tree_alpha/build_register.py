"""Join the immutable v2 protocol to the execution evidence; preserve zero-trigger rows."""
from pathlib import Path
import csv
import yaml

ROOT=Path(__file__).resolve().parent
CFG=yaml.safe_load((ROOT/'config.yaml').read_text())
TRADE='trades/REPORT.md'
STATE='state/REPORT.md'
SCALE='scale/REPORT.md'
EVENT='events/REPORT.md'
C='trades/results/contrasts.csv'
SC='scale/results/comparisons.csv'
EC='events/results/'
PRIMARY={
'A1':('归因已核平','attribution/REPORT.md','attribution/results/a1_concentration.csv','66月原账头部减候补+35.47，三段各删三月后−14.60 bp/月。'),
'A2':('归因已核平',TRADE,C,'同买单下树选卖方较顺位+1.78/+4.03 bp/月，区间跨零。'),
'A3':('归因已核平','trades/a3/REPORT.md','trades/a3/phase_comparison.csv','十相位按资金加权共同起点−0.11/−0.03 bp/H10。'),
'A4':('归因已核平','scale/a4/REPORT.md','scale/a4/results/verification.json','两池五段均以真实持仓加回日内、隔夜和实付费用。'),
'A5':('归因已核平','trades/a5/REPORT.md','trades/a5/fee_reconciliation.csv','50本连续账逐日核对；800后段Ridge少付37.19、毛利少110.55 bp/月。'),
'D1':('历史回放完成',TRADE,C,'2席树低分剔除减Ridge边界−0.05/+7.42 bp/月。'),
'D2':('历史回放完成',TRADE,C,'K/40纯排名缓冲较无缓冲+8.12/+6.29；加价格路径+0.14/−1.93 bp/月。'),
'D3':('历史回放完成，触发稀少',TRADE,'trades/results/dual_gate.csv','23季中仅3季同时通过质量门，后段无触发。'),
'D4':('历史回放及来源审计完成，部分条件数据不足',EVENT,'subtrials.csv','11项均有结果或来源边界，分列同覆盖与同金额对照。'),
'D5':('主检验完成，未通过',STATE,'state/results/main/comparisons.csv','动态减季度静态−1.77/0.00，67月合计−1.29 bp/月。'),
'D6':('历史回放完成','state/D6.md','state/results/d6/comparisons.csv','同域预算下丙减乙−6.57/−17.82/−8.80 bp/月。'),
'S1':('机制审计完成',SCALE,'scale/results/S1_structure.csv','固定构成及实际合格股均核查树分支穿越。'),
'S2':('历史回放完成',SCALE,SC,'原值减同秩固定分布+41.05/+28.34 bp/月，汇总区间跨零。'),
'S3':('历史回放完成',SCALE,'scale/results/S3_four_cells.csv','三列恢复真实截面水平和离散度+1.80/−2.24 bp/月。'),
'S4':('历史回放完成',SCALE,'scale/results/S4_placebo_spread.csv','正确日期减错后20日+5.11/+7.17 bp/月。'),
'S5':('历史回放完成，固定构成状态覆盖不足',SCALE,'scale/results/S5_coverage.csv','严格配对276/2871个分歧席位，固定构成Z1无满252日校准窗。'),
'G1':('历史回放完成',STATE,'state/results/main/g1_high_low.csv','高减低档下树相对Ridge的H10净差−20.63/−27.66 bp。'),
'G2':('历史回放完成',SCALE,'scale/results/state_spreads.csv','同输入同平方损失高低档净差之差−18.78/+13.52 bp/H10。'),
'G3':('历史回放完成',SCALE,'scale/results/G3_coefficients.csv','线性状态交互减相同主效应+1.61/−0.48 bp/月。'),
'G4':('历史回放完成',STATE,'state/results/main/g4_double_difference.csv','合分状态增量减预算状态增量−1.01/0.00 bp/月。'),
'G5':('历史回放完成',STATE,'state/results/main/g5_all_state_pairs.csv','成交、趋势及回撤均已对Z1做增量及单因素对照。'),
'G6':('历史回放完成',STATE,'state/results/main/g6_transitions.csv','滞后20日减当日+0.82/0.00 bp/月。'),
'G7':('历史回放完成，纯树有局部估值缺口',STATE,'state/results/g7_matched_calendar.csv','迁移与重训股票模型的外域动态增量分别−1.94/+1.00 bp/月。')}
CHILDREN={
'D1.1':(C,'历史回放完成','1、2、3席及每规格200种随机剔除。'),
'D1.2':(C,'历史回放完成','窄宽候补池与30%保护线交叉四格。'),
'D1.3':(C,'历史回放完成','联合浅层早停减原树+0.60/−4.83 bp/月。'),
'D1.4':('trades/results/member_notice_audit.csv','历史回放及公告覆盖审计完成','180日安全垫和公告单独回放，188次退出中116次与公告生效日对齐。'),
'D1.5':(C,'历史回放完成','窄池联合减仅剔除2席−1.03/−1.80 bp/月。'),
'D2.1':(C,'历史回放完成','24/40、24/45、K/40及简单排名对照。'),
'D2.2':('trades/results/buffer_path_summary.csv','历史回放完成','过去H10超额超过8个百分点提早释放对纯缓冲。'),
'D2.3':('trades/results/random_summary.csv','历史回放完成','200条等席、金额可比及实际换手接近月的随机对照。'),
'D3.1':('trades/results/dual_gate.csv','概率审计完成','左右尾模型逐季比较，两门共同通过3/23季。'),
'D3.2':(C,'历史回放完成，后段未触发','最多2席联合否决前段20日改32席。'),
'D3.3':(C,'历史回放完成，后段未触发','前段5日改5席。'),
'D4.1':(EC+'same_coverage/comparisons.csv','历史代理账户完成','全池EPS20相对Ridge−0.34，同覆盖−0.27 bp/月。'),
'D4.2':(EC+'fusion/comparisons.csv','历史代理账户完成','全池目标价正交−0.05；同覆盖−0.03 bp/月。'),
'D4.3':(EC+'same_coverage/comparisons.csv','历史代理账户完成','覆盖机构数变化同覆盖增量+0.47 bp/月。'),
'D4.4':(EC+'fusion/folds.csv','历史代理账户完成，主规格未触发','9,919个有值股票日，季度SUE主规格未改仓。'),
'D4.5':(EC+'fusion/comparisons.csv','历史代理账户完成，双源交集未改仓','两源等权较单EPS零增量。'),
'D4.6':(EC+'events_h10/comparisons.csv','历史代理账户及来源审计完成，部分财季缺事前预期','正式、预告及快报分开，Q1至Q3同财期可比预期覆盖另列。'),
'D4.7':(EC+'events_h10/comparisons.csv','历史代理账户完成，部分财季缺事前预期','营收与扣非加速度分别对当日匹配及简单增速。'),
'D4.8':(EC+'events_h20/comparisons.csv','历史代理账户完成','大幅对温和上修H10/H20分别−1.06/+7.44 bp/月。'),
'D4.9':(EC+'etf/comparisons.csv','历史代理账户完成','原两只300ETF的顺流、逆流、同覆盖及现金替代对照。'),
'D4.10':(EC+'etf/comparisons.csv','历史代理账户及篮子覆盖审计完成','八只基金顺流/逆流对Ridge为−40.52/−30.30 bp/月，相同300席上的扩池顺流增量−0.83。'),
'D4.11':(EC+'supply/comparisons.csv','历史代理账户完成，具名关系有限','保留原4条并核5条新增合同，供方和采购方分别比较。')}
def write(name,records):
    with (ROOT/name).open('w',newline='') as f:
        wt=csv.DictWriter(f,fieldnames=list(records[0]));wt.writeheader();wt.writerows(records)
def main():
    rows=[]
    assert set(PRIMARY)==set(CFG['register'])
    for k,v in CFG['register'].items():
        status,report,evidence,result=PRIMARY[k]
        rows.append(dict(id=k,role=v['role'],protocol=v['spec'],status=status,finding=result,report=report,evidence=evidence))
    write('run_register.csv',rows)
    rows=[]
    for parent,group in CFG['required_subtrials'].items():
        for k,v in group.items():
            evidence,status,result=CHILDREN[k]
            rows.append(dict(id=k,parent=parent,name=v['name'],protocol=v['spec'],status=status,finding=result,report=EVENT if parent=='D4' else TRADE,evidence=evidence))
    assert len(rows)==len(CHILDREN)==22
    write('subtrials.csv',rows)
if __name__=='__main__':main()

