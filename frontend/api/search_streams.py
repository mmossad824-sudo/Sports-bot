from http.server import BaseHTTPRequestHandler
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import json

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept-Language': 'ar-EG,ar;q=0.9,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Referer': 'https://www.google.com/',
}

TRANSLATIONS = {
    "برشلونة": "barcelona", "ريال مدريد": "real-madrid",
    "أتلتيكو مدريد": "atletico-madrid", "أتليتكو مدريد": "atletico-madrid",
    "ليفربول": "liverpool", "مانشستر سيتي": "manchester-city",
    "مانشستر يونايتد": "manchester-united", "أرسنال": "arsenal",
    "تشيلسي": "chelsea", "توتنهام": "tottenham",
    "بايرن": "bayern-munich", "باريس سان جيرمان": "psg",
    "باريس": "psg", "يوفنتوس": "juventus",
    "إنتر ميلان": "inter-milan", "انتر ميلان": "inter-milan",
    "ميلان": "ac-milan", "روما": "roma", "نابولي": "napoli",
    "دورتموند": "dortmund", "أياكس": "ajax",
    "الأهلي": "al-ahly", "الزمالك": "zamalek",
    "الهلال": "al-hilal", "النصر": "al-nassr",
    "الاتحاد": "al-ittihad",
    "ستاندر لياج": "standard-liege", "ستاندرد": "standard-liege",
    "سبورتنج لشبونة": "sporting-cp", "سبورتنج": "sporting-cp",
    "موناكو": "monaco", "لاس بالماس": "las-palmas",
}

# Channels to known stream embed URLs
CHANNEL_STREAMS = {
    'bein sports 1':   'https://cdn.akarela.com/bein1.php',
    'bein sport 1':    'https://cdn.akarela.com/bein1.php',
    'bein sports 2':   'https://cdn.akarela.com/bein2.php',
    'bein sport 2':    'https://cdn.akarela.com/bein2.php',
    'bein sports 3':   'https://cdn.akarela.com/bein3.php',
    'bein sport 3':    'https://cdn.akarela.com/bein3.php',
    'bein sports 4':   'https://cdn.akarela.com/bein4.php',
    'bein sports hd':  'https://cdn.akarela.com/bein1.php',
    'on sport':        'https://cdn.akarela.com/onsport.php',
    'on time sport':   'https://cdn.akarela.com/ontimesport.php',
    'on time sport 1': 'https://cdn.akarela.com/ontimesport.php',
    'ssc 1':           'https://cdn.akarela.com/ssc1.php',
    'ssc':             'https://cdn.akarela.com/ssc1.php',
    'ssc sport':       'https://cdn.akarela.com/ssc1.php',
    'ssc sport 1':     'https://cdn.akarela.com/ssc1.php',
    'ssc 2':           'https://cdn.akarela.com/ssc2.php',
    'mbc sport':       'https://cdn.akarela.com/mbcsport.php',
    'mbc sport 1':     'https://cdn.akarela.com/mbcsport.php',
    'mbc sport 2':     'https://cdn.akarela.com/mbcsport2.php',
    'al nahar sport':  'https://cdn.akarela.com/alnaharsport.php',
    'nahar sport':     'https://cdn.akarela.com/alnaharsport.php',
    'ksa sport':       'https://cdn.akarela.com/ksasport.php',
    'ksa sports':      'https://cdn.akarela.com/ksasport.php',
    'abu dhabi sport': 'https://cdn.akarela.com/abudhabi.php',
    'dmc sport':       'https://cdn.akarela.com/dmcsport.php',
    'cbc sport':       'https://cdn.akarela.com/cbcsport.php',
    'al kass':         'https://cdn.akarela.com/alkass.php',
    'al kass sport':   'https://cdn.akarela.com/alkass.php',
}

SKIP_DOMAINS = ['google', 'facebook', 'twitter', 'doubleclick',
                'analytics', 'adsterra', 'taboola', 'disqus',
                'whatsapp', 'telegram', 'shareaholic', 'addthis',
                'googletagmanager', 'googlesyndication']


def normalize(text):
    if not text: return ""
    text = re.sub(r'[أإآ]', 'ا', text)
    text = re.sub(r'ة', 'ه', text)
    return re.sub(r'\s+', ' ', text).strip().lower()


def get_en_slug(team):
    return TRANSLATIONS.get(team, team.lower().replace(' ', '-'))


def extract_iframes(html_content, label="بث"):
    sources = []
    soup = BeautifulSoup(html_content, 'html.parser')
    for iframe in soup.find_all('iframe'):
        src = iframe.get('src', '').strip()
        if not src or 'about:blank' in src or src.startswith('javascript'):
            continue
        if src.startswith('//'): src = 'https:' + src
        if not src.startswith('http'): continue
        if any(d in src for d in SKIP_DOMAINS): continue
        sources.append({"name": label, "type": "iframe", "url": src})
    return sources


