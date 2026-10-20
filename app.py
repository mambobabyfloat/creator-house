import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime, timezone
from graph_api import discover, to_candidate
from storage import save as save_cloud, load as load_cloud
from security import require_login, secret
from tagged_import import normalize_tagged
from socialcrawl import parse_response, fetch_page

st.set_page_config(page_title='Mambo Creator Finder',page_icon='🟡',layout='wide')
st.markdown('''<style>.stApp{background:#F8F7F0;color:#35312d}h1,h2,h3{font-family:Arial,sans-serif}.stButton button[kind="primary"]{background:#F3D54E;color:#24211b;border:none}</style>''',unsafe_allow_html=True)
require_login()
DATABASE_URL=secret('DATABASE_URL')
st.title('🟡 Mambo Creator Finder · Cloud')
st.caption('在线工作区 · Tagged 数据接入 · Meta 查询 · 严格过滤 · 可追溯的候选人名单')
if not DATABASE_URL: st.warning('尚未配置云数据库 DATABASE_URL；本次修改仅保留在浏览器会话中，请务必及时导出。')

with st.sidebar:
 st.header('竞品来源')
 brand=st.text_input('品牌 Instagram 用户名',value='theofficialbibs').strip().lstrip('@')
 source=st.selectbox('候选账号来源',['Tagged','Followers','Following','Mentions','其他'])
 st.markdown(f'[打开品牌主页](https://www.instagram.com/{brand}/)')
 st.info('Instagram 未连接授权数据源时，本工具不会自动读取品牌的 Tagged、Followers 或 Following。请导入合法获取的数据。')
 st.header('筛选规则')
 product=st.selectbox('产品线',['Guard','Float','Rider'])
 min_followers=st.number_input('最低粉丝数',min_value=0,value=1000,step=500)
 max_followers=st.number_input('最高粉丝数',min_value=100,value=20000,step=1000)
 strict_ratio=st.checkbox('关注数不得大于粉丝数',value=True)
 us_only=st.checkbox('仅美国本土',value=True)
 active_only=st.checkbox('最近 90 天活跃',value=True)
 baby_min,baby_max={'Guard':(6,24),'Float':(3,24),'Rider':(60,120)}[product]
 st.caption(f'{product} 目标孩子年龄：{baby_min}–{baby_max} 个月')

st.subheader('1 · 获取或导入候选数据')
with st.expander('🔌 Meta Business Discovery · 连接官方 API（可选）', expanded=False):
 st.caption('需要你的 Meta 应用权限、已授权的 Instagram 专业账号 ID 和访问令牌。令牌只用于本次 API 请求，不写入数据库或 Excel。')
 graph_id = st.text_input('已授权的 Instagram 专业账号 ID', value=secret('META_IG_USER_ID'), placeholder='数字 ID')
 graph_token = st.text_input('Meta Access Token（建议在 Secrets 中配置）', value=secret('META_ACCESS_TOKEN'), type='password')
 graph_version = st.text_input('Graph API 版本', value='v25.0')
 fetch_name = st.text_input('要读取的 Business / Creator 账号', value=brand)
 if st.button('从 Meta API 读取该账号', type='primary'):
  try:
   info = discover(fetch_name, graph_id, graph_token, graph_version)
   st.session_state['meta_result'] = to_candidate(info, brand)
   st.session_state['meta_posts'] = info.get('media', {}).get('data', [])
   st.success(f"读取成功：@{info.get('username')}，近期帖子 {len(st.session_state['meta_posts'])} 条。宝宝年龄、地区、UGC 需另外核实。")
  except Exception as error:
   st.error(str(error))
 if 'meta_posts' in st.session_state:
  st.dataframe(pd.DataFrame(st.session_state['meta_posts'])[['permalink','caption','timestamp']] if st.session_state['meta_posts'] else pd.DataFrame(), use_container_width=True, hide_index=True)
 st.caption('此接口读取单个符合条件的专业账号，不枚举品牌的 Followers/Following/Tagged 用户。')
