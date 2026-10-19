"""Reparse complete cached originals with the final parser before model training."""
import gzip
import hashlib
import json
from pathlib import Path
import pandas as pd
from fetch_eps_reports import DEST, CACHE
from parse_eps_forecasts import parse_report

# Original text is internally inconsistent. Never guess a missing decimal point.
# These exclusions were established from source text without outcome labels.
SOURCE_EXCLUSIONS = {
    'AP202110141522607540': dict(field='forecasts',
        sha256='de2728d963d58191944469d68639044b3fd9083b9b9a85adff4fc180531669a3',
        reason='EPS sequence 2.13,249,2.86 contradicts the same sentence growth 8%,17%,15%; original HTML contains other corrupted numerals.'),
    'AP202409061639782662': dict(field='profit_forecasts',
        sha256='28d203f2d4e0323699b117710bbf9fc3739e891dee5a1e4dfdc07d9ee61c6040',
        reason='Profit sequence 201,30,35 contradicts same-current-market-cap PE sequence 18,12,10. Do not infer a replacement number.'),
}


def validate():
    original = pd.read_parquet(DEST/'full_extractions.parquet')
    selected = pd.read_parquet(DEST/'selected_reports.parquet')
    assert len(original) == len(selected) and not original.infoCode.duplicated().any()
    assert set(original.infoCode) == set(selected.infoCode)
    assert not original.status.eq('fetch_failed').any()
    rows = []
    for row in original.itertuples(index=False):
        raw = gzip.decompress((CACHE/f'{row.infoCode}.html.gz').read_bytes())
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == row.raw_sha256
        result = parse_report(raw.decode('utf-8'), row.publishDate, row.stockCode)
        exclusion = SOURCE_EXCLUSIONS.get(row.infoCode)
        if exclusion is not None:
            assert digest == exclusion['sha256'], 'Review exclusion against the changed original bytes'
            result[exclusion['field']] = {}
            result['status'] = 'parsed' if result.get('forecasts') else ('profit_only' if result.get('profit_forecasts') else 'source_inconsistent_forecast')
        rows.append(dict(infoCode=row.infoCode, stockCode=row.stockCode, publishDate=row.publishDate,
            **{k: v for k, v in result.items() if k not in ['forecasts', 'profit_forecasts']},
            forecasts=json.dumps(result.get('forecasts', {})), profit_forecasts=json.dumps(result.get('profit_forecasts', {})),
            raw_sha256=digest, source_exclusion=exclusion['reason'] if exclusion else None))
    validated = pd.DataFrame(rows)
    validated.to_parquet(DEST/'validated_extractions.parquet', index=False)
    audit = dict(reports=len(validated), statuses=validated.status.value_counts().to_dict(),
        parser_sha256=hashlib.sha256(Path(__file__).with_name('parse_eps_forecasts.py').read_bytes()).hexdigest(),
        original_extraction_sha256=hashlib.sha256((DEST/'full_extractions.parquet').read_bytes()).hexdigest(),
        source_exclusions=SOURCE_EXCLUSIONS,
        rule='Full cached-byte reparse after retrieval; no outcomes used; no inferred correction of corrupted numbers.')
    (DEST/'extraction_validation.json').write_text(json.dumps(audit, indent=2)+'\n')
    print(json.dumps(audit, indent=2), flush=True)
    return validated


if __name__ == '__main__':
    validate()
