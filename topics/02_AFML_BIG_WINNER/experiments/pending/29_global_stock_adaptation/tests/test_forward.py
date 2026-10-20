import json
import pandas as pd
import pytest
from forward import valid_origin,verify_archive,attach
from common import digest


def test_no_future_backfill_or_non_monthend():
    calendar=pd.to_datetime(['2026-10-29','2026-10-30','2026-11-02'])
    assert valid_origin('2026-10-30','2026-10-30 16:01',calendar)==pd.Timestamp('2026-10-30')
    for date,now in [('2026-10-30','2026-10-29 16:01'),('2026-10-30','2026-11-02 16:01'),
                     ('2026-10-30','2026-10-30 15:59'),('2026-10-29','2026-10-29 16:01')]:
        with pytest.raises(AssertionError):valid_origin(date,now,calendar)


def test_archive_detects_mutation_and_path_escape(tmp_path):
    data=tmp_path/'data.txt';data.write_text('original')
    manifest=tmp_path/'manifest.json';manifest.write_text(json.dumps({'files':{'data.txt':digest(data)}}))
    verify_archive(tmp_path);data.write_text('changed')
    with pytest.raises(AssertionError):verify_archive(tmp_path)
    manifest.write_text(json.dumps({'files':{'../data.txt':'bad'}}))
    with pytest.raises(AssertionError):verify_archive(tmp_path)


def test_labels_append_once_without_mutating_predictions(tmp_path):
    archive=tmp_path/'forecasts'/'2021-01-29';archive.mkdir(parents=True)
    pred=pd.DataFrame(dict(date=pd.to_datetime(['2021-01-29']),instrument=['A'],GPI=[.17]))
    p=archive/'M_R_predictions.parquet';pred.to_parquet(p,index=False);h=digest(p)
    (archive/'manifest.json').write_text(json.dumps(dict(ep28_manifest_sha256='shared',
        files={'M_R_predictions.parquet':h})))
    other=tmp_path/'ep28_labels';other.mkdir()
    y=pred[['date','instrument']].assign(actual=-.25,label_end=pd.Timestamp('2021-07-29'))
    path=other/'labels.parquet';y.to_parquet(path,index=False)
    (other/'receipt.json').write_text(json.dumps(dict(forecast_manifest_sha256='shared',labels_sha256=digest(path))))
    destination=tmp_path/'labels'/'2021-01-29'
    attach(archive,other,destination)
    assert digest(p)==h and digest(destination/'labels.parquet')==digest(path)
    with pytest.raises(FileExistsError):attach(archive,other,destination)
    y['label_end']=pd.Timestamp('2021-02-01');y.to_parquet(path,index=False)
    (other/'receipt.json').write_text(json.dumps(dict(forecast_manifest_sha256='shared',labels_sha256=digest(path))))
    with pytest.raises(AssertionError):attach(archive,other,tmp_path/'bad'/'2021-01-29')
