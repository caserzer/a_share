from statistics43 import *
import json,re
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(2**20),b''):h.update(chunk)
    return h.hexdigest()
def seal_inputs():
    from engine import STORE
    paths=[ROOT/'config.yaml',E/'state/weighted.cpp',E/'state/core42.py',E/'state/mixture.py',E/'state/inputs42.py',E/'state/domain_features.py',E/'state/results/scores.parquet',E/'state/results/wide_scores.parquet',STORE/'index800.parquet',EP41/'p1/engine.py',EP41/'p1/book.cpp',EP41/'p1/results/daily.parquet',EP41/'p2/results/funded_daily.parquet',LOCAL/'wide_features.parquet',PRIVATE/'features.parquet',PRIVATE/'labels.parquet',PRIVATE/'industry.parquet',PRIVATE/'net_excess_20261116/H00300.CSI.json']
    for root in [PRIVATE,LOCAL]:
        for c in ['qfq_open','qfq_close','close','daily_members','volume','money','market','turnover_rate']:
            p=root/(c+'.parquet')
            if p.exists():paths.append(p)
    paths+=list(CACHE.glob('block_*.parquet'))+list((CACHE/'wide').glob('early_*.parquet'))+list((E/'events/results/features').glob('*.parquet'))
    paths+=list((E/'scale/a4/results/scores_300').glob('*.parquet'))+list((E/'scale/a4/results/scores_800').glob('*.parquet'))
    for m in [ci.prepare,ci.ridge,ci.predict]:
        import inspect
        paths.append(Path(inspect.getfile(m)))
    pd.DataFrame([(str(p),p.stat().st_size,digest(p)) for p in sorted(set(paths))],columns=['path','bytes','sha256']).to_csv(SUM/'input_hashes.csv',index=False)
