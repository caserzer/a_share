"""Candidate process lineage only: never transfers coverage across versions."""
import argparse,json,re
from pathlib import Path
import pandas as pd
from audit_local_inputs import EP,sha


def compare(old,new,identity):
    for df in [old,new]:
        if df[identity].duplicated().any():raise ValueError('Duplicate native process id')
        if (df.start_date>df.end_date).any():raise ValueError('Reversed interval')
    edges=[];olddegree={x:0 for x in old[identity]};newdegree={x:0 for x in new[identity]}
    groups={k:g for k,g in new.groupby(['era','industry_code'])}
    for a in old.to_dict('records'):
        for b in groups.get((a['era'],a['industry_code']),new.iloc[:0]).to_dict('records'):
            lo=max(a['start_date'],b['start_date']);hi=min(a['end_date'],b['end_date'])
            exact=a['start_date']==b['start_date'] and a['end_date']==b['end_date']
            if lo>hi:continue
            sameblock=a['block']==b['block']
            link='SAME_BLOCK_OVERLAP' if sameblock and (lo<hi or exact) else 'BOUNDARY_TOUCH_REVIEW' if sameblock else 'CROSS_BLOCK_OVERLAP_REVIEW'
            if link=='SAME_BLOCK_OVERLAP':olddegree[a[identity]]+=1;newdegree[b[identity]]+=1
            edges.append(dict(old_id=a[identity],new_id=b[identity],era=a['era'],industry_code=a['industry_code'],
                old_block=a['block'],new_block=b['block'],old_start=a['start_date'],new_start=b['start_date'],
                old_end=a['end_date'],new_end=b['end_date'],old_status=a['status'],new_status=b['status'],link=link))
    records=[]
    for e in edges:
        od=olddegree[e['old_id']];nd=newdegree[e['new_id']]
        if e['link']!='SAME_BLOCK_OVERLAP':kind=e['link']
        elif od>1 and nd>1:kind='COMPLEX_SPLIT_MERGE_REVIEW'
        elif od>1:kind='SPLIT_CANDIDATE_REVIEW'
        elif nd>1:kind='MERGE_CANDIDATE_REVIEW'
        elif e['old_start']!=e['new_start'] or e['old_end']!=e['new_end']:kind='BOUNDARY_REVISION_REVIEW'
        elif e['old_status']!=e['new_status']:kind='STATUS_REVISION'
        elif e['old_id']!=e['new_id']:kind='ID_RENUMBER_ONLY'
        else:kind='UNCHANGED_INTERVAL_STATUS'
        records.append(dict(**e,old_degree=od,new_degree=nd,relation=kind))
    inventory=[]
    for side,df,degree in [('before',old,olddegree),('after',new,newdegree)]:
        for r in df.to_dict('records'):
            inventory.append(dict(side=side,native_id=r[identity],era=r['era'],industry_code=r['industry_code'],block=r['block'],
                start_date=r['start_date'],end_date=r['end_date'],status=r['status'],same_block_links=degree[r[identity]],
                disposition='UNMATCHED_REVIEW' if degree[r[identity]]==0 else 'LINKED_CANDIDATE'))
    return pd.DataFrame(records),pd.DataFrame(inventory)


def main():
    p=argparse.ArgumentParser();p.add_argument('--before',type=Path,required=True);p.add_argument('--after',type=Path,required=True);p.add_argument('--tag',required=True);p.add_argument('--kind',choices=['parent','child'],required=True);p.add_argument('--change-basis',choices=['definition_revision','data_refresh','same_version_check'],required=True);a=p.parse_args()
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}',a.tag):raise ValueError('Invalid tag')
    out=EP/'outputs/process_version_comparisons'/a.tag
    if out.exists():raise FileExistsError('Preserve comparison')
    file='processes.parquet' if a.kind=='parent' else 'children.parquet';identity='process_id' if a.kind=='parent' else 'child_id'
    paths=[]
    for root in [a.before,a.after]:
        rec=json.loads((root/'receipt.json').read_text())
        if sha(root/file)!=rec['artifacts'][file]:raise ValueError('Label artifact hash changed')
        paths.extend([root/file,root/'receipt.json'])
    old=pd.read_parquet(a.before/file);new=pd.read_parquet(a.after/file)
    edges,inventory=compare(old,new,identity);out.mkdir(parents=True)
    edges.to_parquet(out/'candidate_links.parquet',index=False);inventory.to_parquet(out/'complete_inventory.parquet',index=False)
    summary=dict(kind=a.kind,change_basis=a.change_basis,before_records=len(old),after_records=len(new),
        before_status=old.status.value_counts().to_dict(),after_status=new.status.value_counts().to_dict(),
        candidate_relation_counts={} if edges.empty else edges.relation.value_counts().to_dict(),
        unmatched=inventory[inventory.same_block_links.eq(0)].groupby('side').size().to_dict(),
        limits='Relations are review candidates, not accepted opportunity identity; no coverage is transferred. Status changes under definition_revision are not maturation. Other attributes require separate review.')
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');paths.extend([Path(__file__),EP/'protocols/v2_s05/plan.md'])
    (out/'receipt.json').write_text(json.dumps(dict(inputs={str(x):sha(x) for x in paths},artifacts={x.name:sha(x) for x in out.iterdir() if x.is_file()}),indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
