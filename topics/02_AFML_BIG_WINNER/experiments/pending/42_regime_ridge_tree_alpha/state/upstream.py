"""Content digests of external inputs underpinning state, selection and original account parity."""
import csv
from core42 import *
from engine import LOCAL,PRIVATE,STORE,OUT800,DEST
from inputs42 import EP40
def main():
    paths=set()
    for root in [LOCAL,PRIVATE]:paths.update(root.glob('*.parquet'))
    paths.update((PRIVATE/'style_caps_20261117').glob('*.json'))
    for root,names in [(STORE,['effective800.parquet','effective_changes.csv','index800.parquet']),(OUT800,['scores.parquet']),
                       (DEST,['daily_scores.parquet']),(EP41/'p1/results',['daily.parquet','pairs.parquet','actual_stock_pnl.parquet']),
                       (EP41/'p2/results',['scores.parquet','funded_daily.parquet']),(EP41/'models/results',['funded_daily.parquet','model_accounts.csv']),
                       (PRIVATE/'net_excess_20261116',['H00300.CSI.json'])]:
        paths.update(root/n for n in names)
    paths.update(p for p in (OUT800/'models').rglob('*') if p.is_file())
    for root,names in [(EP41/'p1',['engine.py','book.cpp','matching.py']),(EP40/'lightgbm/followup/csi800_69',['inputs.py','scores.py']),
                       (EP40/'lightgbm/followup',['common_inputs.py','accounts_followup.py']),(PRIVATE.parent/'src',['features.py'])]:
        paths.update(root/n for n in names)
    with (OUT/'upstream_sha256.csv').open('w',newline='') as fp:
        wt=csv.writer(fp);wt.writerow(['path','bytes','sha256'])
        for p in sorted(paths):
            with p.open('rb') as src:digest=hashlib.file_digest(src,'sha256').hexdigest()
            wt.writerow([p,p.stat().st_size,digest])
if __name__=='__main__':main()