with st.expander('📋 从 Instagram 链接批量创建待核查候选人', expanded=False):
 raw_urls=st.text_area('每行一个 @用户名或 instagram.com/username 链接',height=110,placeholder='@creator_one\nhttps://www.instagram.com/creator_two/')
 if st.button('添加这些账号'):
  import re
  names=[]
  for line in raw_urls.splitlines():
   match=re.match(r'^(?:https?://(?:www\.)?instagram\.com/)?@?([A-Za-z0-9._]{1,30})/?(?:\?.*)?$',line.strip())
   if match and match.group(1).lower() not in ('p','reel','stories','explore'):
    names.append(match.group(1))
  if names:
   st.session_state['url_candidates']=[{'username':n,'profile_url':f'https://www.instagram.com/{n}/','brand_source':brand,'discovery_source':source} for n in dict.fromkeys(names)]
   st.success(f'已解析 {len(st.session_state["url_candidates"])} 个账号；仅提取用户名，尚未检验主页信息。')
  else:st.warning('没有识别到有效 Instagram 账号链接')

st.subheader('2 · SocialCrawl Tagged 自动发现（新）')
st.caption('每次点击“读取一页”会触发一次付费额度请求，通常为 5 Credits；不会自动翻页或批量扣费。先用下面的 JSON 文件验证免费结果。')
api_key=secret('SOCIALCRAWL_API_KEY')
with st.expander('🔌 SocialCrawl 自动读取或导入原始 JSON',expanded=True):
 json_file=st.file_uploader('上传 SocialCrawl Download JSON 文件（零 API 消耗）',type=['json'],key='socialcrawl_json')
 if json_file is not None:
  try:
   import json
   raw=json.load(json_file)
   candidates,posts,info=parse_response(raw,brand)
   st.session_state['socialcrawl_candidates']=candidates.to_dict('records')
   st.session_state['socialcrawl_posts']=posts
   st.session_state['socialcrawl_cursor']=info['cursor'] if info['has_more'] else None
   st.success(f'JSON 解析成功：{len(posts)} 条 Tagged 作品，{len(candidates)} 个不同作者，消耗 0 Credits。')
  except Exception as e: st.error(f'JSON 格式不符合预期：{e}')
 st.caption('线上自动获取需要在 Streamlit Cloud → Settings → Secrets 添加 SOCIALCRAWL_API_KEY。请勿在聊天或 GitHub 中公开密钥。')
 if not api_key:st.info('尚未配置 SOCIALCRAWL_API_KEY；仍可使用 JSON 上传功能。')
 col1,col2=st.columns(2)
 with col1:
  if st.button('读取一页 Tagged（消耗约 5 Credits）',disabled=not bool(api_key)):
   try:
    raw=fetch_page(brand,api_key)
    candidates,posts,info=parse_response(raw,brand)
    st.session_state['socialcrawl_candidates']=candidates.to_dict('records')
    st.session_state['socialcrawl_posts']=posts
    st.session_state['socialcrawl_cursor']=info['cursor'] if info['has_more'] else None
    st.success(f'取得 {len(posts)} 条作品 / {len(candidates)} 位作者。实际消耗：{info["credits_used"]} Credits；余额 {info["credits_remaining"]}。')
   except Exception as e: st.error(f'读取失败：{e}')
 with col2:
  if st.button('读取下一页（再次消耗额度）',disabled=not bool(api_key and st.session_state.get('socialcrawl_cursor'))):
   try:
    raw=fetch_page(brand,api_key,st.session_state['socialcrawl_cursor'])
    candidates,posts,info=parse_response(raw,brand)
    old=st.session_state.get('socialcrawl_posts',pd.DataFrame())
    combined=pd.concat([old,posts],ignore_index=True).drop_duplicates(subset=['username','post_url'])
    st.session_state['socialcrawl_posts']=combined
    # Rebuild candidates after pagination without losing first evidence URL.
    grouped=combined.groupby('username',as_index=False).agg(profile_url=('profile_url','first'),brand_source=('brand_source','first'),evidence_url=('post_url','first'),tagged_post_count=('post_url','count'))
    grouped['discovery_source']='Tagged · SocialCrawl'
    st.session_state['socialcrawl_candidates']=grouped.to_dict('records')
    st.session_state['socialcrawl_cursor']=info['cursor'] if info['has_more'] else None
    st.success(f'目前累计 {len(combined)} 条作品 / {len(grouped)} 位作者。本次消耗 {info["credits_used"]} Credits。')
   except Exception as e:st.error(f'下一页读取失败：{e}')
 if 'socialcrawl_posts' in st.session_state:
  sp=st.session_state['socialcrawl_posts']
  st.dataframe(sp[['username','post_url','caption','timestamp']].head(100),hide_index=True,use_container_width=True)
  st.download_button('下载已发现的 Tagged 作者 CSV',pd.DataFrame(st.session_state.get('socialcrawl_candidates',[])).to_csv(index=False).encode('utf-8-sig'),'socialcrawl_discovered_creators.csv','text/csv')
  st.warning('注意：Tagged 结果不含作者粉丝数、关注数、美国所在地、宝宝年龄以及主页最近 10 条宝宝出镜次数；这些账号全部先标记为待复核。')

