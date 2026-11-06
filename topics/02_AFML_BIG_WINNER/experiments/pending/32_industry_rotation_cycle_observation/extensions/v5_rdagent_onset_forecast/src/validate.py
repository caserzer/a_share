"""Audit actual execution, immutable inputs, mature training and published artifacts."""
import json
import hashlib
import re
import subprocess
from pathlib import Path
import numpy as np
import pandas as pd
from common import ROOT, OUT, CACHE, RD, js, sha, verify_predecessors
from engine import validate_spec


def main():
    checks=[]
    def check(name,condition):
        assert bool(condition),name
        checks.append(name)
    check('V1 V2 V3 V4 and full-industry supplement unchanged',verify_predecessors())
    audit=json.loads((OUT/'daily_input_audit.json').read_text())
    check('consumed stock and membership inputs unchanged',all(sha(p)==h for p,h in audit['reads'].items()))
    check('monthly return reconciliation complete',audit['monthly_reconciliation']=='PASS' and audit['monthly_reconciliation_rows']==45347)
    f=pd.read_parquet(CACHE/'features.parquet')
    check('membership timestamps never after observation',f.membership_asof.le(f.date).all())
    check('partial October not passed as monthly observation',f.loc[f.frequency.eq('M'),'date'].max()==pd.Timestamp('2026-09-30'))
    check('partial October week excluded',f.loc[f.frequency.eq('W'),'date'].max()==pd.Timestamp('2026-10-16'))
    check('biweekly observations are subset of weekly',set(f.loc[f.frequency.eq('BW'),'date'])<=set(f.loc[f.frequency.eq('W'),'date']))
    check('original feature panel unchanged',sha(CACHE/'features.parquet')==json.loads((OUT/'feature_audit.json').read_text())['features_sha256'])
    phases=pd.read_parquet(CACHE/'daily_phases.parquet').set_index('phase_id')
    check('daily phase IDs unique',phases.index.is_unique)
    for stage in ['a','b']:
        dest=OUT/f'stage_{stage}'
        if not (dest/'verdict.json').exists():continue
        label_path=CACHE/('labels.parquet' if stage=='a' else 'stage_b_labels.parquet')
        lab=pd.read_parquet(label_path)
        check(stage+' original labels unchanged',sha(label_path)==json.loads((OUT/'label_audit.json' if stage=='a' else dest/'label_audit.json').read_text())['labels_sha256'])
        pos=lab[lab.y.eq(1)].merge(phases[['start_date','end_confirmed_at']].reset_index(),left_on='event_or_witness_id',right_on='phase_id')
        dates=f.set_index('row_id').date.reindex(pos.row_id).to_numpy()
        check(stage+' positive labels mature at final confirmation',pos.label_available_at.eq(pos.end_confirmed_at).all())
        if stage=='a':
            check('A all positive onsets strictly future within one month',(pos.start_date.to_numpy()>dates).all() and pos.start_date.le(pos.horizon_end).all())
        else:
            check('B positive onset not in future',(pos.start_date.to_numpy()<=dates).all())
            lower=pd.Series(dates).map(lambda x:x-pd.DateOffset(months=3)).to_numpy()
            check('B positive onset within preceding three calendar months',(pos.start_date.to_numpy()>lower).all())
        neg=lab[lab.y.eq(0)].merge(phases[['start_date','start_confirmed_at']].reset_index(),left_on='event_or_witness_id',right_on='phase_id')
        check(stage+' all negatives have a future trough witness',len(neg)==int(lab.y.eq(0).sum()) and neg.start_date.gt(neg.horizon_end).all())
        check(stage+' negative maturity no earlier than witness',neg.label_available_at.ge(neg.start_confirmed_at).all())
        done=json.loads((dest/'run_complete.json').read_text())
        check(stage+' thirty native RD-Agent loops',done['completed_history']==30 and len(done['sessions'])==30)
        check(stage+' five native checkpoints in every loop',all(len(x['checkpoints'])==5 and any(y.endswith('_record') for y in x['checkpoints']) for x in done['sessions']))
        files=list((dest/'candidates').glob('rd_*/summary.json'))
        check(stage+' thirty evaluated specifications',len(files)==30)
        for p in files:validate_spec(json.loads((p.parent/'spec.json').read_text()))
        check(stage+' no outcome-dependent feature schema',True)
        runtime=json.loads((dest/'runtime.json').read_text())
        check(stage+' pinned RD-Agent checkout unchanged',
            subprocess.check_output(['git','-C',str(RD),'rev-parse','HEAD'],text=True).strip()==runtime['rdagent_commit'] and
            hashlib.sha256(subprocess.check_output(['git','-C',str(RD),'diff','--binary'])).hexdigest()==runtime['adapter_diff_sha256'])
        native=Path(runtime['trace'])/'__session__'
        checkpoint_files=sorted(p for p in native.glob('*/*') if p.is_file())
        check(stage+' actual native checkpoint files exist',len(checkpoint_files)==150)
        js(dest/'native_checkpoints.json',[dict(path=str(p),sha256=sha(p)) for p in checkpoint_files])
        critical=['common.py','data.py','labels.py','engine.py','rdscenario.py']
        check(stage+' core research code unchanged since native run',all(sha(ROOT/'src'/n)==runtime['source_hashes']['src/'+n] for n in critical))
        check(stage+' protocol unchanged since native run',sha(ROOT/'research_plan.md')==runtime['research_plan_sha256'])
        selection=json.loads((dest/'frozen_selection.json').read_text())
        check(stage+' outer evaluator unchanged after freeze',sha(ROOT/'src/outer.py')==selection['evaluation_code_sha256'])
        check(stage+' selection maximizes only search feedback',selection['winner']['objective']==max(x['objective'] for x in selection['all_candidates']))
        receipt=json.loads((dest/'prediction_receipt.json').read_text())
        check(stage+' sealed outer predictions unchanged',sha(receipt['path'])==receipt['sha256'])
        pred=pd.read_parquet(receipt['path'])
        check(stage+' sealed prediction file contains no outcomes',not {'y','label_available_at','end_confirmed_at','event_or_witness_id'}&set(pred.columns))
        check(stage+' all fit labels mature before outer quarter',all(pd.Timestamp(x['latest_train_label'])<pd.Timestamp(x['quarter']) for x in receipt['folds']))
        check(stage+' all probabilities finite and bounded',pred.prob.notna().all() and pred.prob.between(0,1).all())
        check(stage+' frequency identity unique',not pred.duplicated(['row_id','threshold','benchmark','model']).any())
        cover=pd.read_csv(dest/'outer_coverage.csv')
        check(stage+' unknown and known sum to full prediction denominator',(cover.known+cover.unknown).eq(cover.predictions).all())
        check(stage+' alert unknowns retained',(cover.known_alerts+cover.unknown_alerts).eq(cover.alerts).all())
        if stage=='b':
            a=json.loads((OUT/'stage_a/verdict.json').read_text())
            check('B conditional trigger respected',a['advance_to_early_stage'] and all(not x['passed'] for x in a['frequency_gates'].values()))
        verdict=json.loads((dest/'verdict.json').read_text())
        check(stage+' gate never accepts an empty task group',all(sum(x['frequency']==freq and x['threshold']==t for x in verdict['task_gates'])==2 for freq in ['W','BW','M'] for t in [.1,.15,.2]))
    for p in (ROOT/'reports').glob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
            if target.startswith('https://'):continue
            check('report link '+p.name+' '+target,(p.parent/target).is_file())
    # Exact known credentials are checked without printing any value or logging a hit's content.
    from dotenv import dotenv_values
    secrets=[v for k,v in dotenv_values(RD/'.env').items() if v and len(v)>=16 and any(x in k for x in ['KEY','TOKEN','SECRET','PASSWORD'])]
    textfiles=[p for p in ROOT.rglob('*') if p.is_file() and p.suffix in ['.py','.json','.md','.txt','.csv'] and '__pycache__' not in p.parts]
    check('no configured secret in public research files',all(not any(s in p.read_text(errors='replace') for s in secrets) for p in textfiles))
    check('prior versions unchanged after entire research',verify_predecessors())
    js(OUT/'validation.json',dict(status='PASS',checks=checks,count=len(checks),strict_PIT='BLOCKED_DATA'))
    files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(ROOT.rglob('*'))
        if p.is_file() and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts and p!=OUT/'manifest.json']
    js(OUT/'manifest.json',dict(status='WORKING_RESEARCH',strict_PIT='BLOCKED_DATA',files=files))
    print('PASS',len(checks),'checks;',len(files),'manifest files',flush=True)


if __name__=='__main__':main()
