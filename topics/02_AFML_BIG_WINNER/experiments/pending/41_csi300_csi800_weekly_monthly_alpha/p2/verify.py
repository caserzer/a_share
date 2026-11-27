"""Verify portfolio, transaction and feature sources for the narrow P2/E1/E2 accounts."""
from inputs import *
import subprocess,platform

def digest(path):
    hasher=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(2**20),b''):hasher.update(block)
    return hasher.hexdigest()

def main():
    s=pd.read_parquet(OUT/'scores.parquet')
    assert not s.duplicated(['signal_date','instrument']).any()
    f=pd.read_csv(FOLLOW/'csi800_69/results/folds.csv').query('mode=="transfer"')
    assert len(f)==23 and (pd.to_datetime(f.latest_maturity)<pd.PeriodIndex(f.fold,freq='Q').start_time).all()
    d=pd.read_parquet(OUT/'funded_daily.parquet').query('mul==1 and arm!="equal"')
    o=pd.read_parquet(OUT/'orders.parquet')
    by=['scope','arm','idx']
    fee=o.groupby(by).fee.sum().reindex(d.set_index(by).index,fill_value=0)
    np.testing.assert_allclose(fee,d.fee,atol=1e-12)
    legs=pd.read_parquet(OUT/'next_rebalance.parquet')
    support=legs[legs.arm=='tree'].merge(pd.read_parquet(OUT/'match_support.parquet'),on=['entry_idx','instrument'],validate='1:1')
    support['available_amount']=support.planned*(support.alternatives>1)
    support['forced_amount']=support.planned*(support.alternatives==1)
    support['missing_amount']=support.planned*(support.alternatives==0)
    support['one_day_share']=support.planned*(support.share_age==1)
    support.groupby('scope')[['planned','bought','available_amount','forced_amount','missing_amount','one_day_share']].sum().to_csv(OUT/'matched_capital.csv')
    paths=pd.read_parquet(OUT/'random_paths.parquet')
    assert set(paths.seed)==set(range(1,201)) and len(paths)==200*2*67
    ph=pd.read_parquet(OUT/'phase_windows.parquet')
    assert set(ph.phase)==set(range(10))
    controls=HERE.parent/'e1_e2/300'
    files=[FOLLOW/'candidate.json',FOLLOW/'results/daily_scores.parquet',FOLLOW/'results/stagger.parquet',
           FOLLOW/'csi800_69/results/folds.csv',FOLLOW/'results/market_challenge_stagger.parquet',
           *sorted((FOLLOW/'csi800_69/results/models/transfer').glob('*/*')),
           *(PRIVATE/(k+'.parquet') for k in 'qfq_close qfq_open qfq_high qfq_low open close money volume turnover_rate daily_members market industry opening_trade_status_v2 limits/daily suspensions/daily'.split()),
           PRIVATE/'net_excess_20261116/H00300.CSI.json']
    roots=[HERE,controls]
    receipt=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),python=platform.python_version(),
        score_rows=len(s),funded_trading_dates=d[['scope','idx']].drop_duplicates().shape[0],order_rows=len(o),next_seats=len(legs),
        error_fee=float(np.max(abs(fee.to_numpy()-d.fee.to_numpy()))),frozen_folds=len(f),
        source_hashes={str(p):digest(p) for p in files},
        code_hashes={str(p.relative_to(HERE.parent)):digest(p) for a in roots for p in sorted(a.glob('*.py'))},
        results={str(p.relative_to(HERE.parent)):digest(p) for a in roots for p in sorted((a/'results').iterdir()) if p.is_file() and p.name!='receipt.json'})
    (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