def scrape_arabic_homepage(team_a, team_b):
    sources = []
    seen = set()
    
    # Clean up team names to increase match chances
    def clean(t):
        t = re.sub(r'الإماراتي|السعودي|المصري', '', t)
        t = re.sub(r'[أإآ]', 'ا', t)
        t = re.sub(r'ة', 'ه', t)
        return t.strip()

    t_a, t_b = clean(team_a), clean(team_b)
    
    # 1. Yalla Shoot Video Homepage Scrape
    try:
        url = "https://www.yallashoot.video/"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                title = clean(a.get('title', ''))
                text = clean(a.text)
                if (t_a in title or t_a in text) and (t_b in title or t_b in text):
                    match_url = a['href']
                    m_r = requests.get(match_url, headers=HEADERS, timeout=10)
                    if m_r.status_code == 200:
                        # Extract iframes
                        for s in extract_iframes(m_r.content, "يلا شوت فيديو (ذكي)"):
                            if s['url'] not in seen:
                                seen.add(s['url'])
                                sources.append(s)
                        # Extract json sources
                        raw_matches = re.findall(r'\"name\":\"([^\"]+)\",\"src\":\"([^\"]+)\"', m_r.text)
                        for name, src in raw_matches:
                            try:
                                clean_name = name.encode('utf-8').decode('unicode_escape')
                            except Exception:
                                clean_name = name
                            clean_src = src.replace('\\/', '/')
                            if clean_src not in seen:
                                seen.add(clean_src)
                                sources.append({"name": f"يلا شوت فيديو: {clean_name}", "type": "iframe", "url": clean_src})
                    break # Found the match, no need to keep searching links
    except Exception as e:
        print(f"[proxy] Smart Scraper error: {e}")

    return sources


def search_stream_embed(team_a, team_b, channel="", match_link=""):
    sources = []
    seen = set()

    def add(src, name):
        url = src if isinstance(src, str) else src.get('url')
        if url and url not in seen:
            seen.add(url)
            if isinstance(src, str):
                sources.append({"name": name, "type": "iframe", "url": url})
            else:
                src['name'] = name
                sources.append(src)

    # ── 1. Channel-based stream (most reliable) ───────────────────────────────
    if channel:
        ch_low = channel.lower().strip()
        for ch_key, embed_url in CHANNEL_STREAMS.items():
            if ch_key in ch_low or ch_low in ch_key:
                add(embed_url, f"قناة {channel} - بث مباشر 🔴")
                break

    # ── 2. Scrape yallakora match page for embedded iframes ───────────────────
    if match_link and 'yallakora.com' in match_link:
        try:
            r = requests.get(match_link, headers=HEADERS, timeout=12)
            if r.status_code == 200:
                for s in extract_iframes(r.content, "يلا كورة - بث مباشر"):
                    add(s['url'], s['name'])
        except Exception as e:
            print(f"[proxy] yallakora scrape: {e}")

    # ── 3. Try known Arabic stream aggregators ────────────────────────────────
    a_slug = get_en_slug(team_a)
    b_slug = get_en_slug(team_b)

    agg_urls = [
        f"https://www.livescore.com/en/football/",
        f"https://arab-hd.net/live-{a_slug}-vs-{b_slug}/",
        f"https://7m.cn/arabic/live/",
    ]
    for url in agg_urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True)
            if r.status_code == 200 and len(r.text) > 2000:
                for s in extract_iframes(r.content, "سيرفر بث عربي"):
                    if len(sources) < 6:
                        add(s['url'], s['name'])
        except Exception:
            pass

    # ── 4. Smart Arabic Homepage Scraper ──────────────────────────────────────
    smart_sources = scrape_arabic_homepage(team_a, team_b)
    for s in smart_sources:
        if len(sources) < 8:
            add(s['url'], s['name'])

    # ── 5. Search yalla-shoot.tv via pattern ─────────────────────────────────
    try:
        yalla_video_url = f"https://www.yallashoot.video/video/{a_slug}-vs-{b_slug}-live-stream-25-7-2026/"
        
        # Scrape yallashoot.video advanced JSON sources
        try:
            r = requests.get(yalla_video_url.replace('-25-7-2026', ''), headers=HEADERS, timeout=8)
            if r.status_code == 404:
                # Fallback to appending today's date if they require it
                from datetime import datetime
                today = datetime.now()
                r = requests.get(f"https://www.yallashoot.video/video/{a_slug}-vs-{b_slug}-live-stream-{today.day}-{today.month}-{today.year}/", headers=HEADERS, timeout=8)
            
            if r.status_code == 200:
                raw_matches = re.findall(r'\"name\":\"([^\"]+)\",\"src\":\"([^\"]+)\"', r.text)
                for name, src in raw_matches:
                    try:
                        clean_name = name.encode('utf-8').decode('unicode_escape')
                    except Exception:
                        clean_name = name
                    clean_src = src.replace('\\/', '/')
                    if len(sources) < 8:
                        add(clean_src, f"يلا شوت فيديو: {clean_name}")
        except Exception as e:
            print(f"[proxy] yallashoot.video scrape: {e}")

        pattern_urls = [
            f"https://yalla-shoot.tv/{a_slug}-vs-{b_slug}/",
            f"https://kooralive.net/{a_slug}-{b_slug}/",
        ]
        for url in pattern_urls:
            r = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True)
            if r.status_code == 200:
                for s in extract_iframes(r.content, "سيرفر يلا شوت"):
                    if len(sources) < 6:
                        add(s['url'], s['name'])
    except Exception:
        pass

    # ── 6. Always add yallakora match link as iframe fallback ─────────────────
    # Yallakora itself has a watch page that embeds streams
    if match_link and len(sources) < 3:
        # Construct watch/stream page URL
        watch_url = match_link.replace('/match/', '/stream/') if '/match/' in match_link else match_link
        if watch_url not in seen:
            seen.add(watch_url)
            sources.append({"name": "🔴 المصدر الأصلي - يلا كورة", "type": "redirect", "url": match_link})

    print(f"[proxy] Total sources for {team_a} vs {team_b}: {len(sources)}")
    return sources[:8]


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default logging

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed_url.query)

        team_a   = query.get('teamA',   [None])[0]
        team_b   = query.get('teamB',   [None])[0]
        channel  = query.get('channel', [""])[0] or ""
        link     = query.get('link',    [""])[0] or ""

        if not team_a or not team_b:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Missing teamA or teamB"}).encode())
            return

        srcs = search_stream_embed(team_a, team_b, channel, link)

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(srcs).encode())
