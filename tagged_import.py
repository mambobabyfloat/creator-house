"""Tagged candidates ingestion contract for permitted external data sources.
Deliberately NO unauthorized scraping or provider endpoint assumptions.
"""
import re
from datetime import datetime, timezone
import pandas as pd

HANDLE = re.compile(r'^[A-Za-z0-9._]{1,30}$')
ALIASES = {
    'username': ['username','author_username','owner_username','creator_username','author','user','handle'],
    'evidence_url': ['evidence_url','post_url','permalink','url','post_permalink'],
    'followers': ['followers','followers_count','follower_count'],
    'following': ['following','follows_count','following_count'],
    'caption': ['caption','post_caption','text'],
    'post_date': ['post_date','timestamp','taken_at'],
}

def normalize_tagged(frame:pd.DataFrame, brand:str, provider='Tagged provider file'):
    """Extract user-supplied licensed tagged-post exports; preserve provenance.
    Multiple tagged posts for one creator are aggregated; uncertain fields remain blank.
    """
    if len(frame)>20000:
        raise ValueError('单次最多导入 20,000 行')
    lower={str(c).strip().lower():c for c in frame.columns}
    col={dst:next((lower[a] for a in aliases if a in lower),None) for dst,aliases in ALIASES.items()}
    if col['username'] is None:
        raise ValueError('缺少作者用户名列。请提供 author_username / username / owner_username。')
    if col['evidence_url'] is None:
        raise ValueError('缺少作品链接列。请提供 post_url / permalink / evidence_url。')
    rows=[]
    for _, r in frame.iterrows():
        name=str(r[col['username']]).strip().lstrip('@') if pd.notna(r[col['username']]) else ''
        if not HANDLE.fullmatch(name):continue
        url=str(r[col['evidence_url']]).strip() if pd.notna(r[col['evidence_url']]) else ''
        if not url.startswith(('https://www.instagram.com/p/','https://www.instagram.com/reel/','https://instagram.com/p/','https://instagram.com/reel/')):continue
        def val(key):
            c=col.get(key)
            return r[c] if c is not None and pd.notna(r[c]) else None
        rows.append({'username':name.lower(),'evidence_url':url, 'followers':val('followers'),'following':val('following'),
                     'post_date':val('post_date'),'caption':val('caption')})
    if not rows:return pd.DataFrame(),pd.DataFrame()
    evidence=pd.DataFrame(rows).drop_duplicates(subset=['username','evidence_url'])
    candidates=[]
    for name,group in evidence.groupby('username',sort=False):
        first=group.iloc[0]
        candidates.append({'username':name,'profile_url':f'https://www.instagram.com/{name}/',
            'followers':first['followers'],'following':first['following'],'brand_source':brand,
            'discovery_source':provider,'evidence_url':first['evidence_url'],
            'tagged_post_count':len(group),'checked_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'reviewer_note':'来自已获授权的 Tagged 数据文件；其余未提供字段待核验'})
    return pd.DataFrame(candidates),evidence
