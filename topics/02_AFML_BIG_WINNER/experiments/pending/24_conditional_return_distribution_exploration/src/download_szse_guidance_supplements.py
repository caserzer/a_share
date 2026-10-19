"""Known title variants found in the independent archived-category overlap."""
import json
from download_exchange_guidance_catalog import DEST,START,END,fetch_window
from build_margin_information import digest


def run():
    base=DEST/'SZ_manifest.json';manifest=json.loads(base.read_text());assert manifest['complete']
    output=dict(base_manifest=str(base),base_sha256=digest(base),windows=[],complete=False)
    path=DEST/'SZ_supplement_manifest.json'
    for title in ('业绩预增','业绩预减','业绩预亏','业绩预盈'):
        try:
            result=fetch_window('SZ',START,END,manifest['stock_codes'],title_query=title)
            file=DEST/f'SZ_supplement_{title}.json';file.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
            output['windows'].append(dict(title_query=title,status='complete',path=str(file),sha256=digest(file),documents=len(result['records'])))
            print(title,len(result['records']),flush=True)
        except Exception as error:
            output['windows'].append(dict(title_query=title,status='failed',error=repr(error)))
            path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n');raise
        path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    output['complete']=True;path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':run()
