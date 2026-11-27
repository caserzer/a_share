"""Test whether report_rc can retrieve a fiscal-quarter-specific historical comparison set."""
from fetch_sources import *
def main():
    meta=[]
    for q in ['2024Q1','2024Q2','2024Q3']:
        rec=query('report_rc',{'quarter':q,'start_date':'20230101','end_date':'20240930','limit':3000},'ts_code,report_date,org_name,quarter,eps,np')
        g=get_frame(rec)
        if len(g):g.to_parquet(HERE/'results'/('report_rc_'+q+'.parquet'),index=False)
        meta.append({'requested_period':q,'code':rec['code'],'message':rec['message'],'rows':len(g),'match':int((g.get('quarter',pd.Series(dtype=str))==q).sum()),'returned':dict(g.quarter.value_counts()) if len(g) else {},'sha256':rec['sha256']})
        (HERE/'results'/'report_rc_period_probe.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2,default=int))
        time.sleep(61) if q!='2024Q3' else None
if __name__=='__main__':main()