st.subheader('2 · Tagged 数据提供商导入')
st.info('此模块接受你有权使用的数据供应商导出的 Tagged 作品 CSV / XLSX。不是 Instagram 无授权爬虫；没有接入或配置供应商 API 时，不会自动声称找到红人。')
tagged_file=st.file_uploader('上传已授权的 Tagged 作品导出文件',type=['csv','xlsx'],key='tagged_upload')
if tagged_file is not None:
 try:
  tagged_raw=pd.read_csv(tagged_file) if tagged_file.name.endswith('.csv') else pd.read_excel(tagged_file)
  candidates, evidence=normalize_tagged(tagged_raw,brand,provider='Licensed Tagged export')
  st.write(f'识别到 {len(candidates)} 个作者，{len(evidence)} 条带作品链接的 Tagged 记录')
  if len(candidates):
   st.dataframe(evidence.head(50),hide_index=True,use_container_width=True)
   if st.button('将 Tagged 作者加入候选池'):
    st.session_state['tagged_candidates']=candidates.to_dict('records')
    st.success(f'已添加 {len(candidates)} 位待核查候选人')
  else:st.warning('没有找到符合格式的 Instagram 帖子链接和作者用户名')
 except Exception as error:st.error(f'导入 Tagged 作品失败：{error}')
st.download_button('下载 Tagged 数据对接模板',pd.DataFrame([{'author_username':'example_creator','post_url':'https://www.instagram.com/p/POST_ID/','caption':'Example only','timestamp':'2026-10-01'}]).iloc[:0].to_csv(index=False).encode('utf-8-sig'),'tagged_provider_template.csv','text/csv')
st.caption('预留第三方自动接入字段：author_username、post_url、caption、timestamp、followers_count、follows_count。先审核提供商能否合法提供这些字段，再按其实际 API 开发连接器。')

st.write('支持 CSV 或 Excel。建议包含以下字段：username, followers, following, country, child_age_months, baby_posts_last10, ugc, days_since_post, public, profile_url, notes。未知字段请留空，系统会标记为待复核，不会当成符合。')
columns=['username','followers','following','country','child_age_months','baby_posts_last10','ugc','days_since_post','public','profile_url','notes','brand_source','discovery_source','evidence_url','checked_at','recent_post_dates','reviewer_note','tagged_post_count']
example=pd.DataFrame([{'username':'example_mom_1','followers':8500,'following':1200,'country':'US','child_age_months':11,'baby_posts_last10':6,'ugc':'yes','days_since_post':4,'public':'yes','profile_url':'https://www.instagram.com/example_mom_1/','notes':'示例虚构账号，不代表真实红人'},{'username':'example_mom_2','followers':4200,'following':7700,'country':'US','child_age_months':9,'baby_posts_last10':7,'ugc':'yes','days_since_post':2,'public':'yes','profile_url':'https://www.instagram.com/example_mom_2/','notes':'示例虚构账号，不代表真实红人'}])
st.download_button('下载 CSV 填写模板',example.iloc[0:0].to_csv(index=False).encode('utf-8-sig'),'mambo_creator_template.csv','text/csv')
file=st.file_uploader('上传候选账号 CSV / XLSX',type=['csv','xlsx'])
use_saved=st.checkbox('载入云端已保存的候选池',value=False,disabled=not bool(DATABASE_URL))

