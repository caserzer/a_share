"""Conservative extraction of explicitly dated EPS levels from original report prose.

No guessing of years from today's date, no extraction from current quote widgets,
and no silently resolving conflicting forecasts inside a report.
"""
import re
import unicodedata
from bs4 import BeautifulSoup

YEAR_SPAN = re.compile(r'(?<!\d)20\d{2}(?:年)?(?:[-~至/、,及和](?:20)?\d{2}(?:年)?){1,3}')
SHORT_YEAR_SPAN = re.compile(r'(?<!\d)\d{2}(?:年)?(?:[-~至/、,及和]\d{2}(?:年)?){1,3}年')
INDICATOR = re.compile(r'EPS|每股收益', re.I)
NUMBER = r'-?\d+(?:\.\d+)?'
VALUES = re.compile(r'^\)?(?:\(元\))?(?:预测)?(?:预计)?(?:分别)?(?:约)?(?:为|至|是|达到|提升至|:)?'
                    r'(?P<values>' + NUMBER + r'(?:元)?(?:[/、,及和]' + NUMBER + r'(?:元)?){1,3})')
PROFIT_INDICATOR=re.compile(r'归母净利润|归属于母公司(?:股东)?(?:的)?净利润|归属母公司(?:股东)?(?:的)?净利润')
UNIT=r'(?:亿元|百万元|千万元|万元|亿|万|元)'
PROFIT_VALUES=re.compile(r'^(?:分别)?(?:约)?(?:为|达|达到|预计为|:)?(?P<values>'+NUMBER+UNIT+r'?(?:[/、,及和]'+NUMBER+UNIT+r'?){1,3})')
MULTIPLIER={'亿元':1e8,'亿':1e8,'千万元':1e7,'百万元':1e6,'万元':1e4,'万':1e4,'元':1.}


def normalize(text):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', text)).replace('—','-').replace('–','-').replace('～','~')


def parse_years(span):
    raw = re.findall(r'20\d{2}|(?<!\d)\d{2}(?!\d)', span)
    years = [int(y) if len(y)==4 else 2000+int(y) for y in raw]
    if len(years)==2 and re.search(r'[-~至]',span):
        if 1 <= years[1]-years[0] <= 3:
            years = list(range(years[0],years[1]+1))
        else:
            return []
    if not 2 <= len(years) <= 4 or years != sorted(set(years)):
        return []
    return years


def bound_years(prefix, published_year):
    spans = sorted(list(YEAR_SPAN.finditer(prefix))+list(SHORT_YEAR_SPAN.finditer(prefix)),key=lambda x:(x.end(),-x.start()))
    if not spans:
        return []
    last = spans[-1]
    tail = prefix[last.end():]
    # A later single fiscal year replaces the earlier range. Mixed annual/quarter
    # historical observations must not become a pair of annual forecasts.
    if re.search(r'(?<!\d)(?:20\d{2}|\d{2})年|季度|半年|[一二三四]季|Q[1-4]|H[12]', tail, re.I):
        return []
    years = parse_years(last.group())
    if not years or min(years)<published_year-1 or max(years)>published_year+4:
        return []
    return years


def parse_paragraph(text, published_year):
    text = normalize(text)
    pairs = []
    for marker in INDICATOR.finditer(text):
        prefix = text[max(0,marker.start()-450):marker.start()]
        years = bound_years(prefix, published_year)
        if not years:
            continue
        match = VALUES.match(text[marker.end():])
        if not match:
            continue
        following = text[marker.end()+match.end():]
        if following.startswith('%') or re.match(r'^[/、,及和]-?\d',following):
            continue
        numbers = [float(x) for x in re.findall(NUMBER,match.group('values'))]
        # Do not consume a following calendar year as another value after 元.
        if '元' in match.group('values') and not match.group('values').endswith('元'):
            continue
        if len(numbers)!=len(years) or any(abs(x)>1000 for x in numbers):
            continue
        pairs.append(dict(zip(years,numbers)))
    return pairs


def parse_profit_paragraph(text,published_year):
    text=normalize(text);pairs=[]
    for marker in PROFIT_INDICATOR.finditer(text):
        if any(word in text[max(0,marker.start()-50):marker.start()] for word in ['扣非','扣除非经常','不考虑','剔除','考核','业绩承诺']):
            continue
        prefix=text[max(0,marker.start()-450):marker.start()]
        years=bound_years(prefix,published_year)
        if not years:continue
        match=PROFIT_VALUES.match(text[marker.end():])
        if not match:continue
        following=text[marker.end()+match.end():]
        if following.startswith('%') or re.match(r'^[/、,及和]-?\d',following):continue
        values=re.findall(NUMBER,match.group('values'));units=re.findall(UNIT,match.group('values'))
        # No implicit currency units or mixing of differently stated units.
        if len(values)!=len(years) or len(set(units))!=1 or not re.search(UNIT+r'$',match.group('values')):continue
        scale=MULTIPLIER[units[0]]
        pairs.append(dict(zip(years,[float(v)*scale for v in values])))
    return pairs


def consolidate(candidates):
    result={}
    for candidate in candidates:
        for year,value in candidate.items():
            if year in result and abs(result[year]-value)>1e-8:
                return {},True
            result[year]=value
    return result,False


def parse_report(html, published_date, expected_stock=None):
    soup = BeautifulSoup(html,'html.parser')
    body = soup.select_one('#ctx-content')
    if body is None:
        return dict(status='no_original_body',forecasts={})
    if expected_stock is not None:
        securities=set(re.findall(r'"stock"\s*:\s*"(\d{6})"',str(html)))
        if securities!={expected_stock}:
            return dict(status='security_mismatch_or_multiple',forecasts={})
    declared = set(re.findall(r'"notice_date"\s*:\s*"(\d{4}-\d{2}-\d{2})', str(html)))
    if len(declared)!=1:
        return dict(status='missing_or_ambiguous_publication_date',forecasts={})
    source_date = next(iter(declared))
    available = max(str(published_date)[:10],source_date)
    if body.get_text(' ',strip=True) in {'','暂无内容','暂无数据'}:
        return dict(status='empty_original_body',forecasts={},profit_forecasts={},source_date=source_date,available_date=available)
    candidates = [];profits=[]
    for p in body.find_all('p'):
        text=p.get_text(' ',strip=True)
        candidates.extend(parse_paragraph(text,int(source_date[:4])))
        profits.extend(parse_profit_paragraph(text,int(source_date[:4])))
    forecasts,eps_conflict=consolidate(candidates)
    profit_forecasts,profit_conflict=consolidate(profits)
    status='parsed' if forecasts else ('conflicting_forecasts' if eps_conflict else ('profit_only' if profit_forecasts else 'no_explicit_earnings'))
    return dict(status=status,forecasts=forecasts,profit_forecasts=profit_forecasts,
                eps_conflict=eps_conflict,profit_conflict=profit_conflict,
                source_date=source_date,available_date=available,matched_spans=len(candidates),profit_spans=len(profits))
