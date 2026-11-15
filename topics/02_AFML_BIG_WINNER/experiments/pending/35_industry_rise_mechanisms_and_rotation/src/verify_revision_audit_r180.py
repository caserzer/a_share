"""Independent aligned comparison of source values and rollback evidence."""
import pandas as pd
from common import *
from versioned_observations import verify_bundle


def run():
    out=ROOT/'outputs/r180';receipt=json.loads((out/'receipt.json').read_text())
    for p,h in receipt['reads'].items():assert sha(p)==h
    cells=pd.read_parquet(out/'cell_changes.parquet');presence=pd.read_parquet(out/'row_changes.parquet')
    schemas=json.loads((out/'source_schemas.json').read_text());keys=KEY+['date'];fields=['nav','block','day_i','coverage','members','membership_asof','breadth21','breadth63']
    total=0
    for date in sorted(cells["asof"].unique()):
        versions={}
        for version in ['old','new']:
            frames=[]
            for s in schemas:
                if s['asof']!=date or s['version']!=version:continue
                assert sha(s['path'])==s['sha256'];d=pd.read_parquet(s['path'])
                assert s['absent_fields']==[f for f in fields if f not in d]
                frames.append(d)
            d=pd.concat(frames,ignore_index=True);versions[version]=d[d.date<=date].set_index(keys)[fields]
        a,b=versions['old'],versions['new'];idx=a.index.intersection(b.index)
        expected=a.loc[idx].compare(b.loc[idx],keep_shape=False,keep_equal=False)
        actual=cells[cells["asof"].eq(date)]
        for field in fields:
            if field not in expected.columns.get_level_values(0):assert not actual.field.eq(field).any();continue
            diff=expected[field].dropna(how='all');got=actual[actual.field.eq(field)].set_index(keys)
            assert set(diff.index)==set(got.index)
            for col,side in [('old_value','self'),('new_value','other')]:
                left=got[col].sort_index();right=diff[side].sort_index()
                if field=='membership_asof':
                    left=pd.to_datetime(left);right=pd.to_datetime(right)
                else:
                    left=pd.to_numeric(left);right=pd.to_numeric(right)
                assert ((left==right)|(left.isna()&right.isna())).all()
            total+=len(diff)
        p=presence[presence["asof"].eq(date)]
        assert set(p[p.change.eq('added')].set_index(keys).index)==set(b.index.difference(a.index))
        assert set(p[p.change.eq('removed')].set_index(keys).index)==set(a.index.difference(b.index))
    rb=json.loads((out/'rollback.json').read_text());m=verify_bundle(rb['evaluation']);old=verify_bundle(rb['previous_evaluation']);verify_bundle(rb['snapshot'])
    assert sha(Path(rb['previous_evaluation'])/'manifest.json')==rb['previous_sha256']
    assert m['identity']['snapshot']==old['identity']['snapshot'] and m['identity']['asof']<old['identity']['asof']
    d=pd.read_parquet(Path(rb['evaluation'])/'outcomes.parquet');assert len(d)==1022 and d.status.eq('pending_market_sessions').all() and d.excess.isna().all() and d.evaluation_kind.eq('historical_replay').all()
    js(out/'verification.json',dict(status='PASS',changed_cells=total,row_changes=len(presence),rollback_rows=len(d),source_schemas=len(schemas),prior_evaluation_unchanged=True))
    print('PASS',total,len(presence),len(d))


if __name__=='__main__':run()
