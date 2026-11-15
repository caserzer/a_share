from common import *
UPDATES={
'R04':([242,243,244], ' R242独立观察峰值价格过程、R243已发生/提前提示归因、R244同数量动作控制均已完成；未支持状态暂停退出。', '价格过程不同于经济反转；月度频率下未证明普遍更早识别，独立前瞻与真实退出执行仍未认证。'),
'R07':([240], ' R240在原授权内复查公开访问，仍无完整原文。', '完整69项/26组定义和双拥挤精确合成仍缺，摘要及简化评分不能替代原文复现。'),
'R08':([241], ' R241独立重建202598条当前固定评分，核对分层权重无实现偏差。', '未建立稳定独立增量；实现正确不等于有效，不重复旧惩罚或阈值搜索。'),
'R12':([], ' R245历史风险读取明确拒绝当日记录可用时钟晚于截点的条目；L1缺首发时钟仍标历史代理。', '全局严格PIT、首次发布/修订链尚未完成，局部读取时钟检查不能提升全库认证。'),
'R15':([239], ' R239可复用显式日期读取及两日期变化已完成；R245增加无未来过程输入的风险状态注释并保留全部原评分。', '历史工程读取不代表当时已部署或真实增量监控；未使用时期、首次发布数据和另行授权的生产交付仍不足。'),
'R16':([242,243,244], ' R242空目录边界失败及修复、R244事后探索及随机减少行动对照已保存，失败门控分支停止。', '持续推进其余有依据缺口；不得从停止的价格门控分支继续无依据搜索。')}
def run():
 out=ROOT/'outputs/r245';prior=json.loads((ROOT/'outputs/r238/requirements_audit.json').read_text());original=[x['id'] for x in prior['items']];prior['revision']='R245';prior['status']='active_not_complete';prior['full_completion_proven']=False
 refs=[]
 for item in prior['items']:
  if item['id'] not in UPDATES:continue
  rounds,scope,unresolved=UPDATES[item['id']];item['verified_scope']+=scope;item['unresolved']=unresolved
  old=item.get('latest_extension_evidence',[])
  for n in rounds:
   path=ROOT/f'outputs/r{n}/verification.json'
   if not path.exists() and n==240:path=ROOT/'outputs/r240/verification.json'
   assert path.exists();rec=json.loads(path.read_text());assert rec['status']=='PASS';old.append(dict(path=str(path.relative_to(ROOT)),sha256=sha(path)));refs.append(path)
  item['latest_extension_evidence']=old
  if item['id']=='R15':item['next_dependency']='independent_data_and_forward_validation'
 for item in prior['items']:
  if item['id'] in ['R12','R15']:item.setdefault('latest_extension_evidence',[]).append(dict(path='outputs/r245/independent_verification.json',sha256=sha(out/'independent_verification.json')))
 prior['next_local']=[dict(priority=1,task='Audit existing non-price operating follow-up evidence against persistence requirement before any new experiment',basis='R03/R07/R95-R96/R140-R152 already contain operating evidence; distinguish work already done from independent-period and missing-definition gaps',boundary='Existing local sources only; no new data collection, thresholds, deployment or repeated successful-case selection')]
 assert original==[x['id'] for x in prior['items']] and len(original)==16
 js(out/'requirements_audit.json',prior)
 js(out/'verification.json',dict(status='PASS',requirements=16,original_requirements_preserved=True,full_completion_proven=False,adoption=False,inputs={str(p):sha(p) for p in [ROOT/'outputs/r238/requirements_audit.json',ROOT/'protocols/r245.json',out/'independent_verification.json',ROOT/'src/risk_archive_overlay_r245.py',Path(__file__)]+refs},outputs={str(p.relative_to(out)):sha(p) for p in [out/'requirements_audit.json',out/'2026-08-31/manifest.json',out/'2026-09-30/manifest.json']}))
 print('PASS all original 16 requirements preserved; goal remains incomplete')
if __name__=='__main__':run()
