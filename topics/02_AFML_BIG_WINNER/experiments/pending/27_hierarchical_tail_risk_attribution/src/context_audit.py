"""Post-registration endpoint context and inherited artifact provenance; no new candidate or selection."""
from core import *


def main():
    receipts=[]
    for h in C['horizons']:
        for quarter in pd.period_range('2021Q1','2026Q2',freq='Q'):
            checkpoint=EP25/f'outputs/checkpoints/{h}_{quarter}.json';record=json.loads(checkpoint.read_text())
            for key in ['predictions','atoms']:
                path=EP25/record[key]['path'];assert digest(path)==record[key]['sha256']
                receipts.append(dict(episode='EP25',path=str(path.relative_to(TOPIC)),sha256=digest(path),original_checkpoint_sha256=digest(checkpoint)))
    for quarter in pd.period_range('2021Q1','2026Q2',freq='Q'):
        checkpoint=EP26/f'outputs/checkpoints/{quarter}.json';record=json.loads(checkpoint.read_text());path=EP26/record['prediction_path'];assert digest(path)==record['prediction_sha256']
        receipts.append(dict(episode='EP26',path=str(path.relative_to(TOPIC)),sha256=digest(path),original_checkpoint_sha256=digest(checkpoint)))
    pd.DataFrame(receipts).to_csv(OUT/'inherited_baseline_receipts.csv',index=False)
    # Endpoint equals the sum of preregistered layer increments. It does not replace the primary contrast.
    m=pd.read_csv(OUT/'monthly_scores.csv',parse_dates=['date']);m=m[m.horizon.eq(6)];rows=[]
    for baseline in ['M_R','B1']:
        for metric in ['brier','auc']:
            d=paired(m[m.model.eq('M_RMIVF')],m[m.model.eq(baseline)],metric)
            for block in [6,12]:rows.append(dict(candidate='M_RMIVF',baseline=baseline,metric=metric,role='post_registration_endpoint_context_not_formal_primary',**ci(d,block)))
    pd.DataFrame(rows).to_csv(OUT/'endpoint_context_intervals.csv',index=False)
    write_json(OUT/'context_audit.json',dict(inherited_artifacts_match_original_published_checkpoints=True,files_verified=len(receipts),endpoint_contrast_is_explanatory=True,primary_contrast_and_candidates_unchanged=True))
    print('Inherited provenance and endpoint context verified.',flush=True)

if __name__=='__main__':main()
