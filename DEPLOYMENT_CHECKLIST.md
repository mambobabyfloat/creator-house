# One-time deployment checklist

- [ ] Upload all project files (not the zip) into the **root** of `mambobabyfloat/creator-house`.
- [ ] Confirm `app.py`, `pipeline.py`, `socialcrawl.py`, `requirements.txt` appear at repository root.
- [ ] Configure `APP_PASSWORD` and `SOCIALCRAWL_API_KEY` in Streamlit Cloud Secrets (not GitHub).
- [ ] Optional for AI visual/text review: configure `OPENAI_API_KEY` securely.
- [ ] Refresh existing Streamlit web app.
- [ ] Reuse `response.json` first to avoid spending another 5 credits on Tagged discovery.
- [ ] Set a small creator cap, accept cost, click the single primary action and inspect Qualified / Needs_Review / Rejected.
- [ ] Download the Excel output; without DB this app does not promise persistent storage.
