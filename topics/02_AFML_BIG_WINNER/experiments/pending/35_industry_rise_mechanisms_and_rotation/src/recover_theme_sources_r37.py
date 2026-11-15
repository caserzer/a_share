"""Bounded raw-byte and decompressed HTML hash lookup, no network."""
import gzip
import subprocess
from common import *
def run():
 out=ROOT/'outputs/r37';out.mkdir(exist_ok=True);queue=ROOT/'outputs/r36/local_source_recovery_queue.json';targets=json.loads(queue.read_text());byhash={}
 for t in targets:byhash.setdefault(t['content_hash'],[]).append(t['document_id'])
 roots=['/home/xiaolv/.cache/a_share','/home/xiaolv/code/golden_loop_artifacts','/home/xiaolv/code/a_share'];cmd=['rg','--files','-uu',*roots,'-g','!**/.venv/**','-g','!**/.git/**','-g','!**/node_modules/**']
 for glob in ['*.pdf','*.PDF','*.html','*.html.gz','*.txt','*.htm']:cmd+=['-g',glob]
 paths=subprocess.run(cmd,check=True,capture_output=True,text=True).stdout.splitlines();rows=[];matches=[];skips=[];total=0
 for name in paths:
  p=Path(name)
  if p.is_relative_to(out):continue
  size=p.stat().st_size
  if size>50_000_000:skips.append(dict(path=name,size=size,reason='over50MB'));continue
  try:
   h=sha(p);total+=size;row=dict(path=name,size=size,raw_sha256=h)
   for doc in byhash.get(h,[]):matches.append(dict(document_id=doc,path=name,mode='raw_bytes',sha256=h))
   if name.endswith('.html.gz'):
    with gzip.open(p,'rb') as f:content=f.read(50_000_001)
    if len(content)>50_000_000:row['decompressed_skipped']=True
    else:
     h=hashlib.sha256(content).hexdigest();row['decompressed_sha256']=h
     for doc in byhash.get(h,[]):matches.append(dict(document_id=doc,path=name,mode='decompressed_html',sha256=h))
   rows.append(row)
  except (OSError,EOFError) as e:skips.append(dict(path=name,reason=type(e).__name__))
 js(out/'file_hashes.json',rows);js(out/'matches.json',matches);js(out/'skips.json',skips)
 js(out/'receipt.json',dict(queue_sha256=sha(queue),code_sha256=sha(__file__),roots=roots,extensions=['pdf','PDF','html','html.gz','txt','htm'],candidate_files=len(paths),hashed_files=len(rows),bytes_read=total,skipped=len(skips),target_documents=len(targets),target_hashes=len(byhash),matching_documents=len({x['document_id'] for x in matches}),match_rows=len(matches),limitation='bounded extensions and directories; not whole filesystem absence; normalized text or non-file archives not reconstructed'))
 print(json.dumps(json.loads((out/'receipt.json').read_text()),ensure_ascii=False))
if __name__=='__main__':run()
