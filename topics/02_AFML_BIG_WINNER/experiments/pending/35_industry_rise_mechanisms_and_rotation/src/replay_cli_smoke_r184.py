"""Exercise the real CLI against frozen historical sources and prior full frames."""
import subprocess,sys
import pandas as pd
from common import *
from historical_replay import verify_replay


def run():
    out=ROOT/'outputs/r184';source=out/'frozen_sources.json';store=ROOT/'data/replay_cli_r184';cli=ROOT/'src/historical_replay.py';calls=[]
    def invoke(args,success=True):
        result=subprocess.run([sys.executable,str(cli),*args],capture_output=True,text=True)
        calls.append(dict(args=args,returncode=result.returncode,stdout=result.stdout,stderr=result.stderr))
        js(out/'cli_calls.json',calls)
        if success:
            assert result.returncode==0,result.stderr
            return json.loads(result.stdout)
        assert result.returncode!=0
        return result.stderr
    common=['--sources',str(source),'--store',str(store)]
    cap=invoke(['capture','--asof','2026-06-30',*common])['receipt']
    assert invoke(['capture','--asof','2026-06-30',*common])['receipt']==cap
    before=sha(Path(cap)/'manifest.json')
    late=invoke(['evaluate','--asof','2026-10-21','--snapshot',cap,*common])['receipt']
    latehash=sha(Path(late)/'manifest.json')
    early=invoke(['evaluate','--asof','2026-07-15','--snapshot',cap,*common])['receipt']
    assert sha(Path(cap)/'manifest.json')==before and sha(Path(late)/'manifest.json')==latehash
    assert invoke(['verify','--receipt',late])['status']=='PASS'
    assert 'required' in invoke(['capture',*common],False)
    assert 'cutoff exceeds source maximum' in invoke(['capture','--asof','2026-10-22',*common],False)
    assert 'evaluation before observation' in invoke(['evaluate','--asof','2026-06-29','--snapshot',cap,*common],False)
    corrupt=json.loads(source.read_text());corrupt['sources']['daily']['sha256']='0'*64;bad=out/'intentionally_invalid_sources.json';js(bad,corrupt)
    assert 'source hash mismatch' in invoke(['capture','--asof','2026-06-30','--sources',str(bad),'--store',str(store)],False)
    prior=json.loads((ROOT/'outputs/r181/runs.json').read_text());old=next(x for x in prior if x['asof']=='2026-06-30');_,row,_=verify_replay(cap)
    pd.testing.assert_frame_equal(pd.read_parquet(Path(row.bundle)/'observations.parquet'),pd.read_parquet(Path(old['snapshot'])/'observations.parquet'))
    prior_eval=json.loads((ROOT/'outputs/r182/runs.json').read_text())
    for receipt,date in [(late,'2026-10-21'),(early,'2026-07-15')]:
        _,row,_=verify_replay(receipt);old=next(x for x in prior_eval if x['origin']=='2026-06-30' and x['evaluation_asof']==date)
        pd.testing.assert_frame_equal(pd.read_parquet(Path(row.bundle)/'outcomes.parquet'),pd.read_parquet(Path(old['evaluation'])/'outcomes.parquet'))
    js(out/'verification.json',dict(status='PASS',cli_calls=len(calls),capture_rows=511,outcome_rows=2044,rejected_cases=4,idempotent=True,later_evaluation_preserved=True,receipts=dict(capture=cap,evaluation=late,regression=early),prospective_records=0,reads={str(p):sha(p) for p in [source,cli,Path(__file__),ROOT/'outputs/r181/runs.json',ROOT/'outputs/r182/runs.json']}))
    print('PASS real CLI',len(calls))


if __name__=='__main__':run()
