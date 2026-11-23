"""Run with PyMuPDF, capture the two-column consolidated statement and its source pages."""
from pathlib import Path
import csv,re,hashlib
import pymupdf
here=Path(__file__).resolve().parent;out=here/"results"
records=[]
for row in csv.DictReader((out/"sources.csv").open()):
    stock,period=row["instrument"],row["period"]
    f=out/"originals"/f"{stock}_{period}.pdf";doc=pymupdf.open(f)
    assert stock[2:] in re.sub(r"\s+","",doc[0].get_text())
    found={}
    for i,page in enumerate(doc):
        s=re.sub(r"\s+","",page.get_text())
        for field,label in [("total_revenue","一、营业总收入"),("parent_profit","归属于母公司股东的净利润")]:
            m=re.search(label+r"(?:（净亏损以[“”－\-]+号填列）)?([\d,]+\.\d{2})([\d,]+\.\d{2})",s)
            if not m:continue
            assert field not in found,(stock,period,field)
            if field=="total_revenue":
                preceding=re.sub(r"\s+","",("".join(doc[j].get_text() for j in range(max(i-1,0),i+1))))
                assert "合并利润表" in preceding and "人民币" in preceding
            found[field]=m.groups()
            records.append({**row,"pdf_sha256":hashlib.sha256(f.read_bytes()).hexdigest(),"field":field,"page":i+1,"current":m[1].replace(",",""),"prior":m[2].replace(",","")})
    assert len(found)==2,(stock,period,found)
with (out/"source_values.csv").open("w") as f:
    w=csv.DictWriter(f,fieldnames=records[0]);w.writeheader();w.writerows(records)
