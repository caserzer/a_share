"""Check the registered inventory, actual-account bridges and local artifact hashes."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import platform
import sys
import pandas as pd
import numpy as np
import yaml

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[4]
PENDING=ROOT.parent
COMMIT='7b526fb9f0df784d9e04d5e831728b8f04dbd2c7'
SKIP_PARTS={'__pycache__','five_minute_parts','cache'}

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as src:
        for piece in iter(lambda:src.read(1024*1024),b''):h.update(piece)
    return h.hexdigest()

def inputs():
    ep36=next(PENDING.glob('36_*'))/'private'
    follow=next(PENDING.glob('40_*'))/'lightgbm/followup'
    cache=Path.home()/'.cache/a_share/ep32'
    return [*(ep36/(f+'.parquet') for f in 'features labels qfq_open qfq_high qfq_low qfq_close volume money turnover_rate market daily_members industry'.split()),
        cache/'regime_v26/predictions/W_0.1_CSI_ALL.parquet',cache/'extension_v2/sources/legacy_members.parquet',cache/'industry_v1/members.parquet',
        next(PENDING.glob('32_*/extensions/v28*/outputs/historical_alerts.csv.gz')),
        follow/'results/daily_scores.parquet',follow/'results/verification.json',follow/'results/market_challenge_stagger.parquet',follow/'results/stagger.parquet',
        follow/'csi800_69/results/scores.parquet',follow/'csi800_69/results/verification.json',follow/'candidate.json']

def files():
    return sorted(p for p in ROOT.rglob('*') if p.is_file() and p!=ROOT/'verification.json' and not SKIP_PARTS.intersection(p.parts) and p.suffix not in ['.pyc','.so','.log','.tmp'])

def check(sealing=False):
    r=pd.read_csv(ROOT/'run_register.csv')
    cfg=yaml.safe_load((ROOT/'config.yaml').read_text())
    assert r.id.is_unique and set(cfg['directions'])==set(r.id) and len(r)==19
    for file in set(r.report) | set(r.primary_evidence):assert (ROOT/file).is_file(),file
    for f in ROOT.rglob('*.md'):
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',f.read_text()):
            path=target.split('#')[0]
            if path and '://' not in path:
                dest=(f.parent/path).resolve()
                if sealing and dest==ROOT/'verification.json':continue
                assert dest.exists(),(f,target)
    t=pd.read_csv(ROOT/'primary_inference.csv').query("segment=='all'").set_index('test')
    assert t.loc['P1','months']==66 and t.loc['P2','months']==67
    assert np.allclose(t.loc[['P1','P2'],'estimate'],[35.47321179,-1.18851129],atol=1e-8)
    parity=pd.read_csv(ROOT/'primary_book_parity.csv')
    assert len(parity)==10 and parity.max_state_error.max()<1e-10 and parity.max_fee_error.max()<1e-12
    d=pd.read_parquet(ROOT/'models/results/funded_daily.parquet')
    assert not d.duplicated(['arm','hold','segment','date']).any()
    for _,g in d.groupby(['arm','hold','segment'],sort=False):
        delta=g.nav-g.nav.shift(fill_value=1)
        np.testing.assert_allclose(delta,g.gross_pnl-g.fee,atol=1e-12)
        np.testing.assert_allclose(g.fee,.001*g.buy+.002*g.sell,atol=1e-12)
        assert g.cash.min()>-1e-9
    gates=pd.read_csv(ROOT/'models/results/veto_gates.csv')
    w=gates.pivot(index='quarter',columns='model',values=['auc','brier','ece'])
    v=(w.auc['tail']>=.55)&(w.auc['tail']>w.auc.inc)&(w.brier['tail']<w.brier.inc)&(w.brier['tail']<w.brier.history)&(w.ece['tail']<w.ece.inc)
    passed=set(w.index[v]);assert passed==set(gates[gates.challenger_pass].quarter)=={'2022Q3','2022Q4','2023Q2'}
    for n in [2,3]:
        independent=pd.read_parquet(ROOT/'models/results/veto_impact_daily.parquet').query('count==@n and arm!="R"')
        a=d[d.arm.eq(f'V_risk_{n}')].merge(independent.rename(columns={'scope':'segment'}),on=['segment','date'],validate='1:1')
        assert len(a)==1392
        for field in ['nav','fee']:np.testing.assert_allclose(a[field+'_x'],a[field+'_y'],atol=1e-12,rtol=0)
    m=pd.read_csv(ROOT/'models/results/complete_months.csv')
    rand=pd.read_parquet(ROOT/'models/results/veto_random_months.parquet')
    for n in [2,3]:
        a=rand.query('count==@n and seed==1').merge(m[m.arm==f'V_random_{n}'],on=['segment','month'],validate='1:1')
        assert len(a)==67
        np.testing.assert_allclose(a.net_x,a.net_y,rtol=0,atol=1e-12)
    return dict(registered_ids=len(r),primary_months={'P1':66,'P2':67},model_arms=d.arm.nunique(),model_account_days=len(d),veto_enabled=sorted(passed))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--seal',action='store_true');args=parser.parse_args()
    metrics=check(sealing=args.seal)
    receipt=ROOT/'verification.json'
    if args.seal:
        import scipy,lightgbm
        data=dict(run='EP41-20261127-R1',baseline_commit=COMMIT,head_at_run=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            frozen_config_unmodified=subprocess.check_output(['git','show',COMMIT+':'+str((ROOT/'config.yaml').relative_to(REPO))],cwd=ROOT)==(ROOT/'config.yaml').read_bytes(),
            scope='historical proxy; independent forward H10 pending',environment={'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'scipy':scipy.__version__,'lightgbm':lightgbm.__version__},
            checks=metrics,inputs={str(p):digest(p) for p in inputs()},files={str(p.relative_to(ROOT)):digest(p) for p in files()})
        assert data['frozen_config_unmodified']
        receipt.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
    else:
        data=json.loads(receipt.read_text());assert data['checks']==metrics
        assert set(data['files'])=={str(p.relative_to(ROOT)) for p in files()}
        for root,section in [(ROOT,'files'),(Path('/'),'inputs')]:
            for f,want in data[section].items():assert digest(root/f)==want,f
    print(metrics)
if __name__=='__main__':main()
