"""Verify original-universe catalog coverage before any forecast experiment."""
import json
from pathlib import Path
import pandas as pd
from prepare_panel import OUT
from build_joint_information import SOURCE
from build_margin_information import digest
from download_exchange_guidance_catalog import DEST,ALIAS


def load_catalog(exchanges=('SZ','SH')):
    records=[];manifests=[]
    for exchange in exchanges:
        path=DEST/f'{exchange}_manifest.json';manifest=json.loads(path.read_text())
        assert manifest['complete'] and manifest['source_panel_sha256']==digest(SOURCE)
        for window in manifest['windows']:
            file=Path(window['path']);assert digest(file)==window['sha256']
            payload=json.loads(file.read_text());assert payload['status']=='complete'
            for page in payload['pages']:assert digest(Path(page['path']))==page['sha256']
            assert len(payload['records'])==window['selected_documents']
            records.extend(payload['records'])
        manifests.append(dict(path=str(path),sha256=digest(path)))
        if exchange=='SZ':
            supplement_path=DEST/'SZ_supplement_manifest.json'
            supplement=json.loads(supplement_path.read_text());assert supplement['complete']
            assert supplement['base_sha256']==digest(path)
            for window in supplement['windows']:
                file=Path(window['path']);assert digest(file)==window['sha256']
                payload=json.loads(file.read_text());assert payload['status']=='complete'
                for page in payload['pages']:assert digest(Path(page['path']))==page['sha256']
                assert len(payload['records'])==window['documents']
                records.extend(payload['records'])
            manifests.append(dict(path=str(supplement_path),sha256=digest(supplement_path)))
    unique={}
    for record in records:
        identity=(record['exchange'],record['announcement_id'],record['url'])
        if identity in unique:
            # A title can match two public searches; merge only identical document metadata.
            for field in ('stocks','raw_codes','title','publish_date'):assert record[field]==unique[identity][field]
        else:unique[identity]=record
    return list(unique.values()),manifests


def run():
    records,manifests=load_catalog();panel=pd.read_parquet(SOURCE)
    universe=set(panel.instrument.unique());rows=[]
    for record in records:
        for code in record['stocks']:
            instrument=record['exchange']+code;assert instrument in universe
            rows.append(dict(record,instrument=instrument))
    frame=pd.DataFrame(rows);frame.to_parquet(DEST/'announcement_panel.parquet',index=False)
    count=frame.groupby('instrument').size()
    coverage=pd.DataFrame({'instrument':sorted(universe)})
    coverage['catalog_documents']=coverage.instrument.map(count).fillna(0).astype(int)
    coverage.to_csv(DEST/'stock_coverage.csv',index=False)
    frame.assign(year=frame.publish_date.str[:4]).groupby(['exchange','year']).size().rename('documents').to_csv(DEST/'annual_coverage.csv')
    official_ids={r['announcement_id'] for r in records if r['exchange']=='SZ'}
    comparison=[]
    for file in sorted((OUT/'local_cache/r37_guidance_catalog').glob('*.json')):
        payload=json.loads(file.read_text())
        for row in payload['announcements'] or []:
            code=ALIAS.get(row['secCode'],row['secCode'])
            if 'SZ'+code not in universe:continue
            # Compare the query's title scope; embedded/nonmatching documents are separate.
            eligible=any(term in row['announcementTitle'] for term in ('业绩预告','业绩预增','业绩预减','业绩预亏','业绩预盈'))
            comparison.append(dict(stock=code,announcement_id=str(row['announcementId']),title=row['announcementTitle'],
                                   in_title_scope=eligible,in_exchange_catalog=str(row['announcementId']) in official_ids,
                                   cninfo_page=str(file)))
    comparison=pd.DataFrame(comparison).drop_duplicates(['stock','announcement_id'])
    comparison.to_csv(DEST/'cninfo_overlap.csv',index=False)
    missing=comparison[comparison.in_title_scope & ~comparison.in_exchange_catalog]
    missing.to_csv(DEST/'cninfo_unmatched_in_scope.csv',index=False)
    summary=dict(source_manifests=manifests,original_stocks=len(universe),stocks_with_documents=int((coverage.catalog_documents>0).sum()),
                 selected_documents=len(records),stock_document_pairs=len(frame),
                 cninfo_cached_unique=len(comparison),cninfo_title_eligible=int(comparison.in_title_scope.sum()),
                 cninfo_title_eligible_missing=len(missing),
                 limitation='Completed query pagination does not certify all disclosure categories. Missing archive overlap must be reviewed before deriving zero-event features.')
    (DEST/'coverage_audit.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':run()
