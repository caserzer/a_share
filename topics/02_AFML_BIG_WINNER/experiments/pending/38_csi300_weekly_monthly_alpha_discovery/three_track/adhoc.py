from constituent_audit import *
def main():
    gaps=pd.read_csv(OUT/'unexplained_changes.csv',dtype=str);rows=[]
    for month,g in gaps.groupby('month'):
        m=pd.Period(month,freq='M')
        p=dict(lang='cn',startDate=str((m.start_time-pd.Timedelta(days=31)).date()),endDate=str(m.end_time.date()),page=dict(key='',page=1,rows=100),classList=[],indexList=[],typeList=[],relatedTopics=[])
        z=requests.post(api+'queryAnnouncementByVo',json=p,timeout=20).json()
        assert z['total']<=100,(m,z['total'])
        for a in z['data']:
            if not re.search('沪深300|中证500|中证800|部分指数样本|指数样本临时调整|中证系列指数|证券代码变更',a['title']):continue
            doc=requests.get(api+'queryAnnouncementById',params={'id':a['id']},timeout=15).json()['data']
            txt=BeautifulSoup(doc['content'],'html.parser').get_text(' ',strip=True)
            (CACHE/f"adhoc_{a['id']}.json").write_text(json.dumps(doc,ensure_ascii=False))
            rows.append(dict(month=month,id=a['id'],title=a['title'],published=a['publishDate'],body=txt[:1500],matched=','.join(x for x in g.code if x in txt)))
    pd.DataFrame(rows).to_csv(OUT/'adhoc_notice_search.csv',index=False)
if __name__=='__main__':main()
