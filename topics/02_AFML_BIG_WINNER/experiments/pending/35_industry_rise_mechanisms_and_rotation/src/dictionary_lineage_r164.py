"""Versioned factor lineage appendix preserving original definitions verbatim."""
from common import *

def run():
 out=ROOT/'outputs/r164';original=json.loads((out/'original_dictionary.json').read_text());protocol=json.loads((ROOT/'protocols/r164.json').read_text());mapping=protocol['mappings'];assert {x['factor'] for x in original}==set(mapping);items=[]
 for i,entry in enumerate(original):
  m=mapping[entry['factor']];refs=[]
  for rel in m['evidence']:
   p=ROOT/rel;assert p.is_file();refs.append(dict(path=rel,sha256=sha(p),bytes=p.stat().st_size))
  items.append(dict(factor=entry['factor'],module=entry['module'],original_index=i,original_definition=entry,current_status=m['status'],current_interpretation=m['interpretation'],current_evidence=refs,predictive_adoption=False,strict_pit_certified=False))
 js(out/'factor_dictionary.json',dict(revision='R164',quality='Historical-proxy',definitions=len(items),original_dictionary_sha256=sha(out/'original_dictionary.json'),items=items,scope='source and interpretation appendix; no new factors, formulas or calibrated signals'))
 js(out/'receipt.json',dict(status='PASS',definitions=len(items),original_sha256=sha(out/'original_dictionary.json'),protocol_sha256=sha(ROOT/'protocols/r164.json'),code_sha256=sha(Path(__file__)),unclosed_price_repair_factors=[x['factor'] for x in items if x['current_status']=='price_repair_followup_pending']))
 print('R164 DICTIONARY',len(items))
if __name__=='__main__':run()
