"""Recheck the dated issuer documents separately from the sealed price experiment."""
from decimal import Decimal
import re

import pandas as pd
from pypdf import PdfReader

from prepare import D, ROOT, PRIVATE, sha, dump

DOCS = [
    ("q1", "2024-04-27", 8, "2024-05/07/1edb3ed2dbef4bef89ff23a72e3549fa",
     "b706e237e25ff54a0bde7070a13b019a5e1eec7f412eb9d0baf33e750a7c32e2"),
    ("half", "2024-08-09", 30, "2024-08/09/2b1c902cd61b47619604f7ec114b2072",
     "898b37d6529d0042aa66461bae11b84a47f9337c2ff1d572155bfa71fca77c58")]


def run():
    documents = []
    for name, posted, page, suffix, checksum in DOCS:
        pdf = ROOT/"source_cache"/(name+".pdf")
        assert sha(pdf) == checksum
        text = PdfReader(pdf).pages[page-1].extract_text()
        row = next(line for line in text.splitlines() if "一、营业总收入" in line)
        values = re.findall(r"[0-9,]+\.\d{2}", row)
        assert len(values) == 2 and "合并利润表" in text
        documents.append(dict(url="https://www.moutaichina.com/mtgf/articleFileDir/"+suffix+".pdf",
                              posted=posted, page=page, sha256=checksum, current_prior_cny=values))
    (q, old_q), (half, old_half) = [
        [Decimal(v.replace(",", "")) for v in d["current_prior_cny"]] for d in documents]
    current = (half-q)/(old_half-old_q)-1
    previous = q/old_q-1
    state = pd.read_parquet(D/"panel.parquet").query("instrument=='SH600519' and period=='2024Q2'").iloc[0]
    gap = current-previous
    assert abs(float(gap)-state.acceleration) < 1e-10
    calendar = pd.read_parquet(PRIVATE/"market.parquet").index
    usable = calendar[calendar.searchsorted(pd.Timestamp(documents[1]["posted"]), side="right")]
    dump(D/"issuer_pilot.json", dict(instrument="SH600519", report_period="2024Q2",
         issuer_listing="https://www.moutaichina.com/mtgf/tzzgx/cwbg/82bde676-2.html",
         documents=documents, metric="合并利润表 营业总收入", q1_growth=float(previous),
         q2_growth=float(current), change=float(gap), issuer_next_session=str(usable.date()),
         vendor_next_session=str(state.known_date.date()), lag_days=(state.known_date-usable).days,
         included_in_backtest=False))


if __name__ == "__main__":
    run()
