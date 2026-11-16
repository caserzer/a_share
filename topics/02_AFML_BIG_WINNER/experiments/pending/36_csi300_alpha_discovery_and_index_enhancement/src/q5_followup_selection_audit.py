"""Check actual targets against frozen ranks and opening legacy holdings."""
import json
import numpy as np
import pandas as pd
from common import EP,PRIVATE,sha,save_json
from evaluate_ranking import predictions
from q5_followup import DEST,specs

def main():
    p,_=predictions('expanding');p=p.loc[p.model_id.isin(['E1','E2','E3'])&p.seed_or_ensemble.isin(['fixed','equal_seed_ensemble'])]
    lookup={(m,pd.Timestamp(d)):g.set_index('instrument').score for (m,d),g in p.groupby(['model_id','signal_date'])}
    members=pd.read_parquet(PRIVATE/'daily_members.parquet')
    schedule=pd.read_csv(DEST/'schedule.csv',parse_dates=['signal_date','execution_date'])
    count=0
    for spec in specs():
        r=json.loads((DEST/'accounts'/(spec['account']+'.json')).read_text());z=pd.read_parquet(r['orders_path'])
        sm=schedule.loc[schedule.frequency.eq(spec['frequency'])&schedule.phase.eq(spec['phase'])].set_index('execution_date').signal_date
        for date,g in z.groupby('date'):
            signal=sm.loc[date];member=members.loc[signal];member_set=set(member.index[member])
            actual=set(g.loc[g.target_weight>0,'instrument'])
            if spec['model']=='EW':expected=member_set
            else:
                scores=lookup[(spec['model'],signal)].dropna();scores=scores.loc[scores.index.isin(member_set)].rename('score').reset_index().sort_values(['score','instrument'])
                n=len(scores);base=scores.loc[np.floor(5*np.arange(n)/max(1,n)).astype(int)==4,'instrument'];k=len(base)
                if spec['buffer'] is None:expected=set(base)
                else:
                    ranked=scores.instrument.tolist()[::-1];old=set(g.loc[g.units_before>0,'instrument'])
                    kept=[s for s in ranked[:int(np.floor(n*spec['buffer']))] if s in old][:k]
                    expected=set(kept+[s for s in ranked if s not in kept][:k-len(kept)])
            assert actual==expected,(spec['account'],date,actual^expected)
            count+=1
    # Ensure execution copy has no unrelated behavioural edits.
    original=(EP/'src/backtest.py').read_text();original=original[original.index('def run_account('):original.index('\ndef main(scheme,scenario):')]
    changed=(EP/'src/q5_followup_engine.py').read_text();changed=changed[changed.index('def run_account('):].rstrip()
    original=original.replace('def run_account(inp,scores,path,cost,scenario,model,scheme):','def run_account(inp,scores,path,cost,scenario,model,scheme,buffer=None):')
    original=original.replace('ix=np.where(ok)[0];ix=ix[np.lexsort((inp.symbols[ix],score[ix]))];selected=ix[np.floor(5*np.arange(len(ix))/max(1,len(ix))).astype(int)==4]','selected=select_target(score,member,units>0,inp.symbols,buffer)')
    assert original.rstrip()==changed
    save_json(DEST/'selection_validation.json',dict(status='PASS',rebalance_targets_checked=count,accounts=126,execution_copy_only_changes='A stock selection and optional buffer argument',industry_snapshot_sha256=sha(PRIVATE/'industry.parquet')))
    print('PASS independent selection checks',count)

if __name__=='__main__':main()
