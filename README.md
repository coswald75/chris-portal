# chrisoswald.org

Chris Oswald's personal one-pager — a centered column linking to current projects.

Plain static site (no build step). Flat directory deployed as-is to Cloudflare Pages,
same pattern as `mountainwest-site`.

## Files
- `index.html` — the page
- `style.css` — styles (Fraunces serif + Inter sans, single centered column)
- `images/chris-cartoon.png` — portrait at top (**currently a placeholder monogram — replace with the real cartoon**)
- `favicon.svg` — "CO" monogram favicon
- `deploy.sh` — push + deploy helper

## Local preview
Open `index.html` in a browser, or run any static server from this dir, e.g.
`python3 -m http.server`.

## Before launch
1. **Replace the portrait.** Drop the real cartoon at `images/chris-cartoon.png`
   (square works best; it's masked to a circle). Keep the same filename and no HTML edit is needed.
2. Confirm the Mountain West "demographic story" link in `index.html` points where you want
   (currently → https://mountainwestsg.org).

## Deploy
1. Create `.env` with `CLOUDFLARE_API_TOKEN=...` (a Pages deploy token).
2. First time: create a Cloudflare Pages project named `chrisoswald` (direct upload).
3. Run `./deploy.sh`.
4. Attach the custom domain `chrisoswald.org` in the Cloudflare Pages dashboard, then add the
   proxied CNAME DNS records (`@` and `www` → `chrisoswald.pages.dev`) in the dashboard.
   (Per past experience, attaching the domain via API does **not** auto-create DNS — add the
   records manually in the dashboard.)
