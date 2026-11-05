"""Isolated output/cache replay, reading the same immutable EP30 release.

The original experiment outputs and payloads are never overwritten. Path rebinding
is performed before importing any pipeline module; numerical code stays identical.
"""
import argparse
import json
import shutil
from pathlib import Path

import common


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--destination',type=Path,required=True)
    p.add_argument('--phase',choices=['data','fit','winner','sensitivity','h12-independence','auxiliary','admit','constant','score','verify-data'],required=True)
    p.add_argument('--hypothesis',choices=['H01','H02','H03','H07','H10','H11','H12'])
    args=p.parse_args()
    original_cache=common.cache()
    original_out=common.OUT
    target=args.destination.resolve()
    if target == original_cache or original_cache in target.parents:
        raise ValueError('replay must use a separate cache tree')
    if target==common.EP or common.EP in target.parents:
        raise ValueError('replay must not write inside original experiment')
    target.mkdir(parents=True,exist_ok=True,mode=0o700)
    common.OUT=target/'outputs'
    common.OUT.mkdir(exist_ok=True)
    (common.OUT/'manifests').mkdir(exist_ok=True)
    (common.OUT/'audits').mkdir(exist_ok=True)
    for name in ['preregistration.json','revision_01.json']:
        dest=common.OUT/'manifests'/name
        if not dest.exists():shutil.copyfile(original_out/'manifests'/name,dest)
    private=target/'private'
    private.mkdir(exist_ok=True,mode=0o700)
    common.cache=lambda:private
    if args.phase == 'data':
        from build_data import main as build
        build()
    elif args.phase == 'fit':
        if not args.hypothesis: p.error('--hypothesis required for fit')
        from walk_forward import run
        run(args.hypothesis)
    elif args.phase == 'winner':
        from big_winner import main as winner
        winner()
    elif args.phase == 'sensitivity':
        from turnover_sensitivity import main as sensitivity
        sensitivity()
    elif args.phase == 'h12-independence':
        from h12_independence import main as independence
        independence()
    elif args.phase == 'auxiliary':
        from auxiliary_baselines import main as auxiliary
        auxiliary()
    elif args.phase == 'constant':
        from constant_baseline import main as constant
        constant()
    elif args.phase == 'admit':
        from admit_folds import main as admit
        admit()
    elif args.phase == 'score':
        from evaluate import main as score
        from big_winner import evaluate as winner_score
        from turnover_sensitivity import evaluate as sensitivity_score
        from h12_independence import evaluate as independence_score
        from auxiliary_baselines import evaluate as auxiliary_score
        from constant_baseline import evaluate as constant_score
        score();winner_score();sensitivity_score();independence_score();auxiliary_score();constant_score()
    elif args.phase == 'verify-data':
        old=json.loads((original_cache/'data/COMPLETE.json').read_text())['files']
        new=json.loads((private/'data/COMPLETE.json').read_text())['files']
        differences=[name for name in old if old[name] != new.get(name)]
        result=dict(status='PASS' if not differences and set(old)==set(new) else 'FAIL',
                    original_manifest_sha256=common.sha(original_cache/'data/COMPLETE.json'),
                    replay_manifest_sha256=common.sha(private/'data/COMPLETE.json'),
                    parquet_files=len(old),mismatches=differences,replay_root=str(target),
                    source_release='EP30 frozen release only',original_outputs_unchanged=True)
        common.write_json(original_out/'audits/independent_data_replay.json',result)
        if result['status'] != 'PASS':raise ValueError('replay differs')
        print(result)


if __name__=='__main__':main()
