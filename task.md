# Task List - Sports-Bot Full Implementation

## Phase 1: Security 🔐
- [x] Analyze all files - DONE
- [x] Fix cron.py - remove hardcoded BOT_TOKEN + fix timezone
- [x] Fix git remote URLs - remove tokens

## Phase 2: Highlights Fix (Dailymotion + Telegram) 🎬
- [x] Update scraper.py - add search_dailymotion_highlights() + telegram upload
- [x] Update search_highlights.py - add Dailymotion as first source
- [x] Update bot.py - add notify_highlights() + fix AttributeError
- [x] Create upload_to_telegram.py (Integrated directly into scraper on HF for performance/time limit safety)

## Phase 3: Live Streams Proxy Fix 📡
- [x] Update main.py - strip X-Frame headers + lifespan migration
- [x] Update frontend/api/proxy.py - strip headers
- [x] Update frontend/app.js - HLS.js + new types + search + fixes
- [x] Update frontend/index.html - HLS.js CDN + PWA + search UI

## Phase 4: Cron Jobs ⏰
- [x] Update vercel.json - 2 daily cron schedules (optimized for Hobby limits)

## Phase 5: UX/SEO 🚀
- [x] Create frontend/manifest.json - PWA
- [x] Create frontend/sw.js - Service Worker
- [x] Create frontend/robots.txt - SEO
- [x] Create frontend/sitemap.xml - SEO

## Phase 6: Git & Deploy 🚀
- [ ] Commit all changes
- [ ] Push to GitHub
- [ ] Push to Hugging Face
