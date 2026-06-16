#!/usr/bin/env bash
# Pushes this folder to your empty GitHub repo. Run from inside the unzipped folder.
set -e
git init
git add -A
git commit -m "valbot through session 3"
git branch -M main
git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/benedictprimmer-web/ebay-valuation-bot.git
git push -u origin main
echo "Done. Refresh the repo page."
