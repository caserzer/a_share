"""Chronological adaptation; every peer historical forecast remains fixed at its origin."""
from common import *
from hierarchical_model import one_origin
from global_model import freeze


def walk(source,prefix,save_peers=True):
    source=source.sort_values(['date','instrument']).reset_index(drop=True)
    previous=pd.DataFrame(columns=list(source.columns)+['GP']);parts=[];peerparts=[];audits=[]
    for date,current in source.groupby('date',sort=True):
        path=CACHE/f'{prefix}_{date.date()}.parquet';ppath=CACHE/f'{prefix}_{date.date()}_peers.parquet';receipt=AUDIT/f'{prefix}_{date.date()}.json'
        source_hash=hashlib.sha256(current.to_csv(index=False).encode()).hexdigest()
        if receipt.exists():
            audit=json.loads(receipt.read_text());assert digest(path)==audit['prediction_sha256']
            assert audit['source_snapshot_sha256']==source_hash
            out=pd.read_parquet(path)
            if save_peers:
                assert digest(ppath)==audit['peers_sha256'];peerparts.append(pd.read_parquet(ppath))
        else:
            out,peers,audit=one_origin(current.reset_index(drop=True),previous)
            out.to_parquet(path,index=False)
            if save_peers:peers.to_parquet(ppath,index=False);peerparts.append(peers)
            audit.update(prediction_sha256=digest(path),source_keys_sha256=keyhash(current),
                peers_sha256=digest(ppath) if save_peers else None,source_snapshot_sha256=source_hash)
            write_json(receipt,audit)
        previous=pd.concat([previous,out],ignore_index=True);parts.append(out);audits.append(audit)
        if date.month in [1,7]:print(prefix,date.date(),'rows',len(current),'history',audit['history_rows'],flush=True)
    full=pd.concat(parts,ignore_index=True);full.to_parquet(CACHE/f'{prefix}_all.parquet',index=False)
    if save_peers:pd.concat(peerparts,ignore_index=True).to_parquet(CACHE/f'{prefix}_peers.parquet',index=False)
    write_json(AUDIT/f'{prefix}_fits.json',audits)
    return full


def main():
    freeze();assert json.loads((AUDIT/'synthetic_controls.json').read_text())['all_passed'],'Control failure stops real adaptation'
    for name in ['M_R','L2']:
        source=pd.read_parquet(CACHE/f'global_oos_{name}.parquet')
        walk(source,'real_'+name)
    print('All fixed real-data adaptations complete',flush=True)


if __name__=='__main__':main()
