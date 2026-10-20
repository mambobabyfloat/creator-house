# Mambo Creator Finder · One-Click Edition

A single Streamlit app that reads competitor Tagged posts, deduplicates creators, fetches each author's public profile and latest posts, optionally uses an AI model to help review the content, filters by Mambobaby hard requirements, and produces a categorized Excel.

## Deploy once

Replace the files in your existing GitHub repository root with this package's files and commit. Your existing Streamlit Cloud deployment linked to that repository should reload.

Streamlit Cloud → App settings → Secrets (TOML):

```toml
APP_PASSWORD = "SET_A_PRIVATE_STRONG_PASSWORD"
SOCIALCRAWL_API_KEY = "SET_YOUR_SOCIALCRAWL_KEY"
OPENAI_API_KEY = "OPTIONAL_FOR_AI_POST_REVIEW"
```

Do not copy sample credentials literally. Do not put real keys in GitHub, screenshots or chat. An OpenAI API key is different from a ChatGPT subscription and can incur separate API charges. `OPENAI_API_KEY` is optional but without it baby appearance and UGC classifications are not automated; the tool will keep such people in review. Review visual data transmission and any applicable privacy/platform terms before enabling image analysis. Keep previously configured `DATABASE_URL` if you have one, but this edition exports Excel directly and does not require a database. No secrets are written to Excel.

## Usage

1. Enter a competitor's Instagram handle and pick Guard, Float or Rider.
2. Pick **new Tagged scan** or **reuse the saved JSON**.
3. Set a hard ceiling on pages and creator counts; acknowledge possible charges.
4. Press **One click discover, screen and export**.
5. Export Excel with Qualified / Needs_Review / Rejected sheets.

### Data limitations

- Approximate SocialCrawl costs at the time of development: Tagged 5 credits/page; profile 1 credit/account; recent posts 1 credit/account. See current vendor prices before calling. AI requests can incur separate costs and the estimator does not cap AI billing.
- The count limit caps how many newly discovered authors are processed, not how many will qualify. No automatic retries. Vendor may still bill on failed calls.
- The content reviewer looks only at available public posts (up to 10), not the complete private profile or all followers/following lists.
- `Qualified` requires all hard rules to have sufficient evidence. If source fields are missing, the status remains `Needs_Review`, not invented compliance.
- User-supplied SocialCrawl JSON is not an API key and can be reused without new Tagged request charges; profile/posts lookups still use credits.
- AI review is probabilistic. Children's ages require explicit public textual evidence, not inferred from physical appearance. 'US' requires an explicit public location claim.

Run locally: `pip install -r requirements.txt` then `streamlit run app.py`.
Run tests: `python -m pytest tests -q` (requires pytest).
