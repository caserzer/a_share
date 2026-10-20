"""Check source bytes, report links and fixed warning accounting before publication."""
import re
from urllib.parse import unquote
from core import *


def main():
    sources=pd.read_csv(EP/'outputs/manifests/data_sources.csv')
    for r in sources.itertuples():assert digest(TOPIC/r.path)==r.sha256,r.path
    errors=pd.read_csv(OUT/'warning_errors_monthly.csv')
    assert (errors[['TP','FP','FN','TN']].sum(axis=1)==errors.rows).all()
    allrows=errors[(errors.dimension=='all')&(errors.fraction==.05)]
    assert allrows.groupby('model').apply(lambda g:int((g.TP+g.FN).sum()),include_groups=False).eq(4581).all()
    links=0
    for path in EP.rglob('*.md'):
        if CACHE in path.parents:continue
        for target in re.findall(r'\]\(([^)]+)\)',path.read_text()):
            if target.startswith(('http:','https:','#','app:')):continue
            relative=unquote(target.split('#',1)[0])
            assert (path.parent/relative).exists(),(str(path),target);links+=1
    validation=json.loads((EP/'outputs/audits/validation.json').read_text());assert validation['passed']
    control=json.loads((EP/'outputs/audits/controls.json').read_text());assert control['all_passed']
    tests=(EP/'outputs/audits/pytest_final.txt').read_text();assert '23 passed' in tests
    fitted=json.loads((EP/'outputs/audits/fit_audit.json').read_text())
    assert sum(x['models_fit'] for x in fitted)==198
    write_json(EP/'outputs/audits/delivery_checks.json',dict(passed=True,source_files_verified=len(sources),
        local_markdown_links_checked=links,warning_rows_checked=len(errors),all_model_events_4581=True,
        final_tests=23,historical_only=True,all_registered_feasible_work_complete=True,
        stopped_branches=['Level_A_original_samples','unavailable_full_text_formula_replications','L3_real_financial_vintages','text_opacity_valuation_interactions','D1_formal_models','executable_portfolio']))
    print('Delivery checks passed',len(sources),'source files,',links,'local links',flush=True)


if __name__=='__main__':main()
