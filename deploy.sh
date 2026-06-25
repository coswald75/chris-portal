#!/bin/bash
# Deploy chrisoswald.org to Cloudflare Pages
# Usage: ./deploy.sh
#
# Workflow:
#   1. Edit index.html / style.css / images in this directory
#   2. git add + git commit
#   3. ./deploy.sh
#
# Pushes to GitHub (if a remote is set) AND deploys to Cloudflare Pages.
# Requires CLOUDFLARE_API_TOKEN in .env (not committed).

set -e

# Push to GitHub if an 'origin' remote exists
if git remote get-url origin >/dev/null 2>&1; then
  echo "📤 Pushing to GitHub..."
  git push origin main
fi

# Deploy to Cloudflare Pages
echo "🚀 Deploying to Cloudflare Pages..."
source .env
CLOUDFLARE_API_TOKEN="$CLOUDFLARE_API_TOKEN" \
  npx wrangler pages deploy . --project-name chrisoswald --branch main

echo ""
echo "✅ Done! Live at https://chrisoswald.org"
