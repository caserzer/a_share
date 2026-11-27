from engine import *
import json,subprocess
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while block:=f.read(1048576):h.update(block)
    return h.hexdigest()
def main():
    expected=[OUT800/'scores.parquet',OUT800/'strict_daily.parquet',OUT800/'folds.csv',OUT800/'verification.json',STORE/'wide_windows.parquet',STORE/'index800.parquet',STORE/'effective800.parquet',STORE/'effective_changes.csv',DEST/'daily_scores.parquet',PRIVATE/'industry.parquet',*LOCAL.glob('*.parquet'),LOCAL/'limits/daily.parquet',LOCAL/'suspensions/daily.parquet',HERE.parent/'config.yaml',HERE.parent/'GOAL.md']
    snap=PRIVATE/'style_caps_20261117'
    prior=pd.read_csv(OUT800/'folds.csv')
    assert (prior.latest_maturity<prior.first_signal).all()
    p=pd.read_csv(RESULT/'primary.csv').query('segment=="all"').set_index('metric')
    assert abs(p.loc['gross','bp']-p.loc['fee','bp']-p.loc['net','bp'])<1e-8
    for name in ['uniform','matched','matched_head']:
        x=pd.read_parquet(RESULT/(name+'_paths.parquet'),columns=['seed','segment','date'])
        assert set(x.seed)==set(range(1,201)) and not x.duplicated().any()
    meta=dict(git=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),quality='historical-proxy',cutoff='2026-10-12',
        input_sha256={str(f):digest(f) for f in expected},free_shares={f.name:json.loads(f.read_text())['sha256'] for f in sorted(snap.glob('*.receipt.json'))},
        sources={f.name:digest(f) for f in [*HERE.glob('*.py'),HERE/'book.cpp',HERE/'REPORT.md']},results={f.name:digest(f) for f in sorted(RESULT.iterdir()) if f.name!='verification.json'})
    (RESULT/'verification.json').write_text(json.dumps(meta,indent=2)+'\n')
if __name__=='__main__':main()
