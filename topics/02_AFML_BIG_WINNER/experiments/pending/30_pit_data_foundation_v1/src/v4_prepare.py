"""Freeze outcome-independent missing-period cohort; render original review crops."""

import json
import sys

import pandas as pd

from archive import sha, write_json
from v4_core import V4, PUBLIC, BASE, baseline, source_bytes


def prepare():
    PUBLIC.mkdir(parents=True, exist_ok=True)
    gaps = pd.read_csv(baseline("provenance/v2_selected_financial_recovery_bridge.csv"))
    gaps = gaps[~gaps.v3_original_pdf_recovered]
    candidates = pd.read_parquet(
        baseline("normalized/ocr_retired_equity_candidates.parquet")
    )
    verified = pd.read_parquet(baseline("normalized/retired_equity_links.parquet"))
    retired = [
        json.loads(s)
        for s in pd.read_parquet(
            baseline("indices/retirement_complete.parquet")
        ).announcement
    ]
    selected = []
    for r in gaps.itertuples():
        codes = set(
            candidates.loc[candidates.security_id.eq(r.security_id), "retired_code"]
        )
        matches = [
            a
            for a in retired
            if codes.intersection(c["stock_code"] for c in a.get("codes", []))
            and str(r.report_year) in a["title"]
            and "年度报告" in a["title"]
            and not any(
                k in a["title"]
                for k in ["摘要", "提示", "延期", "无法", "说明", "董事", "监事"]
            )
        ]
        if matches and r.security_id not in set(verified.security_id):
            c = (
                candidates[candidates.security_id.eq(r.security_id)]
                .sort_values("art_code")
                .iloc[0]
                .to_dict()
            )
            c["missing_period"] = str(r.report_year) + "-12-31"
            c["instrument"] = r.instrument
            selected.append(c)
    pd.DataFrame(selected).to_parquet(V4 / "identity_review_queue.parquet", index=False)
    pd.DataFrame(selected).drop(columns=["exact_clause"]).to_csv(
        PUBLIC / "identity_review_queue.csv", index=False
    )
    write_json(
        PUBLIC / "selection.json",
        dict(
            missing_v3_full_report_periods=len(gaps),
            missing_in_both_v2_v3=int((~gaps.v2_original_pdf_recovered).sum()),
            identity_source_page_review_queue=len(selected),
            rule="all original scanned confirmations bridging missing prior-selected periods; before numeric-value inspection",
        ),
    )


def render():
    sys.path.insert(0, str(BASE / "vendor"))
    import pymupdf
    from PIL import Image, ImageDraw

    pages = []
    for r in pd.read_parquet(V4 / "identity_review_queue.parquet").to_dict("records"):
        art = r["art_code"]
        doc = json.loads(baseline(f"documents/retirement/{art}.json").read_text())
        source = source_bytes(doc["source"])
        ocr_name = f"ocr/retirement/3f95f31d378ba2ee146440b6720062dd22c5e72239c9dc739279a10141b5830e/{art}.json"
        ocr = json.loads(baseline(ocr_name).read_text())
        crops, evidence = [], []
        with pymupdf.open(source) as pdf:
            for o in ocr["pages"]:
                code_lines = [
                    x
                    for x in o["lines"]
                    if r["old_code"] in x["text"] or r["retired_code"] in x["text"]
                ]
                if not code_lines:
                    continue
                number = o["physical_page"]
                pix = pdf[number - 1].get_pixmap(
                    matrix=pymupdf.Matrix(2, 2), colorspace=pymupdf.csRGB, alpha=False
                )
                image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                folder = V4 / "reviews/identity"
                folder.mkdir(parents=True, exist_ok=True)
                full = folder / f"{art}_page{number}.png"
                image.save(full)
                top = max(0, int(min(y for x in code_lines for _, y in x["box"])) - 140)
                bottom = min(
                    pix.height,
                    int(max(y for x in code_lines for _, y in x["box"])) + 140,
                )
                crop = image.crop((0, top, pix.width, bottom))
                path = folder / f"{art}_page{number}_codes.png"
                crop.save(path)
                crops.append(crop)
                evidence.append(
                    dict(
                        physical_page=number,
                        full_image=str(full.relative_to(V4)),
                        full_image_sha256=sha(full),
                        code_crop=str(path.relative_to(V4)),
                        code_crop_sha256=sha(path),
                        crop_box=[0, top, pix.width, bottom],
                    )
                )
        if not crops:
            raise ValueError("no original-page code evidence crop")
        width = max(x.width for x in crops)
        sheet = Image.new("RGB", (width, sum(x.height for x in crops) + 45), "white")
        ImageDraw.Draw(sheet).text((10, 10), art, fill="black")
        y = 45
        for crop in crops:
            sheet.paste(crop, (0, y))
            y += crop.height
        path = V4 / f"reviews/identity/{art}_contact.png"
        sheet.save(path)
        pages.append(
            dict(
                art_code=art,
                source_sha256=doc["source"]["sha256"],
                images=evidence,
                contact_sheet=str(path.relative_to(V4)),
                contact_sha256=sha(path),
            )
        )
    write_json(V4 / "reviews/identity/rendered.json", pages)


if __name__ == "__main__":
    prepare()
    render()
