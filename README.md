# Manifestos — chrisoswald.org

A 37signals-style catalog of manifestos. Plain static HTML and CSS (no build step), deployed as-is to Cloudflare Pages project `chrisoswald`.

The homepage is a numbered list of titles. Each manifesto lives in its own directory with an `index.html` so the URL is a trailing-slash path (`/plurality-playbook/`).

Older Commonplace portal pages (politics, church, quizzes, and the rest) remain in the tree so existing deep links keep working. They are no longer the homepage.

## Files
- `index.html` — Manifestos list
- `style.css` — shared dark/terracotta styles
- `plurality-playbook/index.html` — 01. Plurality Playbook
- `images/manifestos-logo.png` — terracotta nodal-M wordmark
- `favicon.svg` — nodal-M mark
- `_redirects` — Cloudflare Pages redirects (including `/plurality-playbook` → `/plurality-playbook/`)
- `deploy.sh` — push + Cloudflare Pages deploy helper

## Local preview
From this directory:

```bash
python3 -m http.server
```

Then open http://127.0.0.1:8000/ and http://127.0.0.1:8000/plurality-playbook/.

## Adding a manifesto
1. Create `your-slug/index.html` using `plurality-playbook/index.html` as the template.
2. Add a numbered row to the `<ol>` on `index.html`.
3. Add `/your-slug /your-slug/ 301` to `_redirects` if you want the no-slash URL to land on the directory.

## Deploy
Do not deploy from a cloud agent. Locally:

1. Create `.env` with `CLOUDFLARE_API_TOKEN=...` (a Pages deploy token). `.env` is gitignored.
2. First time: create a Cloudflare Pages project named `chrisoswald` (direct upload).
3. Run `./deploy.sh`.
4. Attach the custom domain `chrisoswald.org` in the Cloudflare Pages dashboard, then add the proxied CNAME DNS records (`@` and `www` → `chrisoswald.pages.dev`) in the dashboard.
