"""Mambo Creator Finder: one primary action, defensible screening, explicit API cost caps."""
import io,json
import pandas as pd
import streamlit as st
from security import secret,require_login
from pipeline import run_pipeline

st.set_page_config(page_title='Mambo Creator Finder',page_icon='🟡',layout='wide')
st.markdown('<style>.stApp{background:#F8F7F0}h1,h2{color:#39342e}.stButton button[kind="primary"]{background:#F3D54E;color:#25221c}</style>',unsafe_allow_html=True)
require_login()
st.title('🟡 Mambo Creator Finder')
st.caption('输入品牌 → 自动发现 Tagged 作者 → 读取主页与最近作品 → AI 辅助筛选 → Excel')
key=secret('SOCIALCRAWL_API_KEY'); ai_key=secret('OPENAI_API_KEY')
brand=st.text_input('竞品 Instagram 用户名',value='theofficialbibs').strip().lstrip('@')
col1,col2,col3=st.columns(3)
with col1:product=st.selectbox('目标产品线',['Guard','Float','Rider'])
with col2:min_followers=st.number_input('最低粉丝数',min_value=0,value=1000,step=500)
with col3:max_followers=st.number_input('最高粉丝数',min_value=100,value=20000,step=1000)
settings={'product':product,'min_followers':min_followers,'max_followers':max_followers,'strict_ratio':True,'us_only':True}
st.caption('硬条件：美国本土｜关注数不得大于粉丝数｜母婴 UGC｜宝宝近 10 条至少出现 3 条｜Guard 6–24m / Float 3–24m / Rider 5–10y。证据不足一律待复核。')
with st.expander('控制费用和数据源',expanded=True):
    mode=st.radio('Tagged 数据来源',['自动获取新数据（消耗额度）','使用之前下载的 JSON（不重复扣 Tagged 费用）'],horizontal=True)
    uploaded=st.file_uploader('可上传已有 response.json',type=['json']) if mode.startswith('使用') else None
    max_creators=st.slider('最多分析多少位不同作者',1,100,15,5)
    pages=st.slider('最多读取 Tagged 页数',1,10,1) if mode.startswith('自动') else 0
    st.caption(f'SocialCrawl 估算上限：约 {pages*5+max_creators*2} Credits（Tagged 每页约5，主页和帖子每人各约1）。实际按服务商计费为准；API 出错也可能有费用。')
    if ai_key:st.success('可选 AI 内容分析已配置；图文分析可能另产生 OpenAI API 费用。')
    else:st.info('OPENAI_API_KEY 未配置：可自动核验粉丝数和关注数，宝宝年龄、出镜和 UGC 会保持待复核，不会伪造合格名单。')
    approved=st.checkbox('我同意本次按上述限制调用数据接口，并理解 AI 可能另行计费',value=False)
    if not key:st.error('缺少 SOCIALCRAWL_API_KEY，请在 Streamlit Cloud Secrets 中配置。')
    if mode.startswith('使用') and uploaded is None:st.info('请先上传之前下载的 response.json。')
ready=bool(key and approved and (mode.startswith('自动') or uploaded))
if st.button('🚀 一键发现、筛选并生成名单',type='primary',disabled=not ready,use_container_width=True):
    payload=None
    if uploaded:
        try:payload=json.loads(uploaded.getvalue().decode('utf-8'))
        except Exception as e:st.error(f'JSON无法解析：{e}');st.stop()
    bar=st.progress(0,text='正在读取 Tagged 与主页资料')
    def update(i,n,name):bar.progress(i/n,text=f'已分析 {i}/{n} · @{name}')
    try:
        rows,stats=run_pipeline(brand,key,settings,max_creators,pages,ai_key,progress=update,candidate_payload=payload)
        st.session_state['results']=rows;st.session_state['run_stats']=stats
        st.success(f'完成：发现 {stats["unique_discovered"]} 个不同账号，已处理 {stats["analyzed"]} 个。SocialCrawl 返回的本次扣费合计 {stats["socialcrawl_credits_reported"]} Credits。')
    except Exception as e:st.error(f'处理未完成：{str(e)[:300]}')
if 'results' in st.session_state:
    results=st.session_state['results']; stats=st.session_state['run_stats']
    if stats['errors']:st.warning('；'.join(stats['errors']))
    records=[]
    for r in results:
        analysis=r.get('analysis') or {};posts=r.get('posts') or []
        records.append({'账号':r['username'],'筛选结果':r['status'],'原因与待核验项':r['reasons'],
        '粉丝数':r.get('followers'),'关注数':r.get('following'),'所在地信息':r.get('country'),
        '宝宝年龄(月)':analysis.get('child_age_months'),'年龄证据':analysis.get('age_evidence'),
        '最近10条宝宝出镜数':analysis.get('baby_posts_last10'),'UGC':analysis.get('ugc'),
        'AI分析说明':analysis.get('reason'),'简介':r.get('bio'),'IG主页':r.get('profile_url'),
        'Tagged证据':r.get('evidence_url'),'最近帖子证据':posts[0]['url'] if posts else '',
        '读取错误':r.get('fetch_error') or r.get('ai_error') or ''})
    df=pd.DataFrame(records)
    a,b,c=st.columns(3)
    a.metric('符合',sum(df['筛选结果']=='符合'))
    b.metric('待复核',sum(df['筛选结果']=='待复核'))
    c.metric('排除',sum(df['筛选结果']=='排除'))
    st.subheader('筛选名单')
    selection=st.multiselect('显示状态',['符合','待复核','排除'],default=['符合','待复核'])
    st.dataframe(df[df['筛选结果'].isin(selection)],hide_index=True,use_container_width=True)
    output=io.BytesIO()
    with pd.ExcelWriter(output,engine='openpyxl') as writer:
        for state,title in [('符合','Qualified'),('待复核','Needs_Review'),('排除','Rejected')]:
            df[df['筛选结果']==state].to_excel(writer,index=False,sheet_name=title)
    st.download_button('⬇ 下载分类 Excel 名单',output.getvalue(),file_name=f'mambo_{brand}_{product.lower()}_screened.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',type='primary')
st.caption('不会获取未经许可的私人账号数据。AI 结果是辅助判断；年龄和美国所在地必须有明确公开证据，不能仅凭照片推断。')
