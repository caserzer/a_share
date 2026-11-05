"""Enforce >=24 exact calendar months independently before reading outer scores.

The fit helper's elapsed-day approximation is only a provisional precheck.
Rejected provisional payloads remain immutable in their original private paths.
"""
import json
import shutil
import csv

import pandas as pd

from common import OUT, cache, config, sha, utc_now, write_json


def full_months_available(start,end,months=24):
    return pd.notna(start) and pd.notna(end) and pd.Timestamp(start)+pd.DateOffset(months=months)<=pd.Timestamp(end)


def admission_reason(receipt):
    if not full_months_available(receipt['train_start'],receipt['train_end']):return 'OUTER_LESS_THAN_24_FULL_CALENDAR_MONTHS'
    for inner in receipt['inner_timeline']:
        if not full_months_available(inner['train_min'],inner['train_max']):return 'INNER_LESS_THAN_24_FULL_CALENDAR_MONTHS'
    return None


def main():
    if (OUT/'audits/scoring_start.json').exists():raise RuntimeError('admission must precede all outer scoring')
    if (OUT/'audits/fold_admission.json').exists():raise RuntimeError('completed admission is immutable')
    archive=cache()/'pre_score_history_admission';archive.mkdir(exist_ok=True)
    summary=[];rejected_h02=set()
    for h in config()['primary']:
        if h=='H09':continue
        p=OUT/f'manifests/{h}_folds.json';current=json.loads(p.read_text())
        original=archive/p.name
        if not original.exists():shutil.copyfile(p,original)
        d=json.loads(original.read_text());before=sha(original)
        if not current.get('exact_calendar_admission') and sha(p)!=before:raise RuntimeError('unexpected partial index change')
        retained=[];rejected=[]
        for r in d['folds']:
            reason=admission_reason(r)
            if reason:
                rejection=dict(hypothesis=h,scheme=r['scheme'],fold=r['fold'],reason='BLOCKED_INSUFFICIENT_HISTORY',
                               exact_reason=reason,provisional_model_path=r['model_path'],provisional_predictions_path=r['predictions_path'],
                               provisional_model_sha256=r['model_sha256'],provisional_predictions_sha256=r['predictions_sha256'],
                               inner_timeline=r['inner_timeline'],excluded_before_any_outer_score=True)
                d['blocked'].append(rejection);rejected.append(rejection)
                if h=='H02':rejected_h02.add((r['scheme'],r['fold']))
            else:retained.append(r)
        d['folds']=retained;d['exact_calendar_admission']=True
        d['admitted_at']=current.get('admitted_at',utc_now());write_json(p,d)
        timeline_path=OUT/f'audits/{h}_fold_timeline.csv'
        if timeline_path.exists():
            source=archive/timeline_path.name
            if not source.exists():shutil.copyfile(timeline_path,source)
            with source.open(newline='') as stream:
                reader=csv.DictReader(stream);fields=reader.fieldnames;timeline=list(reader)
            accepted={(r['scheme'],r['fold']) for r in retained}
            for row in timeline:row['admission_status']='ADMITTED' if (row['scheme'],row['fold']) in accepted else 'BLOCKED_INSUFFICIENT_HISTORY'
            with timeline_path.open('w',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=fields+['admission_status']);writer.writeheader();writer.writerows(timeline)
        summary.append(dict(hypothesis=h,admitted=len(retained),rejected=rejected,original_index_sha256=before,admitted_index_sha256=sha(p)))
    p=OUT/'manifests/H02_turnover_sensitivity.json'
    if not (archive/p.name).exists():shutil.copyfile(p,archive/p.name)
    d=json.loads((archive/p.name).read_text())
    d['folds']=[r for r in d['folds'] if (r['scheme'],r['fold']) not in rejected_h02]
    d['exact_calendar_admission']=True;d['blocked_primary_folds']=[list(x) for x in sorted(rejected_h02)];write_json(p,d)
    write_json(OUT/'audits/fold_admission.json',dict(status='PASS',admitted_at=utc_now(),checks=summary,
               exact_rule='train_min + 24 calendar months <= train_max for outer and every inner window',
               original_indexes_archived=str(archive),no_outer_metrics_seen=True))


if __name__=='__main__':main()
