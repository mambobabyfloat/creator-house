"""Single-workspace gate. Passwords only via deployment secrets/environment."""
import hmac
import os
import streamlit as st

def secret(key, default=''):
    # no hard-coded credentials and no serialization
    try:
        return str(st.secrets.get(key, os.getenv(key, default)))
    except (FileNotFoundError, KeyError):
        return os.getenv(key, default)

def require_login():
    password=secret('APP_PASSWORD')
    if not password:
        st.error('管理员尚未配置 APP_PASSWORD。为了保护红人数据，网站默认拒绝未授权访问。')
        st.info('在 Streamlit Cloud 的 App settings → Secrets 设置 APP_PASSWORD。也可在本地 .streamlit/secrets.toml 设置。')
        st.stop()
    if st.session_state.get('authenticated') is True:
        with st.sidebar:
            if st.button('退出登录'):
                st.session_state['authenticated']=False
                st.rerun()
        return
    st.title('🔒 Mambo Creator Finder')
    st.caption('Mambobaby 内部红人筛选后台 · 输入工作区密码')
    attempt=st.text_input('工作区密码',type='password')
    if st.button('进入工作区',type='primary'):
        if hmac.compare_digest(attempt.encode('utf-8'),password.encode('utf-8')):
            st.session_state['authenticated']=True
            st.rerun()
        else: st.error('密码不正确')
    st.stop()
