import re
from bs4 import BeautifulSoup
from wide_sources import CACHE,OUT
import pandas as pd
import requests,hashlib
from concurrent.futures import ThreadPoolExecutor
base='https://vip.stock.finance.sina.com.cn/corp/view/'
def page(kind,n):
    url=base+f'vII_{kind}Component.php?page={n}&indexid=000906'
    path=CACHE/f'{kind}{n}.html'
    if not path.exists():
        r=requests.get(url,timeout=20);r.raise_for_status();path.write_bytes(r.content)
    soup=BeautifulSoup(path.read_bytes().decode('gb18030','replace'),'html.parser'); rows=[]
    for tr in soup.select('tr'):
        cells=[x.get_text(strip=True) for x in tr.find_all('td',recursive=False)]
        if len(cells)>=3 and re.fullmatch(r'\d{6}',cells[0]) and re.fullmatch(r'\d{4}-\d\d-\d\d',cells[2]):
            rows.append((cells[0],cells[2],cells[3] if kind=='History' else None))
    pages=[int(x) for a in soup.select('a[href]') for x in re.findall(kind+r'Component.php\?page=(\d+)',a['href'])]
    return rows,max(pages or [1]),dict(url=url,rows=len(rows),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
records=[]; receipts=[]
for kind in ['History','Newest']:
    rows,n,receipt=page(kind,1);records.extend(rows);receipts.append(receipt)
    done=1
    with ThreadPoolExecutor(4) as pool:
        while done<n:
            batch=range(done+1,n+1);done=n
            for rows,last,receipt in pool.map(lambda i:page(kind,i),batch):
                records.extend(rows);receipts.append(receipt);n=max(last,n)
pd.DataFrame(records,columns=['code','start','end']).drop_duplicates().to_csv(OUT/'intervals800.csv',index=False)
pd.DataFrame(receipts).to_csv(OUT/'interval_receipts.csv',index=False)