if file is None:
 
 try: df=load_cloud(DATABASE_URL) if use_saved else pd.DataFrame()
 except Exception as e: st.error(f'读取云端数据库失败：{e}');df=pd.DataFrame()
 if 'socialcrawl_candidates' in st.session_state:
  df=pd.concat([df,pd.DataFrame(st.session_state['socialcrawl_candidates'])],ignore_index=True)
 if 'tagged_candidates' in st.session_state:
  df=pd.concat([df,pd.DataFrame(st.session_state['tagged_candidates'])],ignore_index=True)
 if 'url_candidates' in st.session_state:
  df=pd.concat([df,pd.DataFrame(st.session_state['url_candidates'])],ignore_index=True)
 if 'meta_result' in st.session_state:
  df=pd.concat([df,pd.DataFrame([st.session_state['meta_result']])],ignore_index=True)
 if df.empty:
  st.warning('尚无真实候选账号。可连接 Meta、添加账号链接、导入表格或载入本地数据。')
  if st.checkbox('查看虚构演示数据',value=False): df=example.copy()
  else: st.stop()
else:
 try:
  df=pd.read_csv(file) if file.name.lower().endswith('.csv') else pd.read_excel(file)
 except Exception as e:
  st.error(f'读取文件失败：{e}');st.stop()
if 'socialcrawl_candidates' in st.session_state and file is not None:
 df=pd.concat([df,pd.DataFrame(st.session_state['socialcrawl_candidates'])],ignore_index=True)
if 'tagged_candidates' in st.session_state and file is not None:
 df=pd.concat([df,pd.DataFrame(st.session_state['tagged_candidates'])],ignore_index=True)
if 'url_candidates' in st.session_state and file is not None:
 df=pd.concat([df,pd.DataFrame(st.session_state['url_candidates'])],ignore_index=True)
if 'meta_result' in st.session_state and file is not None:
 df=pd.concat([df,pd.DataFrame([st.session_state['meta_result']])],ignore_index=True)
for c in columns:
 if c not in df.columns:df[c]=pd.NA
# One row per brand + source + username; latest input wins.
df['username']=df['username'].astype('string').str.strip().str.lstrip('@')
df=df.dropna(subset=['username'])
df=df[df['username']!='']
df=df.drop_duplicates(subset=['username'],keep='last').reset_index(drop=True)
st.caption('下表可以直接修改或补全候选账号的数据。所有未知字段保持空白，避免被误判为符合。')
df=st.data_editor(df[columns],num_rows='dynamic',use_container_width=True,key='candidate_editor')
if st.button('💾 保存候选池到云端',disabled=not bool(DATABASE_URL)):
 try:save_cloud(df,DATABASE_URL);st.success('已保存到云端数据库；不会自动删除其他浏览器会话中的账号。')
 except Exception as e:st.error(f'保存失败：{e}')
if df.empty:
 st.info('表格没有候选账号。');st.stop()
for c in ['followers','following','child_age_months','baby_posts_last10','days_since_post']:
 df[c]=pd.to_numeric(df[c],errors='coerce')
def yn(v):
 if pd.isna(v):return None
 s=str(v).strip().lower()
 return True if s in ['yes','true','1','y','是','符合'] else False if s in ['no','false','0','n','否','不符合'] else None

