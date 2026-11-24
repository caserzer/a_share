"""Cross-check the shipped books against their frozen universes and source bars."""
import json
import re
import numpy as np
import pandas as pd

from common import HERE, OUT, MARKET, PANEL, get_panel, sha

KEY = ["pool", "signal_date", "instrument"]


def read_rows(name):
    return pd.read_csv(OUT/name, parse_dates=["signal_date"])


def check_paths(panel):
    # Derive sample windows by date slicing independently of common.py's array offsets.
    bars = {k: pd.read_parquet(MARKET/f"qfq_{k}.parquet") for k in ("open","close","high","low")}
    dates = bars["open"].index
    sample = panel.groupby(["pool","scope"]).sample(n=40,random_state=39)
    for row in sample.itertuples():
        i = dates.get_loc(row.signal_date)
        stock = row.instrument
        close = bars["close"][stock]
        assert (row.entry_date,row.exit_date)==(dates[i+1],dates[i+11])
        hi = bars["high"][stock].iloc[i-20:i]
        lo = bars["low"][stock].iloc[i-4:i+1]
        path_low = bars["low"][stock].iloc[i+1:i+11]
        path_close = close.iloc[i+1:i+11]
        high20 = hi.max(skipna=False)
        wanted = [high20,lo.min(skipna=False),path_low.min(skipna=False),
                  close.iloc[i]/close.iloc[i-5]-1,
                  bars["open"].at[row.exit_date, stock]/bars["open"].at[row.entry_date,stock]-1,
                  float((path_close>=high20).sum()) if path_close.notna().all() and np.isfinite(high20) else np.nan]
        np.testing.assert_allclose([row.prior_high20,row.prior_low5,row.hold_low10,row.ret5,row.ret10,row.above_high_days],
                                   wanted,atol=1e-12,rtol=0,equal_nan=True)


def match_records(pairs, cases, identifier, key, label):
    ids = pairs[identifier].rename(columns=key)
    c = ids.merge(cases, on=KEY, validate="1:1")
    assert len(c)==len(pairs) and c.label.eq(label).all()
    assert np.array_equal(c.selected, pairs.selected)


def main():
    panel=get_panel()
    receipt=json.loads((OUT/"panel_receipt.json").read_text())
    assert sha(PANEL)==receipt["panel_sha256"]
    assert panel.groupby("pool").size().to_dict()=={"CSI300":40756,"CSI800":108303}
    assert not panel.duplicated(KEY).any()
    check_paths(panel)
    a=read_rows("breakout_cases.csv.gz")
    b=read_rows("oversold_cases.csv.gz")
    for cases,trigger in [(a,"breakout"),(b,"oversold")]:
        expected=panel.loc[panel[trigger].fillna(False),KEY]
        assert not cases.duplicated(KEY).any()
        assert cases.merge(expected,on=KEY,how="outer",indicator=True)._merge.eq("both").all()
    known=a.ret10.notna() & a.above_high_days.notna()
    labels=np.select([~known,(a.above_high_days>=6)&(a.ret10>0),(a.above_high_days<=4)&(a.ret10<0)],
                     ["未知","延续","失败"],default="中间")
    assert (a.label==labels).all()
    # Compare the original unrounded values, including exact touches of a prior low.
    bf=panel.merge(b[KEY+["label"]],on=KEY,validate="1:1")
    breach=bf.hold_low10<bf.prior_low5
    known=bf[["hold_low10","prior_low5","ret10"]].notna().all(axis=1)
    labels=np.select([~known,breach&(bf.ret10<0),~breach&(bf.ret10>0),breach&(bf.ret10>0)],
                     ["路径未知","持续下跌","止跌反弹","破低后收涨"],default="其他或持平")
    assert (bf.label==labels).all()
    ap=read_rows("breakout_pairs.csv.gz"); bp=read_rows("oversold_pairs.csv.gz")
    for col,label in [("continued_id","延续"),("failed_id","失败")]:
        joined=ap.merge(a, left_on=col,right_on="case_id",validate="1:1",suffixes=("_pair",""))
        assert len(joined)==len(ap) and joined.label.eq(label).all()
        for k in ["pool","scope","signal_date","selected"]: assert joined[k].eq(joined[k+"_pair"]).all()
    for prefix,label in [("rebound","止跌反弹"),("fall","持续下跌")]:
        col=prefix+"_instrument"
        match_records(bp,b,["pool","signal_date",col],{col:"instrument"},label)
    r=read_rows("oversold_replacements.csv.gz")
    assert len(r)==b.selected.sum() and not r.duplicated(["pool","signal_date","alternate"]).any()
    for side,flag in [("original",True),("alternate",False)]:
        g=r.rename(columns={side:"instrument"}).merge(panel[KEY+["oversold","selected"]],on=KEY,validate="1:1")
        assert len(g)==len(r) and g.selected.eq(flag).all() and g.oversold.eq(flag).all()
    np.testing.assert_allclose(r.cash_lot_diff_after_fees,
       ((r.alt_ret10-r.old_ret10)*.998/1.001).where(r.both_fillable_known),atol=1e-12,equal_nan=True)
    for doc in HERE.glob("*.md"):
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)",doc.read_text()):
            assert "://" in target or (doc.parent/target).exists() or target=="results/verification.json",(doc,target)
    files=sorted([*HERE.glob("*.md"),*HERE.glob("*.py"),*[f for f in OUT.iterdir() if f.is_file() and f.name!="verification.json"]])
    hashes={str(f.relative_to(HERE)):sha(f) for f in files}
    result=dict(panel_rows=len(panel),unique_stock_dates=receipt["unique_stock_dates"],independently_sliced_windows=160,
                breakout_cases=len(a),breakout_pairs=len(ap),oversold_cases=len(b),oversold_pairs=len(bp),
                oversold_replacement_seats=len(r),paired_fillable_seats=int(r.both_fillable_known.sum()),sha256=hashes)
    (OUT/"verification.json").write_text(json.dumps(result,indent=2)+"\n")
    print({k:v for k,v in result.items() if k!="sha256"})


if __name__=="__main__":
    main()
