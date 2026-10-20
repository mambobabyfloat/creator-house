"""One-click bounded, cost-aware discovery and screening. No credentials are logged."""
import json, re, datetime
from urllib.parse import urlparse
import requests
from socialcrawl import parse_response

ROOT='https://www.socialcrawl.dev/v1/instagram'
HEADERS=lambda key:{'x-api-key':key.strip()}
US={'us','usa','united states','united states of america','美国'}

def api_get(path,handle,key,**params):
    response=requests.get(f'{ROOT}/{path}',params={'handle':handle,**params},headers=HEADERS(key),timeout=45)
    response.raise_for_status()
    data=response.json()
    if not data.get('success'):
        raise ValueError((data.get('error') or {}).get('message','API did not return success'))
    return data

def profile(payload,handle):
    data=payload.get('data') or {}
    a=data.get('author') or data.get('profile') or (data if 'followers' in data else {})
    if not isinstance(a,dict) or not a:
        raise ValueError('Profile author missing')
    ext=a.get('ext') or {}
    country=ext.get('country') or a.get('country') or ''
    return {'username':handle,'followers':a.get('followers'),'following':a.get('following'),
            'bio':a.get('bio') or '', 'country':country,
            'public':None if a.get('private') is None else not a.get('private'),
            'profile_url':a.get('url') or f'https://www.instagram.com/{handle}/',
            'credits_profile':payload.get('credits_used',1)}

def posts(payload):
    raw=(payload.get('data') or {}).get('items') or []
    result=[]
    for item in raw[:10]:
        p=item.get('post',item)
        if not isinstance(p,dict):continue
        content=p.get('content') or {}
        media=content.get('media_urls') or []
        image=next((x for x in media if isinstance(x,str) and x.startswith('https://') and 'instagram' in urlparse(x).hostname.lower()),None) if media else None
        result.append({'url':p.get('url') or '', 'text':content.get('text') or '',
                       'date':p.get('published_at') or '', 'image':image})
    return result

def screen(record,settings):
    errors=[]; uncertain=[]; evidence=[]
    followers=record.get('followers');following=record.get('following')
    if followers is None:uncertain.append('粉丝数未知')
    elif not settings['min_followers']<=followers<=settings['max_followers']:errors.append('粉丝数量不符')
    if following is None:uncertain.append('关注数未知')
    elif followers is not None and settings['strict_ratio'] and following>followers:errors.append('关注数超过粉丝数')
    if record.get('public') is False: errors.append('私密账号')
    elif record.get('public') is None:uncertain.append('主页公开状态未知')
    country=str(record.get('country') or '').strip().lower()
    ai=record.get('analysis') or {}
    confirmed_country=country or str(ai.get('country_evidence') or '').strip().lower()
    if settings['us_only']:
        if not confirmed_country:uncertain.append('美国本土缺少证据')
        elif confirmed_country not in US:errors.append('明确不在美国')
    recents=record.get('posts') or []
    if recents:
        try:
            date=datetime.datetime.fromisoformat((recents[0].get('date') or '').replace('Z','+00:00'))
            if (datetime.datetime.now(datetime.timezone.utc)-date).days>90:errors.append('超过90天没有更新')
        except ValueError:uncertain.append('最近活跃日期无法核实')
    else:uncertain.append('没有近期内容')
    if ai:
        age=ai.get('child_age_months')
        if isinstance(age,(int,float)) and ai.get('age_evidence'):
            lo,hi={'Guard':(6,24),'Float':(3,24),'Rider':(60,120)}[settings['product']]
            if lo<=age<=hi:evidence.append('孩子年龄有公开文字证据')
            else:errors.append('孩子年龄不符合')
        else:uncertain.append('孩子年龄缺少明确证据')
        baby=ai.get('baby_posts_last10')
        if len(recents)<10:uncertain.append('少于10条近期帖子，出镜频率样本不足')
        if isinstance(baby,int):
            if baby<3 and len(recents)>=10:errors.append('最近10条宝宝出镜不足3条')
            elif baby>=3:evidence.append('近期宝宝出镜频率达到3条')
            else:uncertain.append('宝宝出镜不足以判断')
        else:uncertain.append('宝宝出镜频率待核实')
        if ai.get('ugc') is False:errors.append('非UGC母婴账号')
        elif ai.get('ugc') is not True:uncertain.append('UGC 类型待核实')
    else:uncertain.extend(['孩子年龄未分析','宝宝出镜频率未分析','UGC类型未分析'])
    if not confirmed_country and settings['us_only'] and '美国本土缺少证据' not in uncertain: uncertain.append('美国本土缺少证据')
    record['status']='排除' if errors else ('待复核' if uncertain else '符合')
    record['reasons']='；'.join(errors or uncertain or evidence)
    return record