def inspect(row):
 hard=[];unknown=[]
 def check(field,ok,description):
  if pd.isna(row[field]):unknown.append(description)
  elif not ok:hard.append(description)
 check('followers',min_followers<=row['followers']<=max_followers if pd.notna(row['followers']) else False,'粉丝数不在范围')
 if strict_ratio:
  check('following',row['following']<=row['followers'] if pd.notna(row['following']) and pd.notna(row['followers']) else False,'关注数大于粉丝数或粉丝数缺失')
 if us_only:
  if pd.isna(row['country']) or str(row['country']).strip()=='':unknown.append('地区未确认')
  elif str(row['country']).strip().lower() not in ('us','usa','united states','united states of america','美国'):hard.append('非美国账号')
 check('child_age_months',baby_min<=row['child_age_months']<=baby_max if pd.notna(row['child_age_months']) else False,'孩子年龄不符合')
 check('baby_posts_last10',row['baby_posts_last10']>=3 if pd.notna(row['baby_posts_last10']) else False,'近期宝宝出镜不足 3/10')
 u=yn(row['ugc']);p=yn(row['public'])
 if u is None:unknown.append('UGC 类型未验证')
 elif not u:hard.append('非 UGC 内容')
 if p is None:unknown.append('账号公开状态未验证')
 elif not p:hard.append('非公开账号')
 if active_only:check('days_since_post',row['days_since_post']<=90 if pd.notna(row['days_since_post']) else False,'90 天未更新')
 status='排除' if hard else '待复核' if unknown else '符合'
 # Interpretability-first score, never supersedes hard filters.
 score=0
 if pd.notna(row['followers']) and min_followers<=row['followers']<=max_followers:score+=15
 if pd.notna(row['following']) and pd.notna(row['followers']) and row['following']<=row['followers']:score+=15
 if str(row['country']).strip().lower() in ('us','usa','united states','united states of america','美国'):score+=15
 if pd.notna(row['child_age_months']) and baby_min<=row['child_age_months']<=baby_max:score+=15
 if pd.notna(row['baby_posts_last10']):score+=min(15,max(0,row['baby_posts_last10'])*2.5)
 if u is True:score+=10
 if p is True:score+=5
 if pd.notna(row['days_since_post']) and row['days_since_post']<=30:score+=10
 return pd.Series({'status':status,'score':round(score),'reject_reasons':'；'.join(hard),'review_required':'；'.join(unknown)})
results=pd.concat([df.reset_index(drop=True),df.apply(inspect,axis=1)],axis=1)
results=results.sort_values(by=['status','score'],ascending=[True,False],key=lambda s:s.map({'符合':0,'待复核':1,'排除':2}) if s.name=='status' else s)

a,b,c,d=st.columns(4)
a.metric('候选账号',len(results));b.metric('符合',(results.status=='符合').sum());c.metric('待复核',(results.status=='待复核').sum());d.metric('排除',(results.status=='排除').sum())
st.subheader('2 · 查看结果')
choice=st.multiselect('状态筛选',['符合','待复核','排除'],default=['符合','待复核'])
show=results[results.status.isin(choice)]
st.dataframe(show[['username','followers','following','country','child_age_months','baby_posts_last10','status','score','reject_reasons','review_required','profile_url','notes']],hide_index=True,use_container_width=True, column_config={'profile_url':st.column_config.LinkColumn('主页链接')})
st.subheader('3 · 导出名单')
st.download_button('导出当前筛选 CSV',show.to_csv(index=False).encode('utf-8-sig'),f'mambo_{product.lower()}_{brand}_creators.csv','text/csv',type='primary')
buf=BytesIO()
with pd.ExcelWriter(buf,engine='openpyxl') as writer:
 for status,name in [('符合','Qualified'),('待复核','Needs_review'),('排除','Rejected')]:results[results.status==status].to_excel(writer,sheet_name=name,index=False)
st.download_button('导出完整 Excel（分类 3 个工作表）',buf.getvalue(),f'mambo_{product.lower()}_{brand}_creators.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
st.caption('说明：Meta Business Discovery 可读取符合条件的专业账号；Tagged 当前支持合规数据导出导入，自动提供商 API 仍待对接。未授权的完整 Followers / Following 列表不提供。所有无法核验条件保持待复核。')
