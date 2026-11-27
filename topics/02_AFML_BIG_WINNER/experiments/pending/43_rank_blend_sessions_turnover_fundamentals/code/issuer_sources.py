"""Historical member disclosure inventory; preserve issuer query outcomes, including delisted names."""
from disclosures import *
from threading import Event
from concurrent.futures import as_completed
def main():
    d=Path(__file__).resolve().parents[1];f=next(d.parent.glob('42_*/state/results/wide_scores.parquet'))
    symbols=pd.read_parquet(f,columns=['instrument']).instrument.unique()
    s=requests.Session();s.trust_env=False
    url='https://www.cninfo.com.cn/new/data/szse_stock.json'
    r=s.get(url,timeout=30);r.raise_for_status();data=r.json()
    (O/'directory.json').write_bytes(r.content)
    org={v['code']:v['orgId'] for v in data['stockList']}
    def work(sym):
        code=sym[2:];file=O/(code+'.json')
        if file.exists():return
        query(code,org.get(code,('gssz0' if sym.startswith('SZ') else 'gssh0')+code))
    with ThreadPoolExecutor(5) as ex:list(ex.map(work,sorted(symbols)))
if __name__=='__main__':main()
