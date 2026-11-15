from common import *
def run():
 out=ROOT/'outputs/r37';r=json.loads((out/'receipt.json').read_text());q=ROOT/'outputs/r36/local_source_recovery_queue.json';assert sha(q)==r['queue_sha256']
 targets={x['content_hash'] for x in json.loads(q.read_text())};files=json.loads((out/'file_hashes.json').read_text());matches=json.loads((out/'matches.json').read_text());assert len(files)==r['hashed_files'] and sum(x['size'] for x in files)==r['bytes_read']
 expected=[(x['path'],h) for x in files for h in [x['raw_sha256'],x.get('decompressed_sha256')] if h in targets];assert not expected and not matches
 # Recheck immutable-looking raw documents, excluding mutable research reports/logs.
 sample=[x for x in files if x['path'].lower().endswith('.pdf')][:30]
 for x in sample:assert sha(x['path'])==x['raw_sha256']
 js(out/'verification.json',dict(status='PASS',manifest_entries=len(files),target_hashes=len(targets),intersection_size=len(expected),direct_pdf_rehashes=len(sample),limitation='saved scan scope only, not global nonexistence'))
 print('R37 VERIFIED',len(files),'manifest entries,',len(sample),'PDF rehashes')
if __name__=='__main__':run()
