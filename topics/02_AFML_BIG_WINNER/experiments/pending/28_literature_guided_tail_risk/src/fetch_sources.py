"""Bounded public-source retrieval; raw copyrighted documents remain local only."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import requests
import argparse

EP = Path(__file__).resolve().parents[1]
SOURCES = [
    ("US-01_author", "https://www.mit.edu/~jcstein/for-crash.pdf"),
    ("US-02_published", "https://campbell.scholars.harvard.edu/sites/g/files/omnuum5881/files/campbell/files/campbellhilscherszilagyi_jf2008.pdf"),
    ("US-03_accepted", "https://eprints.soton.ac.uk/452368/1/Financial_Distress_Risk_and_Stock_Price_Crashes.pdf"),
    ("US-04_nber", "https://www.nber.org/system/files/working_papers/w19375/w19375.pdf"),
    ("CN-01_author", "https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID4148454_code4934227.pdf?abstractid=4148454&mirid=1"),
    ("CN-01_publisher", "https://doi.org/10.1016/j.finmar.2024.100908"),
    ("CN-02_publisher", "https://www.sciencedirect.com/science/article/pii/S1544612321001768"),
    ("CN-03_publisher", "https://www.sciencedirect.com/science/article/pii/S0275531923001010"),
    ("CN-04_proof", "https://uploads.strikinglycdn.com/files/f36fb6f3-5a5e-46f5-b061-d0b70110521c/On%20the%20prediction%20of%20stock%20price%20crash%20risk%20using%20textual%20sentiment%20of%20management%20statement.pdf"),
    ("CN-04_publisher", "https://doi.org/10.1108/CFRI-12-2022-0250"),
    ("PRACTICE-01", "https://www.robeco.com/en-us/insights/2022/06/forecasting-stock-crash-risk-with-machine-learning"),
    ("US-04_author_site", "https://www.bryankellyacademic.org/"),
    ("CN-01_author_site", "https://fuweijiang.weebly.com/research.html"),
]
FOLLOWUP = [
    ("US-03_durham", "https://durham-repository.worktribe.com/OutputFile/1282457"),
    ("US-04_published", "https://academic.oup.com/rfs/article-pdf/27/10/2841/24449527/hhu039.pdf"),
    ("US-04_corrigendum", "https://www.dropbox.com/scl/fi/xx8q12zyijny1h0t6y12p/corrigendum.pdf?rlkey=hec8vuf4oj71muymte38p9887&dl=1"),
    ("PRACTICE-01_whitepaper", "https://www.robeco.com/files/docm/docu-202206-forecasting-stock-crash-risk-with-machine-learning-us.pdf"),
    ("CN-01_crossref", "https://api.crossref.org/works/10.1016/j.finmar.2024.100908"),
    ("CN-02_crossref", "https://api.crossref.org/works/10.1016/j.frl.2021.102095"),
    ("CN-03_crossref", "https://api.crossref.org/works/10.1016/j.ribaf.2023.101975"),
]
LAST_ACCESS = [
    ("CN-01_publisher_tdm", "https://api.elsevier.com/content/article/PII:S1386418124000260?httpAccept=text/xml"),
    ("CN-02_publisher_tdm", "https://api.elsevier.com/content/article/PII:S1544612321001768?httpAccept=text/xml"),
    ("CN-03_publisher_tdm", "https://api.elsevier.com/content/article/PII:S0275531923001010?httpAccept=text/xml"),
    ("US-03_crossref", "https://api.crossref.org/works/10.1016/j.jcorpfin.2020.101870"),
]


def fetch(item):
    name, url = item
    folder = EP / 'outputs/local_cache/sources'
    receipt = dict(id=name, requested_url=url, accessed_utc=datetime.now(timezone.utc).isoformat())
    try:
        r = requests.get(url, timeout=35, headers={'User-Agent': 'Mozilla/5.0 (academic replication audit)'})
        pdf = r.content.startswith(b'%PDF')
        path = folder / (name + ('.pdf' if pdf else '.html'))
        path.write_bytes(r.content)
        receipt.update(status=r.status_code, final_url=r.url, pdf=pdf, bytes=len(r.content),
                       sha256=hashlib.sha256(r.content).hexdigest(), path=str(path.relative_to(EP)))
        if pdf:
            import fitz
            doc = fitz.open(path)
            text = '\n'.join(f'\n=== PDF PAGE {i+1} ===\n{p.get_text()}' for i, p in enumerate(doc))
            path.with_suffix('.txt').write_text(text)
            receipt['pages'] = len(doc)
    except Exception as exc:
        receipt['error'] = type(exc).__name__ + ': ' + str(exc)[:500]
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch', choices=['initial', 'followup', 'last_access'], default='initial')
    args = parser.parse_args()
    path = EP / 'outputs/audits/source_access.jsonl'
    with ThreadPoolExecutor(max_workers=4) as executor:
        selected = {'initial': SOURCES, 'followup': FOLLOWUP, 'last_access': LAST_ACCESS}[args.batch]
        for result in executor.map(fetch, selected):
            with path.open('a') as stream:
                stream.write(json.dumps(result, ensure_ascii=False) + '\n')
            print(json.dumps({k: v for k, v in result.items() if k not in ['requested_url', 'final_url', 'sha256']}), flush=True)
