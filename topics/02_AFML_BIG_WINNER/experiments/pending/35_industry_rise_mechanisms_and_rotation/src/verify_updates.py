"""Check sealed replay bundles and locally reviewed public-document provenance."""
from common import *
import pandas as pd
from versioned_observations import verify_bundle


def run():
    receipt=json.loads((ROOT/'outputs/r18/replay_receipt.json').read_text())
    assert receipt['prospective_records']==0
    for row in receipt['runs']:
        bundle=Path(row['snapshot']); evaluation=Path(row['evaluation'])
        m=verify_bundle(bundle);verify_bundle(evaluation)
        assert sha(bundle/'manifest.json')==row['snapshot_sha256']
        assert m['capture_kind']=='historical_replay'
        obs=pd.read_parquet(bundle/'observations.parquet')
        outcomes=pd.read_parquet(evaluation/'outcomes.parquet')
        assert len(obs)==row['rows'] and obs.price_ready.sum()==row['ready']
        assert not obs.duplicated(KEY).any()
        assert not {'return20','excess20','maturity20','y','entry_date'} & set(obs)
        assert outcomes.evaluation_kind.eq('historical_replay').all()
        assert len(outcomes)==2*len(obs)
        assert outcomes.groupby(['horizon','status']).size().rename('rows').reset_index().to_dict('records')==row['statuses']
    review=json.loads((ROOT/'outputs/r19/review_receipt.json').read_text())
    assert sha(review['source_csv'])==review['source_csv_sha256']
    assert sha(ROOT/'outputs/r08/authorized_download_receipt.json')==review['download_receipt_sha256']
    assert sha(ROOT/'outputs/r19/reviewed_operating_observations.json')==review['reviewed_facts_sha256']
    facts=json.loads((ROOT/'outputs/r19/reviewed_operating_observations.json').read_text())
    assert len(facts)==13 and len({x['ts_code'] for x in facts})==5
    for fact in facts:
        assert sha(fact['pdf_path'])==fact['source_sha256']
        assert fact['review_status']=='PRIMARY_PDF_FACT_CHECKED_NOT_PIT_CERTIFIED'
    for image in review['images']:assert sha(image['path'])==image['sha256']
    js(ROOT/'outputs/r18/verification.json',dict(status='PASS',snapshots=2,prospective_records=0,
        public_documents=5,reviewed_facts=13,code_sha256=sha(__file__),
        limitation='integrity and replay verification; visual fact review separately recorded, not an automated semantic proof'))
    print('R18/R19 provenance and sealed bundles PASS')


if __name__=='__main__':run()
