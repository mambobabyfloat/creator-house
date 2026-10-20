# 部署检查清单
- [ ] 私有 GitHub 仓库已建立，上传的是 ZIP 内的项目文件（不是直接上传 ZIP）
- [ ] `.streamlit/secrets.toml`、`.env` 不在仓库里
- [ ] 在 Streamlit Community Cloud 新建应用，入口 `app.py`
- [ ] APP_PASSWORD 设置为单独生成的强密码，且测试未登录无法进入
- [ ] Supabase PostgreSQL 已建立，SSL 连接方式和云托管环境兼容
- [ ] DATABASE_URL 放在 Secrets；测试云端保存与重新打开后的加载
- [ ] 先导入少量授权 Tagged 数据测试并核对作品链接
- [ ] 任何第三方 API 对接前，审核数据访问权限、服务条款与费用
- [ ] 不将孩子的照片、姓名、生日等敏感资料写入红人数据库
