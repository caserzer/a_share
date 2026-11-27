"""Independent arithmetic and coverage checks for the EP42 revision-2 historical run."""
from pathlib import Path
from datetime import datetime,timezone
import csv
import argparse
import hashlib
import json
import re
from urllib.parse import unquote
import numpy as np
import pandas as pd
import yaml

ROOT=Path(__file__).resolve().parent
STATE=ROOT/'state/results'
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def assert_links():
    n=0
    for p in ROOT.rglob('*.md'):
        if '__pycache__' in p.parts:continue
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',p.read_text()):
            fn=unquote(target.split('#')[0])
            if not fn or '://' in fn or fn.startswith('mailto:'):continue
            path=p.parent/fn
            assert path.exists() or path.resolve() in (ROOT/'hashes.csv',ROOT/'verification.json'),(str(p.relative_to(ROOT)),fn)
            n+=1
    return n
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seal',action='store_true',help='record a new delivery manifest after all writers finish')
    seal=parser.parse_args().seal
    reg=yaml.safe_load((ROOT/'config.yaml').read_text())
    prior={k:sha(ROOT/k) for k in reg['experiment']['predecessor_file_sha256']}
    assert prior==reg['experiment']['predecessor_file_sha256']
    register=pd.read_csv(ROOT/'run_register.csv');children=pd.read_csv(ROOT/'subtrials.csv')
    assert register.id.is_unique and set(register.id)==set(reg['register']) and len(register)==23
    assert children.id.is_unique and set(children.id)==set().union(*(v.keys() for v in reg['required_subtrials'].values())) and len(children)==22
    for table in [register,children]:
        assert table.status.notna().all()
        for c in ['protocol','report','evidence']:
            assert all((ROOT/v.split('#')[0]).is_file() for v in table[c]),(c,list(table[~table[c].map(lambda v:(ROOT/v.split('#')[0]).is_file())].id))
    folds=pd.read_csv(STATE/'main/weights_quarterly.csv').set_index('q')
    history=pd.read_csv(STATE/'main/inner_objectives.csv')
    assert len(folds)==23 and set(folds.months)=={23}
    for (q,fam),g in history.groupby(['quarter','family']):
        assert pd.to_datetime(g.last_mature_date).max()<pd.Period(q).start_time
        got=g.loc[g.mean_net.idxmax(),'candidate']
        assert abs(got-float(folds.at[q,{'static':'b','Z1':'s','Z2':'z2','Z3':'z3','Z4':'z4'}[fam]]))<1e-12
    w=pd.read_parquet(STATE/'main/weights_daily.parquet').loc['2021-01-08':]
    reweight=(w.b+w.s*.175*(2*w.Z1-1).fillna(0)).clip(0,.35)
    np.testing.assert_allclose(w.dynamic,reweight,atol=1e-13,rtol=0)
    archived=pd.read_csv(STATE/'main/baseline_parity.csv')
    assert archived[['nav','cash','fee','crossed']].to_numpy().max()<1e-11
    total_rows=0;max_error=0
    for name in ['main','shallow','single_states','d6','d6_common','g7_transfer','g7_refit']:
        d=pd.read_parquet(STATE/name/'daily.parquet');total_rows+=len(d)
        for (arm,seg),g in d.groupby(['arm','segment']):
            assert g.date.is_monotonic_increasing and g.date.is_unique
            fee=(g.buy*.001+g.sell*.002)*(2 if arm.endswith('_2fee') else 1)
            err=max((g.nav-g.nav.shift().fillna(1)-g.gross_pnl+g.fee).abs().max(),(g.fee-fee).abs().max())
            assert err<1e-10,(name,arm,seg,err)
            assert g.cash.min()>-1e-9
            max_error=max(max_error,err)
    mo=pd.read_csv(STATE/'main/monthly.csv').pivot(index=['segment','month'],columns='arm',values='net')
    delta=1e4*(mo.dynamic-mo.static)
    assert list(delta.groupby(level=0).size())==[49,18]
    stats=pd.read_csv(STATE/'main/comparisons.csv').query('arm=="dynamic" and base=="static"').set_index('segment')
    for seg,g in delta.groupby(level=0):assert abs(g.mean()-stats.at[str(seg),'net_bp'])<1e-9
    rng=np.random.default_rng(4201);pieces=[]
    for _,g in delta.groupby(level=0):
        a=g.to_numpy();n=len(a);draw=rng.integers(0,n-2,(10000,(n+2)//3));idx=(draw[:,:,None]+np.arange(3)).reshape(10000,-1)[:,:n]
        pieces.append(a[idx].sum(axis=1))
    ci=np.percentile(sum(pieces)/len(delta),[2.5,97.5]);np.testing.assert_allclose(ci,stats.loc['all',['lo','hi']].to_numpy(float),atol=1e-10)
    a1=pd.read_csv(ROOT/'attribution/results/a1_checks.csv')
    assert a1[['max_daily_gross_error','stock_gross_error','stock_fee_error']].to_numpy().max()<1e-10
    a5=pd.read_csv(ROOT/'trades/a5/fee_reconciliation.csv')
    assert len(a5)==50 and a5.max_parity.max()<1e-10 and a5.fifo_resid.max()<1e-9
    a4=json.loads((ROOT/'scale/a4/results/verification.json').read_text())
    assert a4['max_daily_pnl_error']<1e-10
    event_errors=[];event_arms=0
    for name in ['fusion','same_coverage','events_h10','events_h20','etf','supply']:
        df=pd.read_csv(ROOT/'events/results'/name/'verification.csv')
        event_errors.extend(df[['fee_error','identity_error']].max().tolist())
        event_arms+=df.arm.nunique()
    assert max(event_errors)<1e-9
    d6=pd.read_csv(STATE/'d6/baseline_parity.csv')
    assert d6.max_daily_account_error.max()<1e-10
    links=assert_links()
    exclude={'hashes.csv','verification.json'}
    files=[p for p in sorted(ROOT.rglob('*')) if p.is_file() and not any(n.startswith('.') or n=='__pycache__' for n in p.relative_to(ROOT).parts) and p.relative_to(ROOT).as_posix() not in exclude and p.suffix not in {'.pyc','.so'}]
    manifest=ROOT/'hashes.csv'
    if seal:
        with manifest.open('w',newline='') as f:
            writer=csv.writer(f);writer.writerow(['relative_path','bytes','sha256'])
            for p in files:writer.writerow([p.relative_to(ROOT).as_posix(),p.stat().st_size,sha(p)])
    else:
        saved=json.loads((ROOT/'verification.json').read_text())
        assert sha(manifest)==saved['sha256_manifest'],'delivery manifest digest changed'
        with manifest.open(newline='') as f:
            expected={r['relative_path']:(int(r['bytes']),r['sha256']) for r in csv.DictReader(f)}
        actual={p.relative_to(ROOT).as_posix() for p in files}
        assert actual==set(expected),('inventory changed',sorted(set(expected)^actual))
        for p in files:
            name=p.relative_to(ROOT).as_posix()
            assert (p.stat().st_size,sha(p))==expected[name],('file changed',name)
    out=dict(run='EP42-20261127-R1',protocol_revision=2,verified_at_utc=datetime.now(timezone.utc).isoformat(),scope='historical',last_valuation='2026-10-12',
             forward_live_pre_entry_predictions_in_this_run=0,forward_mature_nonoverlapping_h10=0,items=len(register),required_children=len(children),children_by_parent=children.groupby('parent').size().to_dict(),
             unchanged_registered_predecessor_hashes=prior,checked_local_links=links,fingerprinted_files=len(files),sha256_manifest=sha(ROOT/'hashes.csv'),
             outer_quarters=len(folds),inner_candidate_quarters=len(history),state_account_daily_rows=total_rows,max_state_daily_account_residual=max_error,
             d5_months=len(delta),d5_net_bp=float(delta.mean()),d5_95ci_bp=list(ci),d5_nonzero_slope_quarters=int((folds.s!=0).sum()),
             a1_daily_books=len(a1),a4_audited_stock_sleeve_rows=a4['stock_sleeve_rows_audited'],a5_books=len(a5),a5_account_days=int(a5.trading_dates.sum()),
             event_accounts_across_six_books=event_arms,max_event_cash_fee_error=max(event_errors))
    if seal:
        (ROOT/'verification.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    assert (ROOT/'hashes.csv').stat().st_size and (ROOT/'verification.json').stat().st_size
    print(json.dumps(out,ensure_ascii=False))
if __name__=='__main__':main()