def execute(seal):
    counts={};fees=[];balances=[];target_sums=[];segments=0
    for line in (O/'protocol_inputs.sha256').read_text().splitlines():
        sha,n=line.split(maxsplit=1);p=O/'protocol/README.md' if n=='README.md' else ROOT/n
        assert digest(p)==sha,(n,digest(p),sha)
    register=pd.read_csv(ROOT/'run_register.csv')
    assert set(register.id)==set(CFG['register']) and len(register)==20
    for row in register.itertuples():assert (ROOT/row.report).exists()
    assert len(list((O/'models').glob('*.parquet')))==31
    panel_names=set(pd.read_csv(O/'fundamental/events_input_names.csv').ts_code)
    train_names=set(pd.read_parquet(O/'fundamental/training_panel.parquet',columns=['instrument']).instrument)
    score_names=set(pd.read_parquet(O/'fundamental/scoring_panel.parquet',columns=['instrument']).instrument)
    assert {n[2:]+'.'+n[:2] for n in train_names|score_names}==panel_names
    strict=pd.read_csv(O/'fundamental/strict/F2_coverage.csv')
    assert strict.joint_neutral.sum()==0 and strict.denom.sum()==1076242
    max_ledger=0.;max_target_leak=0.;max_cash=0.
    days=pd.read_parquet(PRIVATE/'market.parquet',columns=[]).index
    pd.DataFrame({'entry_idx':range(len(days)),'date':days}).to_csv(SUM/'calendar.csv',index=False)
    for marker in sorted((O/'accounts').glob('*/*/*/done')):
        de=marker.parent;pool=int(de.parents[1].name);counts[pool]=counts.get(pool,0)+1
        daily=pd.read_parquet(de/'daily.parquet');details=pd.read_csv(de/'detail.csv')
        for seg in sorted(daily.segment.unique()):
            segments+=1;seg=int(seg);p=de/str(seg)
            life=pd.read_parquet(p/'fifo.parquet',columns=['buy_fee','sell_fee','shares']);assert (life.shares>=0).all()
            a=daily[(daily.segment==seg)&(daily.multiple==1)];err=abs(life.buy_fee.sum()+life.sell_fee.sum()-a.fee.sum());max_ledger=max(err,max_ledger);assert err<1e-9,(de,seg,err)
            assert (p/'exposures.parquet').exists() and (p/'session.parquet').exists()
            for fee in [1,2]:
                suffix='' if fee==1 else '_2fee'
                targets=pd.read_parquet(p/f'targets{suffix}.parquet')
                assert not targets.duplicated(['day','phase','stock']).any() and (targets.target_weight>=-1e-12).all()
                planned=targets.groupby(['day','phase']).target_weight.sum()
                max_target_leak=max(max_target_leak,max(0,planned.max()-1));assert planned.max()<=1+1e-8
                c=pd.read_parquet(p/f'cash{suffix}.parquet');v=daily[(daily.segment==seg)&(daily.multiple==fee)].set_index('date')
                assert c.index.equals(v.index);err=(c.sum(axis=1)-v.cash).abs().max();max_cash=max(max_cash,err);assert err<1e-9
                tx=pd.read_parquet(p/f'transactions{suffix}.parquet',columns=['day','fee'])
                txf=tx.groupby('day').fee.sum().reindex(days.get_indexer(v.index),fill_value=0)
                assert np.max(abs(txf.to_numpy()-v.fee.to_numpy()))<1e-9
    primary=pd.read_csv(SUM/'primary.csv');assert len(primary)==4 and primary.p_holm.between(0,1).all()
    cap=pd.read_csv(SUM/'capK_target_parity.csv');assert cap.unlocked_mismatch.sum()==0
    for pool in [300,800]:
        z=pd.read_parquet(O/f'W5_ranks_{pool}.parquet')
        assert (z.full_sales+z.partial_sales+z.retained==z.old_names).all()
        s=pd.read_parquet(O/f'W1_solver_{pool}.parquet');s=s[s.arm!='mechanical'];assert s[['kkt','bound','residual']].abs().max().max()<=1e-8
    if seal:seal_inputs()
    for p in list((ROOT/'reports').glob('*.md'))+[ROOT/'REPORT.md',ROOT/'REPRODUCE.md',ROOT/'README.md']:
        for target in re.findall(r'\]\(([^ )#]+)(?:#[^ )]*)?\)',p.read_text()):
            if '://' not in target and target!='verification.json':assert (p.parent/target).exists(),(p,target)
    if seal:
        evidence=[p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and 'revisions' not in p.parts and p.name not in ('verification.json','artifact_hashes.csv','revision_pending') and not p.name.endswith('.pyc')]
        pd.DataFrame([(str(p.relative_to(ROOT)),p.stat().st_size,digest(p)) for p in sorted(evidence)],columns=['path','bytes','sha256']).to_csv(ROOT/'artifact_hashes.csv',index=False)
    else:
        for r in pd.read_csv(SUM/'input_hashes.csv').itertuples():assert digest(Path(r.path))==r.sha256,r.path
        for r in pd.read_csv(ROOT/'artifact_hashes.csv').itertuples():assert digest(ROOT/r.path)==r.sha256,r.path
    receipt=dict(registered=20,primary_tests=4,strategies_by_pool=counts,independent_account_segments=segments,fee_multiples=[1,2],cash_reconciliation_max=max_cash,FIFO_fee_reconciliation_max=max_ledger,maximum_target_weight_budget_excess=max_target_leak,independent_forward_mature_H10=0,forward_thresholds=[12,24],source_limit='issuer directory HTTP 403; strict sector-neutral support zero',prewarm_only_issuers=len(train_names-score_names),historical_endpoint='2026-10-12',artifact_manifest_sha256=digest(ROOT/'artifact_hashes.csv'))
    if seal:(ROOT/'verification.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    else:assert json.loads((ROOT/'verification.json').read_text())['artifact_manifest_sha256']==receipt['artifact_manifest_sha256']
    print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':execute('--seal' in sys.argv)
