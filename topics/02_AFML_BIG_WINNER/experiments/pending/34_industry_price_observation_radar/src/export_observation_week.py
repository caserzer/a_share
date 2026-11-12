"""Export any archived research week without running signals or reading labels."""
import argparse,json
from pathlib import Path
import pandas as pd
from audit_local_inputs import EP,sha


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--date');args=parser.parse_args()
    root=EP/'outputs/delivery_v1';manifestfile=root/'manifest.json';m=json.loads(manifestfile.read_text())
    source=root/'weekly_evidence_catalog.parquet';assert sha(source)==m['artifacts'][source.name]
    f=pd.read_parquet(source);date=pd.Timestamp(args.date or m['latest_complete_review']).normalize();f=f[f.date.eq(date)].sort_values(['era','industry_code'])
    if f.empty:raise ValueError('date is not an archived complete review; no substitute date used')
    out=root/'exports'/date.strftime('%Y%m%d');out.mkdir(parents=True,exist_ok=True)
    new=int(f.state.eq('NEW').sum());active=int(f.in_pool.sum());unknown=int(f.state.eq('DATA_INSUFFICIENT').sum())
    lines=[f'# EP34历史证据清单 · {date.date()}','','**R01规则未获验证；这是历史模拟清单，不是当前观察建议。**',
        f"归档价格截至 {m['source_data_asof']}，本页每行证据只截至 {date.date()}。规则 {m['rules_version']}，证据版本 {m['version']}，数据版本 {m['data_version']}。",
        f'完整目录 {len(f)} 个行业；本周新增 {new}，在池 {active}，数据不足 {unknown}。每周新增上限5已获用户确认，在池上限30仅为研究假设。','',
        '绝对收益与相对市场收益分别展示；相对收益是行业收益减同期中证全指收益。已有涨幅指提示时已知的过去收益，不使用事后过程起点。提示以来变化只使用首次提示至本页日期的完整同块路径。空值保持未知，不填零。','',
        '退出条件：20日收益≤0、首次提示满60交易日、连续两次复查数据不足或分类制度切换。一次缺失只暂停判断。订单、盈利及产业景气尚未检验；价格观察不等于买入。','',
        '|行业代码|行业|状态|仍在池|20日绝对|20日相对市场|首次提示|提示以来绝对|提示以来相对|状态依据|','|---|---|---|---|---:|---:|---|---:|---:|---|']
    def pct(x):return '未知' if pd.isna(x) else f'{x:.2%}'
    def txt(x):return str(x).replace('|','／').replace('\n',' ')
    for r in f.itertuples():
        first='—' if pd.isna(r.first_hint_date) else str(r.first_hint_date.date())
        since='—' if pd.isna(r.observation_id) else pct(r.since_first_hint_absolute)
        relative='—' if pd.isna(r.observation_id) else pct(r.since_first_hint_excess)
        lines.append(f'|{r.industry_code}|{txt(r.industry_name)}|{r.state_label}|{"是" if r.in_pool else "否"}|{pct(r.absolute_return_20)}|{pct(r.excess_return_20)}|{first}|{since}|{relative}|{txt(r.trigger_explanation)}|')
    lines+=['','每行完整5/20/60日证据、数据日期、唯一观察编号、未知标记及规则版本见同目录 catalog.json。事后过程身份与成熟结果单独保存在 retrospective_evaluation.parquet，不回填本页历史证据。']
    outputs={'catalog.md':'\n'.join(lines)+'\n','catalog.json':f.to_json(orient='records',date_format='iso',force_ascii=False,indent=2)+'\n'}
    for name,content in outputs.items():
        path=out/name
        if path.exists() and path.read_text()!=content:raise FileExistsError('export differs; use a new delivery version')
        path.write_text(content)
    receipt=dict(review_date=str(date.date()),catalog_rows=len(f),state_counts=f.state.value_counts().to_dict(),new=new,in_pool=active,data_insufficient=unknown,
                 source_manifest_sha256=sha(manifestfile),exporter_sha256=sha(Path(__file__)),artifacts={n:sha(out/n) for n in outputs})
    (out/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(receipt,ensure_ascii=False))


if __name__=='__main__':main()
