"""Optional Meta Graph API Business Discovery integration; no scraping or token storage."""
import re
import requests

USERNAME_RE = re.compile(r'^[A-Za-z0-9._]{1,30}$')


def discover(username, ig_user_id, access_token, version='v25.0'):
    username = username.strip().lstrip('@')
    if not USERNAME_RE.fullmatch(username):
        raise ValueError('Instagram 用户名格式不正确')
    if not re.fullmatch(r'\d{5,30}', str(ig_user_id).strip()):
        raise ValueError('请填写自己已授权的 Instagram 专业账号数字 ID')
    if not re.fullmatch(r'v\d+\.\d+', version):
        raise ValueError('Graph API 版本格式不正确')
    if not access_token.strip():
        raise ValueError('请填写有效的 Meta access token')
    fields = (f'business_discovery.username({username})'
              '{username,name,biography,followers_count,follows_count,media_count,'
              'media.limit(10){id,caption,media_type,permalink,timestamp}}')
    response = requests.get(
        f'https://graph.facebook.com/{version}/{ig_user_id}',
        params={'fields': fields, 'access_token': access_token.strip()},
        timeout=18,
    )
    try:
        payload = response.json()
    except ValueError:
        raise RuntimeError('Meta 返回了无法解析的响应')
    if not response.ok or 'error' in payload:
        err = payload.get('error', {})
        raise RuntimeError(f"Meta API 请求失败：{err.get('message', 'HTTP '+str(response.status_code))}")
    data = payload.get('business_discovery')
    if not data:
        raise RuntimeError('没有返回 Business Discovery 数据：检查专业账号类型及授权权限')
    return data


def to_candidate(info, brand, source='Business Discovery'):
    media = info.get('media', {}).get('data', [])
    dates = [x.get('timestamp') for x in media if x.get('timestamp')]
    return {
        'username': info.get('username'), 'followers': info.get('followers_count'),
        'following': info.get('follows_count'), 'country': None,
        'child_age_months': None, 'baby_posts_last10': None,
        'ugc': None, 'days_since_post': None, 'public': None,
        'profile_url': f"https://www.instagram.com/{info.get('username', '')}/",
        'notes': (info.get('biography') or '')[:600],
        'brand_source': brand, 'discovery_source': source,
        'evidence_url': media[0].get('permalink') if media else None,
        'checked_at': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(timespec='seconds'),
        'recent_post_dates': '; '.join(dates[:10]),
        'reviewer_note': '',
    }
