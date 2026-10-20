"""SocialCrawl Tagged API adapter. Never logs or persists API keys."""
import re
import requests
import pandas as pd

BASE = 'https://www.socialcrawl.dev/v1/instagram/tagged'


def parse_response(payload, brand):
    if not isinstance(payload, dict) or payload.get('success') is not True:
        raise ValueError('SocialCrawl did not return a successful JSON response')
    if payload.get('endpoint') != '/v1/instagram/tagged':
        raise ValueError('JSON is not an Instagram Tagged response')
    records=[]
    for item in payload.get('data', {}).get('items', []):
        post=item.get('post') or {}
        author=post.get('author') or {}
        name=(author.get('username') or '').strip().lstrip('@').lower()
        if not re.fullmatch(r'[a-z0-9._]{1,30}',name):
            continue
        content=post.get('content') or {}
        records.append({'username':name,'post_url':post.get('url') or '',
                        'caption':content.get('text') or '',
                        'timestamp':post.get('published_at') or '',
                        'brand_source':brand,
                        'profile_url':f'https://www.instagram.com/{name}/'})
    posts=pd.DataFrame(records,columns=['username','post_url','caption','timestamp','brand_source','profile_url'])
    if posts.empty:
        candidates=pd.DataFrame(columns=['username','profile_url','brand_source','discovery_source','evidence_url','tagged_post_count'])
    else:
        posts=posts.drop_duplicates(subset=['post_url','username'])
        candidates=posts.groupby('username',as_index=False).agg(profile_url=('profile_url','first'),brand_source=('brand_source','first'),evidence_url=('post_url','first'),tagged_post_count=('post_url','count'))
        candidates['discovery_source']='Tagged · SocialCrawl'
    page=payload.get('pagination') or {}
    return candidates,posts,{'cursor':page.get('next_cursor') or (payload.get('data') or {}).get('next_cursor'),
                             'has_more':bool(page.get('has_more')),
                             'credits_used':payload.get('credits_used'),
                             'credits_remaining':payload.get('credits_remaining'),
                             'total_estimate':(payload.get('data') or {}).get('total')}


def fetch_page(handle,key,cursor=None):
    handle=handle.strip().lstrip('@')
    if not re.fullmatch(r'[A-Za-z0-9._]{1,30}',handle):
        raise ValueError('Invalid Instagram handle')
    if not key.strip():
        raise ValueError('Configure SOCIALCRAWL_API_KEY in Streamlit Secrets')
    params={'handle':handle}
    if cursor:params['cursor']=cursor
    response=requests.get(BASE,params=params,headers={'x-api-key':key.strip()},timeout=40)
    response.raise_for_status()
    return response.json()
