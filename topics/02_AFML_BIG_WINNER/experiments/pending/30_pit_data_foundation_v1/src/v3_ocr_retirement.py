"""Local scanned-original OCR candidates. No OCR row becomes a verified equity link."""

import hashlib
import json
import sys
import platform
import pandas as pd
from archive import sha, write_json
from v3_core import V3, PUBLIC3, documents, code_version
from v3_evidence import original_pages, security_map
from v3_rights import retired_link


def main():
    version = code_version(__file__)
    sys.path.insert(0, str(V3 / "vendor"))
    sys.path.insert(0, str(V3 / "ocr_vendor"))
    import pymupdf
    import numpy as np
    import onnxruntime as ort
    import cv2
    from rapidocr_onnxruntime import RapidOCR

    engine = RapidOCR(
        intra_op_num_threads=2,
        inter_op_num_threads=1,
        det_use_cuda=False,
        cls_use_cuda=False,
        rec_use_cuda=False,
    )
    models = [
        dict(path=str(p.relative_to(V3)), sha256=sha(p))
        for p in sorted((V3 / "ocr_vendor/rapidocr_onnxruntime/models").glob("*.onnx"))
    ]
    write_json(
        PUBLIC3 / "ocr_environment.json",
        dict(
            python=platform.python_version(),
            numpy=np.__version__,
            onnxruntime=ort.__version__,
            opencv=cv2.__version__,
            engine="rapidocr_onnxruntime==1.4.4",
            models=models,
            raster_dpi=144,
            max_physical_pages_per_document=3,
            cpu_threads=2,
            values_are_unreviewed_candidates=True,
        ),
    )
    mapping, candidates, docs = security_map(), [], []
    selected = []
    for p, r in documents("retirement"):
        if (
            r["status"] != "ORIGINAL_PDF_RECOVERED"
            or "确权" not in r["announcement"]["title"]
        ):
            continue
        pages = original_pages(r["source"]["archive_path"], r["source"]["sha256"])
        if sum(len(s.strip()) for s in pages) == 0:
            selected.append((p, r))
    for i, (p, r) in enumerate(selected):
        target = V3 / f"ocr/retirement/{version}/{p.stem}.json"
        if target.exists():
            result = json.loads(target.read_text())
        else:
            result = dict(
                art_code=p.stem,
                source_sha256=r["source"]["sha256"],
                source_uri=r["source"]["url"],
                notice_date=r["announcement"]["notice_date"][:10],
                transform_sha256=version,
                models=models,
                status="UNKNOWN",
                pages=[],
            )
            try:
                source = r["source"]["archive_path"]
                if sha(source) != result["source_sha256"]:
                    raise ValueError("changed scanned original")
                with pymupdf.open(source) as pdf:
                    for j, page in enumerate(pdf[:3]):
                        pix = page.get_pixmap(
                            matrix=pymupdf.Matrix(2, 2),
                            colorspace=pymupdf.csRGB,
                            alpha=False,
                        )
                        pixels = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                            pix.height, pix.width, 3
                        )
                        lines, _ = engine(cv2.cvtColor(pixels, cv2.COLOR_RGB2BGR))
                        rows = [
                            dict(
                                box=np.asarray(box).tolist(),
                                text=text,
                                score=float(score),
                            )
                            for box, text, score in (lines or [])
                        ]
                        result["pages"].append(
                            dict(
                                physical_page=j + 1,
                                width=pix.width,
                                height=pix.height,
                                rgb_pixels_sha256=hashlib.sha256(
                                    pix.samples
                                ).hexdigest(),
                                lines=rows,
                            )
                        )
                result["status"] = "OCR_COMPLETED_UNREVIEWED"
            except Exception as exc:
                result["error"] = str(exc)[:250]
            write_json(target, result)
        texts = [
            "\n".join(row["text"] for row in page["lines"]) for page in result["pages"]
        ]
        found = retired_link(texts, mapping)
        docs.append(
            dict(
                art_code=p.stem,
                status=result["status"],
                pages=len(texts),
                candidate_links=len(found),
            )
        )
        for link in found:
            candidates.append(
                dict(
                    **link,
                    art_code=p.stem,
                    source_sha256=r["source"]["sha256"],
                    source_uri=r["source"]["url"],
                    quality_tier="UNKNOWN/BLOCKED",
                    source_page_reviewed=False,
                    source_text_method="OCR_SCANNED_ORIGINAL",
                    transform_sha256=version,
                )
            )
        if i % 10 == 0:
            print("scanned retirement originals", i + 1, "/", len(selected), flush=True)
    f = pd.DataFrame(candidates)
    f.to_parquet(V3 / "normalized/ocr_retired_equity_candidates.parquet", index=False)
    f.drop(columns=["exact_clause"], errors="ignore").to_csv(
        PUBLIC3 / "ocr_retired_equity_candidates.csv", index=False
    )
    pd.DataFrame(docs).to_csv(
        PUBLIC3 / "scanned_retirement_ocr_coverage.csv", index=False
    )
    write_json(
        PUBLIC3 / "retirement_ocr_summary.json",
        dict(
            scanned_confirmations=len(selected),
            attempted=len(docs),
            completed=sum(d["status"] == "OCR_COMPLETED_UNREVIEWED" for d in docs),
            code_link_candidates=len(f),
            candidate_securities=f.security_id.nunique() if len(f) else 0,
            promoted_to_verified_equity_links=0,
            independent_human_review=False,
            transform_sha256=version,
        ),
    )


if __name__ == "__main__":
    main()
