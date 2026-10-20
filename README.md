# Mambo Creator Finder · Cloud V3

Private Streamlit web application for Mambobaby's Instagram creator screening.

## What works now
- Brand workspace with Guard / Float / Rider filters and hard rejects.
- Password gate, configured via `APP_PASSWORD` in deployment secrets.
- Optional persistent PostgreSQL storage with upsert, configured via `DATABASE_URL`.
- Import licensed Tagged-post CSV/XLSX; aggregate authors with source post evidence, distinct tagged-post count.
- Paste multiple Instagram profile URLs; import candidate CSV/XLSX; edit and verify rows.
- Optional Meta Business Discovery lookups of eligible professional accounts (using **your own** authorized credentials).
- Export 3-tab XLSX or CSV; unknown data stays `待复核` instead of being marked qualified.

## Not implemented
- **No general automatic Tagged scraping**: a specific licensed/approved provider and its API contract must be evaluated and implemented.
- **No bulk Followers / Following enumeration** of arbitrary competitor accounts.
- **No vision-based automatic age/location inference.** Content review requires a further authorised source and a separately evaluated model.
- Password gate is for a small internal team, not enterprise SSO; do not store sensitive personal data about children.

## Online deployment: Streamlit Community Cloud
1. Create a **private GitHub repository**. Unzip and upload the contents of `mambo-creator-finder` to repo root, including `app.py`, requirements and `.streamlit/config.toml`. Do **not** upload `.streamlit/secrets.toml` or `.env`.
2. Open https://share.streamlit.io/ → New app → choose repository, branch and `app.py`.
3. Open **Advanced settings → Secrets** and paste e.g.:
   ```toml
   APP_PASSWORD = "a-long-unique-secret-you-generate"
   DATABASE_URL = "postgresql://USER:PASSWORD@HOST:5432/postgres?sslmode=require"
   ```
4. For the DATABASE_URL, create a Supabase Postgres project and copy the **connection string** from its database settings. For a cloud deployment, use the connection method supported by your hosting IPv4/IPv6 environment (often session pooler); use SSL. Never paste this string into a public chat or commit it to GitHub.
5. Deploy. Access the provided Streamlit app URL, then enter your APP_PASSWORD. First, use the example/template or CSV upload.
6. Select `载入云端已保存的候选池` to load prior saves, and click `保存候选池到云端` to persist edits.

**Without DATABASE_URL** you can still use the app within a session and export, but the cloud service does NOT guarantee durable local files. Cloud secrets must be set before launch or the app intentionally denies entry.

## Local use
```bash
python -m pip install -r requirements.txt
```
Create `.streamlit/secrets.toml` based on `.streamlit/secrets.toml.example`, with a real APP_PASSWORD and optionally DATABASE_URL. For a local test only, you may set `DATABASE_URL = "sqlite:///local_creator_finder.db"`; DO NOT use SQLite as durable cloud storage.
```bash
python -m streamlit run app.py
```

## Tagged integration: design contract

The external licensed provider must supply permitted access to tagged-post author and original post URL, in a documented and contractually allowed manner. Normalized columns:

| Field | Required | Meaning |
| --- | --- | --- |
| `author_username` | yes | Public Instagram handle posting content that tagged the brand |
| `post_url` | yes | Post/reel URL for verification |
| `caption` | no | Public caption when granted |
| `timestamp` | no | Posted date |
| `followers_count` | no | Provider-verified current follower count |
| `follows_count` | no | Provider-verified current following count |

A CSV containing these columns is already supported. The import will never treat an account as qualified if age, geography, public status, or other screening facts are unknown.

### Real automatic API adapter (next milestone, not shipped)
- Evaluate providers' lawful access, quotas, pricing and terms; confirm the endpoint supports **Tagged author discovery**, not merely the brand's own mentions.
- Store the provider API token ONLY in server secrets, not the browser/client/database.
- Implement `fetch_tagged(brand, cursor, max_items)` server-side against the provider's official documented endpoint; implement pagination, backoff, date range, source URL validation and deduplication.
- Normalize the provider response to the table above and import with `normalize_tagged`.
- Keep `provider_name`, evidence URL, retrieval time and original ID to trace each account; enforce deletion/refresh per provider terms.
- For each eligible account, use Business Discovery where permissions allow; only fetch public data when authorized and respect limits.
- Optional content analysis must be evidence-based, avoid confident age or location conclusions from appearance alone, and require review before outreach.

## Notes
- Example users in the template are fictional.
- Confirm your provider license and Meta's latest API permissions before production use.
- Do not share access tokens or database URLs in chats or GitHub issues.
