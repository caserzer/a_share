"""Seal the current bounded research deliverables, not prospective success."""
from pathlib import Path
import json
import re
import sys
import hashlib
import subprocess
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];EXT=ROOT.parent;EP=EXT.parent;OUT=ROOT/'outputs'
sys.path.insert(0,str(EXT/'v31_all_signal_economics/src'))
from common31 import sha,js,md


def run():
    checks=[]
    def ck(name,value):
        assert bool(value),name
        checks.append(name)
    tests=subprocess.run([sys.executable,'-m','pytest','-q',str(ROOT/'tests')],capture_output=True,text=True)
    ck('forward evidence admission adversarial tests',tests.returncode==0)
    js(OUT/'test_receipt.json',dict(command=[sys.executable,'-m','pytest','-q',str(ROOT/'tests')],
        exit_code=tests.returncode,stdout=tests.stdout,stderr=tests.stderr))
    pred=json.loads((EXT/'v31_all_signal_economics/outputs/predecessors.json').read_text())
    ck('all V1-V30 manifest-covered artifacts preserved',all(sha(p)==h for p,h in pred.items()))
    sealed=[]
    for name in ['v31_all_signal_economics','v32_mechanism_rotation']:
        root=EXT/name;m=json.loads((root/'outputs/manifest.json').read_text())
        ck(name+' output hashes',all(sha(root/f['path'])==f['sha256'] for f in m['files']))
        sealed.append(dict(version=name,manifest_sha256=sha(root/'outputs/manifest.json'),files=m['file_count']))
    contract=json.loads((OUT/'forward_contract.json').read_text())
    identity=hashlib.sha256(json.dumps({k:v for k,v in contract.items() if k!='identity_sha256'},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    ck('forward contract hash',identity==contract['identity_sha256'])
    ck('frozen forward source unchanged',all(sha(p)==h for p,h in contract['code_hashes'].items()))
    financial=json.loads((OUT/'financial_audit.json').read_text())
    ck('financial original evidence unchanged',all(sha(p)==h for p,h in financial['evidence_hashes'].items()))
    readiness=json.loads((OUT/'forward_readiness.json').read_text())
    ck('no fabricated forward prediction',readiness['new_forward_predictions_created']==0 and readiness['status']=='BLOCKED_DATA')
    metric=pd.read_csv(EXT/'v31_all_signal_economics/outputs/primary_metrics.csv').query("method=='accepted' and unit=='six_month_launches' and months==6")
    table=metric[['frequency','signals','known_returns','mean_return','median_return','mean_excess','median_excess','mean_max_drawdown']].copy()
    for c in ['mean_return','median_return','mean_excess','median_excess','mean_max_drawdown']:table[c]=table[c].map(lambda x:f'{x:.2%}')
    overview='''# EP32 后续实验交付：经济价值、机制与前瞻准备

2026-11-08，Asia/Shanghai。用户授权的固定实验方案已执行，完成历史经济评价、机制负对照、领先更替检验、基本面/实时输入审计和前瞻记录准备。**没有宣称前瞻有效性已经完成，也没有因为数据不足补造基本面实验。** 原V1—V30保持不变；V28的历史分类目标验收继续保留。

## 主要发现

三级行业、15%转折、中证全指为主口径，周/双周/月分别报告。同一行业6月观察段只用首次信号；次交易日收盘起算，纳入误报及周期未知但收益可计算的记录。下表为6月结果：

'''+md(table)+'''
平均超额为5.63—8.09个百分点，但相对同日同K动量对照的成对改善区间均跨零；同日行业等权等简单对照在部分口径下更高。分类precision提高没有自动转化为复杂模型收益增量。

2023年的行业绝对收益为负但仍跑赢市场，说明“正超额”不等于盈利。2021行业分类断点造成部分收益无法连续测量，12月观察尤其明显。所有缺失保留，不补零。

同容量扩散与无扩散模型比较未得到跨频率稳健收益增量。真实扩散相对一次行业对应关系打乱在周/双周有线索，不能证明龙头先行的经济因果。领先行业6月留存约18.5%—18.9%，不高于本次置换对照；新领先者识别优于动量，但与日期内置换相比并非一致胜出。可预测行业轮动尚未确立。

基本面已核验数据仅2个发行人、15条事实、3个版本，无法形成代表性行业面板。已有价格截至2026-10-21，距审计日18个自然日；未生成11月伪前瞻信号。前瞻规范与追加记录器已建立，真实前瞻仍FORWARD_PENDING，严格PIT仍BLOCKED_DATA。

## 交付入口

- [V31 全部信号收益、去重周期及简单对照](extensions/v31_all_signal_economics/reports/all_signal_economics.md)
- [V32 机制消融、打乱负对照与行业领先更替](extensions/v32_mechanism_rotation/reports/mechanism_rotation.md)
- [V33 基本面PIT与前瞻准入审计](extensions/v33_pit_forward_readiness/reports/readiness.md)
- [本轮事前固定方案](extensions/v31_all_signal_economics/research_plan.md)

## 复算与运行顺序

使用topics/02_AFML_BIG_WINNER/.venv/bin/python，保留虚拟环境路径，不解析为系统解释器。需要本机私有冻结数据，Git中的摘要不能替代完整价格和预测。依次运行V31的build31.py、evaluate31.py、validate31.py、report31.py；V32的negative_control.py、evaluate32.py、report32.py；V33的audit33.py与deliver33.py。已有研究封存后再次运行会产生新冻结时间，应在新目录复制工作，不覆盖已交付清单。

V31独立核对180条原始路径，并核对36项原分类任务、未知标签和因果启动规则。V32精确复现原扩散模型2021Q1预测后完成固定负对照重训。V33追加准入的4项测试覆盖过期数据、未来/未成熟信息、篡改和禁止覆盖。两次实现失败均保留，未据此改变实验配置。

本轮没有继续优化阈值，没有实际下单、部署调度或发送外部消息。下一阶段的决定应基于上述经济价值对照与数据补齐，而非再次优化历史precision。
'''
    (EP/'FOLLOWUP.md').write_text(overview)
    for root in [EXT/'v31_all_signal_economics',EXT/'v32_mechanism_rotation',ROOT]:
        for p in root.rglob('*.md'):
            for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
                if '://' not in target and not target.startswith('#'):
                    ck('link '+str(p.relative_to(EP))+' '+target,(p.parent/target).exists())
    for target in re.findall(r'\]\(([^)]+)\)',overview):ck('overview link '+target,(EP/target).exists())
    js(OUT/'completion.json',dict(status='BOUNDED_RESEARCH_PLAN_EXECUTED',completed=['fixed-scope counting and all-signal economics',
        'fixed economic ablations and diffusion negative control','leadership transition tests',
        'fundamental and current-input audit','frozen prospective contract and append-only admission'],
        not_completed_due_to_evidence=['representative PIT fundamental mechanism estimates','new admitted prospective prediction stream','mature prospective performance'],
        strict_PIT='BLOCKED_DATA',independent_forward_validation='FORWARD_PENDING',production_deployed=False,
        historical_overfitting_boundary_preserved=True,overview_sha256=sha(EP/'FOLLOWUP.md'),upstream=sealed))
    js(OUT/'validation.json',dict(status='PASS',checks_count=len(checks),checks=checks))
    files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(ROOT.rglob('*'))
        if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts]
    js(OUT/'manifest.json',dict(files=files,file_count=len(files)))
    print('PASS',len(checks),'delivery checks');print(tests.stdout)


if __name__=='__main__':run()