def analyze_ai(bio,post_items,api_key):
    """Optional multimodal AI review, never infers child age from appearance or guessed location."""
    if not api_key:return {}
    post_items=post_items[:10]
    blocks=[{'type':'input_text','text':(
        'Analyze a PUBLIC Instagram creator for US baby UGC collaboration. Return ONLY JSON with keys '
        'child_age_months (number or null), age_evidence (exact public text or empty string), '
        'baby_posts_last10 (integer or null), ugc (true/false/null), '
        'country_evidence (only exact country code US when text EXPLICITLY states US; else empty string), '
        'reason (short Chinese). Do not infer child age from appearance or country from language. '
        'For baby_posts_last10, count visible baby posts using images and captions, set null when not enough clear information. '
        'For ugc, distinguish genuine parent/family content from stores/retailers. '
        f'BIO: {bio[:1500]}\nPOSTS: '+json.dumps([{'index':i+1,'caption':p['text'][:700],'url':p['url']} for i,p in enumerate(post_items)],ensure_ascii=False))}]
    for i,p in enumerate(post_items):
        if p.get('image'):
            blocks.append({'type':'input_text','text':f'Post {i+1} image:'})
            blocks.append({'type':'input_image','image_url':p['image'],'detail':'low'})
    r=requests.post('https://api.openai.com/v1/responses',headers={'Authorization':f'Bearer {api_key.strip()}','Content-Type':'application/json'},
                    json={'model':'gpt-4.1-mini','input':[{'role':'user','content':blocks}],'max_output_tokens':500},timeout=90)
    r.raise_for_status();payload=r.json()
    content=''.join(chunk.get('text','') for part in payload.get('output',[]) for chunk in part.get('content',[]) if chunk.get('type')=='output_text').strip()
    content=re.sub(r'^```(?:json)?\s*|\s*```$','',content).strip()
    obj=json.loads(content)
    if not isinstance(obj,dict):raise ValueError('AI response was not JSON object')
    return obj

def run_pipeline(brand,key,settings,max_creators=10,pages=1,openai_key='',progress=None,candidate_payload=None):
    """Returns records, budget audit, errors; explicitly bounded. No auto retries."""
    items=[]; total_credits=0; errors=[]
    if candidate_payload is not None:
        c,_,meta=parse_response(candidate_payload,brand)
        items=c.to_dict('records');page_count=0
    else:
        cursor=None;page_count=0
        for i in range(pages):
            try:
                payload=api_get('tagged',brand,key,**({'cursor':cursor} if cursor else {}))
                total_credits+=payload.get('credits_used') or 0
                c,_,meta=parse_response(payload,brand)
                items.extend(c.to_dict('records'))
                page_count+=1
                cursor=meta['cursor'] if meta['has_more'] else None
                if not cursor:break
            except Exception as e:
                errors.append(f'Tagged 第{i+1}页失败：{str(e)[:160]}');break
    dedup={v['username']:v for v in items}
    selected=list(dedup.values())[:max_creators]
    out=[]
    for i,rec in enumerate(selected):
        name=rec['username'];record=dict(rec);record['posts']=[]
        try:
            response=api_get('profile',name,key)
            total_credits+=response.get('credits_used') or 0
            record.update(profile(response,name))
            basic=screen(dict(record),settings)
            if basic['status']!='排除':
                response=api_get('profile/posts',name,key)
                total_credits+=response.get('credits_used') or 0
                record['posts']=posts(response)
                if openai_key:
                    try:record['analysis']=analyze_ai(record.get('bio',''),record['posts'],openai_key)
                    except Exception as ex:record['ai_error']=str(ex)[:160]
        except Exception as ex:record['fetch_error']=str(ex)[:160]
        out.append(screen(record,settings))
        if progress: progress(i+1,len(selected),name)
    return out,{'tagged_pages':page_count,'unique_discovered':len(dedup),'analyzed':len(selected),'socialcrawl_credits_reported':total_credits,'errors':errors}
