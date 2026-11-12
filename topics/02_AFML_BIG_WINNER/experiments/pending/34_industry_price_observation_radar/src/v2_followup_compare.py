"""Compare immutable followup snapshots; never rewrite observations or evaluation."""
import argparse,json,re
from pathlib import Path
import pandas as pd
import numpy as np
from audit_local_inputs import EP,sha

KEY=['arm','event_id','horizon']
FIELDS=['date','era','industry_code','status','absolute_return','max_drawdown','relative_return']

def compare(before,after):
    for f in [before,after]:
        if f.duplicated(KEY).any():raise ValueError('Non-unique event/window identity')
    m=before.merge(after,on=KEY,how='outer',suffixes=('_before','_after'),indicator=True,validate='one_to_one')
    changes=[]
    for r in m.to_dict('records'):
        fields=[k for k in FIELDS if not ((pd.isna(r.get(k+'_before')) and pd.isna(r.get(k+'_after'))) or r.get(k+'_before')==r.get(k+'_after'))]
        if r['_merge']=='right_only':kind='ADDED_EVENT_WINDOW'
        elif r['_merge']=='left_only':kind='REMOVED_EVENT_WINDOW_REVIEW'
        elif not fields:kind='UNCHANGED'
        elif any(k in fields for k in ['date','era','industry_code']):kind='EVENT_IDENTITY_REVISION_REVIEW'
        elif r['status_before']=='IMMATURE' and r['status_after']=='MATURE':kind='BECAME_MATURE'
        elif r['status_before']=='IMMATURE' and r['status_after']=='DATA_OR_CLASSIFICATION_GAP':kind='WINDOW_ENDED_WITH_GAP'
        else:kind='HISTORICAL_RESULT_REVISION_REVIEW'
        changes.append(dict(**{k:r[k] for k in KEY},change=kind,changed_fields='|'.join(fields),
                            **{k:r[k] for k in r if k.endswith('_before') or k.endswith('_after')}))
    return pd.DataFrame(changes)


def main():
    p=argparse.ArgumentParser();p.add_argument('--before',required=True);p.add_argument('--after',required=True);p.add_argument('--tag',required=True);a=p.parse_args()
    for v in [a.before,a.after,a.tag]:
        if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}',v):raise ValueError('Invalid version tag')
    roots=[EP/'outputs/followup_versions'/v for v in [a.before,a.after]];paths=[];receipts=[]
    out=EP/'outputs/followup_comparisons'/a.tag
    if out.exists():raise FileExistsError('Preserve comparison')
    for root in roots:
        rec=json.loads((root/'receipt.json').read_text());receipts.append(rec)
        for rel,digest in rec['artifacts'].items():
            if sha(root/rel)!=digest:raise ValueError('Snapshot artifact modified')
        paths += [root/'receipt.json',root/'version.json',root/'all_new_paths.parquet']
    versions=[json.loads((r/'version.json').read_text()) for r in roots]
    if versions[0]['as_of']>versions[1]['as_of']:raise ValueError('Cutoff moves backwards')
    d=compare(*[pd.read_parquet(r/'all_new_paths.parquet') for r in roots]);out.mkdir(parents=True)
    d.to_parquet(out/'all_transitions.parquet',index=False)
    d.groupby(['arm','horizon','change']).size().rename('count').to_csv(out/'transition_counts.csv')
    sameprice={k:v for k,v in receipts[0]['inputs'].items() if k.endswith('/daily_industries.parquet') or k.endswith('/CSI_ALL.parquet')}=={k:v for k,v in receipts[1]['inputs'].items() if k.endswith('/daily_industries.parquet') or k.endswith('/CSI_ALL.parquet')}
    (out/'summary.json').write_text(json.dumps(dict(before=a.before,after=a.after,same_price_source_hashes=sameprice,
        changes=d.change.value_counts().to_dict(),limits='Mature means full price window, not success. Different source vintages require revision review, even for became-mature rows. Does not compare process definitions or retrospectively establish known_at.'),indent=2)+'\n')
    paths.append(Path(__file__))
    (out/'receipt.json').write_text(json.dumps(dict(inputs={str(x):sha(x) for x in paths},artifacts={x.name:sha(x) for x in out.iterdir() if x.is_file()}),indent=2)+'\n')
    print((out/'summary.json').read_text())

if __name__=='__main__':main()
