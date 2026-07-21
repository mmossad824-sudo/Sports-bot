// ══════════════════════════════════════════════════════════════════════════════
// BILINGUAL SUPPORT — Arabic (RTL) ↔ English (LTR)
// ══════════════════════════════════════════════════════════════════════════════
const TRANSLATIONS = {
    ar: {
        siteName:       'يلا شوت',
        siteAccent:     'شوت',
        tabToday:       'مباريات اليوم',
        tabYesterday:   'مباريات الأمس',
        tabTomorrow:    'مباريات الغد',
        titleToday:     'مباريات اليوم بث مباشر',
        titleYesterday: 'مباريات الأمس',
        titleTomorrow:  'مباريات الغد',
        btnToday:       'اليوم',
        btnYesterday:   'الأمس',
        btnTomorrow:    'الغد',
        loading:        'جاري تحميل المباريات...',
        noMatches:      'لا توجد مباريات مجدولة في هذا اليوم',
        watchLive:      'مشاهدة مباشرة',
        live:           'مباشر',
        finished:       'انتهت',
        notStarted:     'لم تبدأ',
        halfTime:       'استراحة',
        searchPlaceholder: 'ابحث عن مباراة أو فريق...',
        noStream:       'البث غير متوفر حالياً، يبدأ قبل المباراة بـ 15 دقيقة',
        switchLang:     'English',
        telegramBtn:    'قناة التليجرام',
        facebookBtn:    'فيسبوك',
        joinTelegram:   'انضم للجروب',
        tickerText:     '🔥 أهلاً بكم في يلا شوت - تغطية حصرية ومباشرة لأهم مباريات اليوم بأعلى جودة وبدون تقطيع! 🔥',
        breaking:       'عاجل',
        footerText:     '© 2026 يلا شوت — الموقع دليل رياضي للبث المباشر',
        footerSub:      'لا نستضيف أي محتوى مرئي على خوادمنا بل نوفر روابط لبثوث خارجية.',
        fbStripLabel:   'تابعنا على فيسبوك للتنبيهات الفورية',
        fbStripSub:     'Yalla Shoot Today — أخبار وأهداف مباشرة',
        fbStripBtn:     'أعجبني',
        sideNavTitle:   'يلا شوت',
        liveBadge:      'مباشر',
        analysis:       'تحليل وتوقعات المباراة',
        liveChat:       'الدردشة الحية وتوقعات الجماهير',
        teamA:          'الفريق الأول',
        teamB:          'الفريق الثاني',
        streamBlack:    'شاشة سوداء؟ اضغط هنا للمشاهدة مباشرة',
        fullscreen:     'ملء الشاشة',
        close:          'إغلاق',
        official:       'رسمي',
        tgGroupLabel:   'جروب التليجرام الرسمي - Yalla Shoot Today Group',
        tgGroupSub:     'تغطية حصرية، أهداف، ومباريات بدون تقطيع مجاناً',
        predict:        'اضغط لبدء البث المباشر',
        predictSub:     'اضغط الزر',
        predictTimes:   'مرات لبدء المشاهدة المجانية',
        watchNow:       'شاهد الآن مجاناً',
    },
    en: {
        siteName:       'Yalla Shoot',
        siteAccent:     'Shoot',
        tabToday:       "Today's Matches",
        tabYesterday:   "Yesterday's Matches",
        tabTomorrow:    "Tomorrow's Matches",
        titleToday:     'Live Football Matches Today',
        titleYesterday: "Yesterday's Results",
        titleTomorrow:  "Tomorrow's Schedule",
        btnToday:       'Today',
        btnYesterday:   'Yesterday',
        btnTomorrow:    'Tomorrow',
        loading:        'Loading matches...',
        noMatches:      'No matches scheduled for this day',
        watchLive:      'Watch Live',
        live:           'LIVE',
        finished:       'Full Time',
        notStarted:     'Not Started',
        halfTime:       'Half Time',
        searchPlaceholder: 'Search match or team...',
        noStream:       'Stream not available yet. Starts 15 minutes before kick-off.',
        switchLang:     'عربي',
        telegramBtn:    'Telegram Channel',
        facebookBtn:    'Facebook',
        joinTelegram:   'Join Group',
        tickerText:     '🔥 Welcome to Yalla Shoot — HD live football streams, no buffering! Today\'s biggest matches covered. 🔥',
        breaking:       'Breaking',
        footerText:     '© 2026 Yalla Shoot — Sports streaming directory',
        footerSub:      'We do not host any video content. We provide links to external streams.',
        fbStripLabel:   'Follow us on Facebook for live alerts',
        fbStripSub:     'Yalla Shoot Today — Live goals & match updates',
        fbStripBtn:     'Like Page',
        sideNavTitle:   'Yalla Shoot',
        liveBadge:      'LIVE',
        analysis:       'Match Analysis & Predictions',
        liveChat:       'Live Chat & Fan Predictions',
        teamA:          'Home Team',
        teamB:          'Away Team',
        streamBlack:    'Black screen? Click here to watch',
        fullscreen:     'Fullscreen',
        close:          'Close',
        official:       'Official',
        tgGroupLabel:   'Official Telegram Group — Yalla Shoot Today',
        tgGroupSub:     'Exclusive coverage, goals, and HD streams for free',
        predict:        'Tap to Start Live Stream',
        predictSub:     'Tap the button',
        predictTimes:   'times to watch for free',
        watchNow:       'Watch Now Free',
    }
};

let currentLang = localStorage.getItem('yalla_lang') || 'ar';

function t(key) {
    return (TRANSLATIONS[currentLang] || TRANSLATIONS['ar'])[key] || key;
}

function applyLanguage() {
    const isAr = currentLang === 'ar';
    document.documentElement.lang = currentLang;
    document.documentElement.dir  = isAr ? 'rtl' : 'ltr';
    document.body.classList.toggle('lang-en', !isAr);

    // Header logo
    const logoSpan = document.querySelector('.hdr-logo span');
    if (logoSpan) logoSpan.innerHTML = isAr
        ? 'يلا <span class="hdr-logo-accent">شوت</span>'
        : 'Yalla <span class="hdr-logo-accent">Shoot</span>';

    // Language toggle button
    const langBtn = document.getElementById('lang-toggle-btn');
    if (langBtn) langBtn.textContent = t('switchLang');

    // Search placeholder
    const srch = document.getElementById('search-input');
    if (srch) srch.placeholder = t('searchPlaceholder');

    // Date strip buttons
    const btnMap = { yesterday: 'btnYesterday', today: 'btnToday', tomorrow: 'btnTomorrow' };
    document.querySelectorAll('.ds-btn[data-tab]').forEach(btn => {
        const key = btnMap[btn.getAttribute('data-tab')];
        if (key) btn.innerHTML = btn.innerHTML.replace(/[\u0600-\u06FF\w]+[\s\S]*$/, t(key));
    });

    // Side nav tabs
    document.querySelectorAll('.snav-tab[data-tab]').forEach(a => {
        const tab = a.getAttribute('data-tab');
        const icon = a.querySelector('i');
        const iconHtml = icon ? icon.outerHTML + ' ' : '';
        const tabKeys = { yesterday: 'tabYesterday', today: 'tabToday', tomorrow: 'tabTomorrow' };
        if (tabKeys[tab]) a.innerHTML = iconHtml + t(tabKeys[tab]);
    });

    // Side nav header
    const sideNavTitle = document.querySelector('.side-nav-header span');
    if (sideNavTitle) sideNavTitle.textContent = t('sideNavTitle');

    // News ticker
    const ticker = document.querySelector('.ticker-scroll p');
    if (ticker) ticker.textContent = t('tickerText');
    const tickerLabel = document.querySelector('.ticker-label');
    if (tickerLabel) tickerLabel.textContent = t('breaking');

    // No matches text
    const noMatchEl = document.querySelector('#no-matches p');
    if (noMatchEl) noMatchEl.textContent = t('noMatches');

    // Loading text
    const loadingP = document.querySelector('#loading-spinner p');
    if (loadingP) loadingP.textContent = t('loading');

    // No stream placeholder
    const noStreamP = document.querySelector('#no-stream-placeholder p');
    if (noStreamP) noStreamP.textContent = t('noStream');

    // Live badge in player
    const liveBadgeSm = document.querySelector('.live-badge-sm');
    if (liveBadgeSm) liveBadgeSm.innerHTML = '<i class="fa-solid fa-circle"></i> ' + t('liveBadge');

    // External stream btn
    const extStream = document.querySelector('#external-stream-link span');
    if (extStream) extStream.textContent = t('streamBlack');

    // Analysis header
    const analysisH3 = document.querySelector('.analysis-hdr h3');
    if (analysisH3) analysisH3.textContent = t('analysis');

    // Live chat header
    const chatH3 = document.querySelector('.chat-hdr h3');
    if (chatH3) chatH3.textContent = t('liveChat');

    // Telegram ad card
    const tgLabel = document.querySelector('.ad-card strong');
    if (tgLabel) tgLabel.textContent = t('tgGroupLabel');
    const tgSub = document.querySelector('.ad-card small');
    if (tgSub) tgSub.textContent = t('tgGroupSub');
    const tgBtn = document.querySelector('.ad-card-btn');
    if (tgBtn) tgBtn.textContent = t('joinTelegram');

    // Floating buttons
    const fbBtn = document.querySelector('.floating-btn.fb-btn span');
    if (fbBtn) fbBtn.textContent = t('facebookBtn');
    const tgFloatBtn = document.querySelector('.floating-btn.tg-btn span');
    if (tgFloatBtn) tgFloatBtn.textContent = t('telegramBtn');

    // Footer
    const footerP = document.querySelector('.site-footer p');
    if (footerP) footerP.textContent = t('footerText');
    const footerSm = document.querySelector('.site-footer small');
    if (footerSm) footerSm.textContent = t('footerSub');

    // Facebook follow strip
    const fbStripLabel = document.getElementById('fb-strip-label');
    if (fbStripLabel) fbStripLabel.textContent = t('fbStripLabel');
    const fbStripSub = document.getElementById('fb-strip-sub');
    if (fbStripSub) fbStripSub.textContent = t('fbStripSub');
    const fbStripBtnText = document.getElementById('fb-strip-btn-text');
    if (fbStripBtnText) fbStripBtnText.textContent = t('fbStripBtn');

    // Ad click modal
    const admTitle = document.querySelector('.adm-title');
    if (admTitle) admTitle.textContent = t('predict');
    const admBtn = document.querySelector('.adm-btn');
    if (admBtn) admBtn.innerHTML = '<i class="fa-solid fa-play"></i> ' + t('watchNow');

    // Official label in ad strip
    const officialLabel = document.querySelector('.ad-strip-label');
    if (officialLabel) officialLabel.textContent = t('official');

    // Fullscreen/Close buttons in player
    const fsBtn = document.getElementById('fullscreen-player');
    if (fsBtn) fsBtn.title = t('fullscreen');
    const closeBtn = document.getElementById('close-player');
    if (closeBtn) closeBtn.title = t('close');

    // Meta title & description
    document.title = isAr
        ? 'يلا شوت - بث مباشر مباريات اليوم'
        : 'Yalla Shoot - Watch Live Football Today';
    const metaDesc = document.querySelector('meta[name="description"]');
    if (metaDesc) metaDesc.content = isAr
        ? 'يلا شوت - مشاهدة مباريات اليوم بث مباشر بدون تقطيع بجودة عالية'
        : 'Yalla Shoot — Watch today\'s football matches live in HD, no buffering, for free.';

    // Update date badge if needed
    updateDateBadge();
}

function toggleLanguage() {
    currentLang = currentLang === 'ar' ? 'en' : 'ar';
    localStorage.setItem('yalla_lang', currentLang);
    applyLanguage();
    // Re-render matches with new language
    if (allMatches.length > 0) displayMatchesForActiveTab();
}

// ══════════════════════════════════════════════════════════════════════════════
// API Configuration
// Replace this URL with your actual Hugging Face Space API URL once deployed!
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://127.0.0.1:7860'
    : window.location.origin; 

// Monetization Configuration
const ADS_CONFIG = {
    // Adsterra Social Bar Ad Script URL (from your Adsterra dashboard)
    socialBarScript: 'https://pl29899837.effectivecpmnetwork.com/e4/48/0b/e4480b4a0a4ef0a7e842009f7c505039.js',
    
    // Adsterra Native Banner configurations (under video player)
    bannerAd: {
        containerId: 'container-3de130477da3485fd755fef311849b77',
        scriptHash: '3de130477da3485fd755fef311849b77',
        // Adsterra domain for invocation
        domain: 'pl29899836.effectivecpmnetwork.com',
        // Auto-refresh interval in milliseconds (3 minutes = 180000ms, 5 minutes = 300000ms)
        refreshIntervalMs: 180000
    },
    
    // Popunder Ad configuration (Direct Link option from Adsterra / Monetag / PropellerAds)
    // Put your actual Direct Link URL here. Users clicking anywhere on the page will trigger it.
    popunder: {
        enabled: true,
        directLinkUrl: 'https://www.profitablecpmrate.com/e4480b4a0a4ef0a7e842009f7c505039', // replace with your actual Direct Link
        // Cooling down period: once clicked, don't trigger another popunder for 5 minutes (300000ms)
        cooldownMs: 300000 
    },
    
    // Adsterra VAST Video Ad tag configuration (Plays video ads inside the player)
    vast: {
        enabled: false, // Set to true once you have a VAST tag URL from Adsterra
        url: '' // Paste your Adsterra VAST XML/URL tag here
    }
}; 

let hlsPlayer = null;
let activeMatchId = null;
let currentSources = [];
let activeSourceIndex = -1;
let pollIntervalId = null;
let retryCount = 0;
const MAX_RETRIES = 3;

let activeTab = 'today';
let allMatches = [];

// ── Click-Trap Modal State ────────────────────────────────────────────────────
let clickTrapClicks = 0;
const CLICK_TRAP_TOTAL = 3;
let clickTrapMatchId = null;  // stored match to open after clicks done
let clickTrapSources = null;  // stored sources


// Helper to get date string in Cairo Time (UTC+3)
function getCairoDateString(offsetDays = 0) {
    const d = new Date();
    const utc = d.getTime() + (d.getTimezoneOffset() * 60000);
    const cairoTime = new Date(utc + (3600000 * 3));

    if (offsetDays !== 0) cairoTime.setDate(cairoTime.getDate() + offsetDays);

    const year  = cairoTime.getFullYear();
    const month = String(cairoTime.getMonth() + 1).padStart(2, '0');
    const day   = String(cairoTime.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function filterMatchesByTab(matches, tab) {
    const targetDate = getCairoDateString(tab === 'yesterday' ? -1 : (tab === 'tomorrow' ? 1 : 0));
    return matches.filter(m => !m.match_date ? tab === 'today' : m.match_date === targetDate);
}

function updateDateBadge() {
    const badge = document.getElementById('current-date');
    const titleEl = document.getElementById('page-title-text');
    if (!badge) return;
    const d = new Date();
    const utc = d.getTime() + (d.getTimezoneOffset() * 60000);
    const cairoTime = new Date(utc + (3600000 * 3));
    let offset = 0;
    if (activeTab === 'yesterday') offset = -1;
    if (activeTab === 'tomorrow')  offset = 1;
    cairoTime.setDate(cairoTime.getDate() + offset);
    const locale = currentLang === 'en' ? 'en-US' : 'ar-EG';
    const dateStr = cairoTime.toLocaleDateString(locale, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    badge.innerText = dateStr;
    if (titleEl) {
        const labels = {
            today:     t('titleToday'),
            yesterday: t('titleYesterday'),
            tomorrow:  t('titleTomorrow')
        };
        titleEl.innerText = labels[activeTab] || t('titleToday');
    }
}

function displayMatchesForActiveTab() {
    const container = document.getElementById('matches-container');
    const noMatches = document.getElementById('no-matches');
    const filtered  = filterMatchesByTab(allMatches, activeTab);
    if (filtered.length === 0) {
        noMatches.classList.remove('hidden');
        container.innerHTML = '';
        return;
    }
    noMatches.classList.add('hidden');
    renderMatches(filtered);
}


// Initialize Page
document.addEventListener('DOMContentLoaded', () => {
    updateDateBadge();

    // Setup Tab click handlers
    document.querySelectorAll('.ds-btn, .snav-tab').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const tab = btn.getAttribute('data-tab');
            if (!tab) return;
            document.querySelectorAll('.ds-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.ds-btn[data-tab="' + tab + '"]').forEach(b => b.classList.add('active'));
            document.querySelectorAll('.snav-tab').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.snav-tab[data-tab="' + tab + '"]').forEach(b => b.classList.add('active'));
            activeTab = tab;
            updateDateBadge();
            displayMatchesForActiveTab();
            closeSideNav();
        });
    });

    // ── Hamburger menu ───────────────────────────────────────────────────────
    const menuBtn    = document.getElementById('hdr-menu-btn');
    const sideNav    = document.getElementById('side-nav');
    const navOverlay = document.getElementById('nav-overlay');
    const navClose   = document.getElementById('side-nav-close');

    function openSideNav() {
        sideNav.classList.remove('hidden');
        sideNav.classList.add('open');
        navOverlay.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }
    window.closeSideNav = function() {
        sideNav.classList.remove('open');
        navOverlay.classList.add('hidden');
        document.body.style.overflow = '';
        setTimeout(() => { if (!sideNav.classList.contains('open')) sideNav.classList.add('hidden'); }, 300);
    };
    if (menuBtn) menuBtn.addEventListener('click', openSideNav);
    if (navClose) navClose.addEventListener('click', closeSideNav);
    if (navOverlay) navOverlay.addEventListener('click', closeSideNav);

    // ── Search ───────────────────────────────────────────────────────────────
    const searchToggle = document.getElementById('search-toggle-btn');
    const searchBar    = document.getElementById('hdr-search-bar');
    const searchInput  = document.getElementById('search-input');
    const searchClear  = document.getElementById('search-clear-btn');

    if (searchToggle) {
        searchToggle.addEventListener('click', () => {
            searchBar.classList.toggle('hidden');
            if (!searchBar.classList.contains('hidden')) searchInput.focus();
        });
    }
    if (searchClear) {
        searchClear.addEventListener('click', () => {
            searchInput.value = '';
            searchBar.classList.add('hidden');
            displayMatchesForActiveTab();
        });
    }
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            const q = searchInput.value.trim().toLowerCase();
            if (!q) { displayMatchesForActiveTab(); return; }
            const filtered = allMatches.filter(m =>
                m.teamA.toLowerCase().includes(q) ||
                m.teamB.toLowerCase().includes(q) ||
                m.tournament.toLowerCase().includes(q)
            );
            if (filtered.length === 0) {
                document.getElementById('no-matches').classList.remove('hidden');
                document.getElementById('matches-container').innerHTML = '';
            } else {
                document.getElementById('no-matches').classList.add('hidden');
                renderMatches(filtered);
            }
        });
    }

    // ── Load data ────────────────────────────────────────────────────────────
    fetchMatches();
    setInterval(fetchMatches, 60000);

    // ── Ads ──────────────────────────────────────────────────────────────────
    loadSocialBar();
    // No popunder on page load — only on match click via click-trap modal

    // ── Close / Fullscreen player ─────────────────────────────────────────────
    const closeBtn = document.getElementById('close-player');
    if (closeBtn) closeBtn.addEventListener('click', closePlayer);

    const fsBtn = document.getElementById('fullscreen-player');
    if (fsBtn) fsBtn.addEventListener('click', toggleWrapperFullscreen);

    // ── Overlay ad ───────────────────────────────────────────────────────────
    const overlayAd     = document.getElementById('player-overlay-ad');
    const closeOverlay  = document.getElementById('close-overlay-btn');
    if (closeOverlay) {
        closeOverlay.addEventListener('click', (e) => {
            e.stopPropagation();
            overlayAd.classList.add('hidden');
            const v = document.getElementById('native-video-player');
            if (v) v.play().catch(() => {});
        });
    }
    if (overlayAd) {
        overlayAd.addEventListener('click', (e) => {
            if (e.target.closest('#close-overlay-btn')) return;
            const url = ADS_CONFIG.popunder.directLinkUrl;
            if (url) window.open(url, '_blank');
            overlayAd.classList.add('hidden');
            const v = document.getElementById('native-video-player');
            if (v) v.play().catch(() => {});
        });
    }

    // ── External link ─────────────────────────────────────────────────────────
    const extLink = document.getElementById('external-stream-link');
    if (extLink) extLink.addEventListener('click', (e) => e.stopPropagation());

    // ── Click-Trap Modal ─────────────────────────────────────────────────────
    const adClickBtn  = document.getElementById('ad-click-btn');
    const adModal     = document.getElementById('ad-click-modal');

    if (adClickBtn && adModal) {
        adClickBtn.addEventListener('click', () => {
            clickTrapClicks++;
            const adUrl = ADS_CONFIG.popunder.directLinkUrl;
            if (adUrl) window.open(adUrl, '_blank');

            const dot = document.getElementById(`ad-dot-${clickTrapClicks}`);
            if (dot) dot.classList.add('done');

            const remaining = CLICK_TRAP_TOTAL - clickTrapClicks;
            const counterEl = document.getElementById('ad-counter-display');
            const neededEl  = document.getElementById('ad-clicks-needed');
            if (counterEl) counterEl.textContent = remaining > 0 ? remaining : '✓';
            if (neededEl)  neededEl.textContent   = remaining > 0 ? remaining : '0';

            if (clickTrapClicks >= CLICK_TRAP_TOTAL) {
                adModal.classList.add('hidden');
                if (clickTrapMatchId) _loadMatchStream(clickTrapMatchId);
            } else {
                const btn = document.getElementById('ad-click-btn');
                if (btn) btn.innerHTML = `<i class="fa-solid fa-play"></i> اضغط مرة أخرى (${remaining} متبقي)`;
            }
        });
    }
});

// Fetch Matches from FastAPI Backend
async function fetchMatches() {
    const spinner = document.getElementById('loading-spinner');
    const container = document.getElementById('matches-container');
    const noMatches = document.getElementById('no-matches');
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/matches`);
        if (!response.ok) throw new Error('Failed to fetch matches');
        
        const data = await response.json();
        allMatches = data.matches || [];
        displayMatchesForActiveTab();
        
        // Handle SEO URL: ?match=id
        const urlParams = new URLSearchParams(window.location.search);
        const matchParam = urlParams.get('match');
        if (matchParam && !activeMatchId) {
            const m = allMatches.find(x => x.id === matchParam);
            if (m) openMatchStream(matchParam);
        }
        
        spinner.classList.add('hidden');
    } catch (error) {
        console.error('Error loading matches:', error);
        spinner.classList.add('hidden');
        noMatches.classList.remove('hidden');
        noMatches.querySelector('h3').innerText = 'خطأ في الاتصال بالخادم';
        noMatches.querySelector('p').innerText = 'تأكد من تشغيل خادم Hugging Face ومطابقة الرابط في app.js';
    }
}

// Render Matches grouped by Tournament
function renderMatches(matches) {
    const container = document.getElementById('matches-container');
    container.innerHTML = '';
    
    // Group matches by tournament
    const groups = {};
    matches.forEach(match => {
        if (!groups[match.tournament]) {
            groups[match.tournament] = [];
        }
        groups[match.tournament].push(match);
    });
    
    // Render groups
    for (const [tournament, tourMatches] of Object.entries(groups)) {
        const tourCard = document.createElement('div');
        tourCard.className = 'tournament-group';
        
        // Find tournament logo if available
        const firstMatchLogo = tourMatches[0].logoA || ''; // fallback or generic
        
        tourCard.innerHTML = `
            <div class="tournament-header">
                <i class="fa-solid fa-trophy icon-color"></i>
                <span class="tournament-name">${tournament}</span>
            </div>
            <div class="tournament-matches">
                ${tourMatches.map(match => renderMatchCard(match)).join('')}
            </div>
        `;
        container.appendChild(tourCard);
    }
}

// Helper: Format Cairo Time (GMT+3) to Viewer's Local Time
function formatMatchTime(rawTime) {
    if (!rawTime || !rawTime.includes(':')) return rawTime;
    
    try {
        const [hours, minutes] = rawTime.split(':').map(Number);
        const today = new Date();
        const year = today.getFullYear();
        const month = String(today.getMonth() + 1).padStart(2, '0');
        const day = String(today.getDate()).padStart(2, '0');
        const hr = String(hours).padStart(2, '0');
        const min = String(minutes).padStart(2, '0');
        
        // Cairo matches are GMT+3
        const cairoIsoStr = `${year}-${month}-${day}T${hr}:${min}:00+03:00`;
        const matchDate = new Date(cairoIsoStr);
        
        // Formatted to visitor's local system locale
        const localTimeStr = matchDate.toLocaleTimeString('ar-EG', {
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        });
        
        // If timezone matches Cairo (UTC+3), show once
        if (today.getTimezoneOffset() === -180) {
            return `<div class="cairo-time">${rawTime} <span class="time-label">(توقيت مصر)</span></div>`;
        }
        
        // Else, show Cairo time + User local time
        return `
            <div class="cairo-time">${rawTime} <span class="time-label">(توقيت مصر)</span></div>
            <div class="local-time">${localTimeStr} <span class="time-label">(توقيتك المحلي)</span></div>
        `;
    } catch (e) {
        console.error("Error formatting time:", e);
        return rawTime;
    }
}

// Render Individual Match Card — thumbnail style like yallashoot.video
function renderMatchCard(match) {
    const isLive     = match.status === 'جارية الآن' || match.status.includes('الشوط');
    const isFinished = match.status === 'انتهت';
    const isHalf     = match.status.includes('بين الشوطين');

    const logoA = match.logoA || 'https://mediayk.gemini.media/img/yallakora/iosteams/YK-Generic-team-logo.png';
    const logoB = match.logoB || 'https://mediayk.gemini.media/img/yallakora/iosteams/YK-Generic-team-logo.png';
    const escapedId = match.id.replace(/'/g, "\\'");

    const scoreA = (match.scoreA !== null && match.scoreA !== undefined && match.scoreA !== '') ? match.scoreA : '-';
    const scoreB = (match.scoreB !== null && match.scoreB !== undefined && match.scoreB !== '') ? match.scoreB : '-';

    let badgeHtml = '';
    if (isLive || isHalf) {
        badgeHtml = `<span class="mc-live-badge"><i class="fa-solid fa-circle"></i> مباشر</span>`;
    } else if (isFinished) {
        badgeHtml = `<span class="mc-finished-badge">انتهت</span>`;
    } else {
        badgeHtml = `<span class="mc-upcoming-badge">${match.time || 'قريباً'}</span>`;
    }

    const watchText = isFinished
        ? `<i class="fa-solid fa-film"></i> الملخص والأهداف`
        : `<i class="fa-solid fa-circle-play"></i> شاهد الآن`;
    const watchClass = isFinished ? 'mc-watch-btn finished' : 'mc-watch-btn';

    return `
        <div class="match-card" onclick="openMatchStream('${escapedId}')">
            <div class="mc-thumb">
                <div class="mc-thumb-inner">
                    <img class="mc-team-img" src="${logoA}" alt="${match.teamA}" loading="lazy"
                        onerror="this.src='https://mediayk.gemini.media/img/yallakora/iosteams/YK-Generic-team-logo.png'">
                    <div class="mc-vs-score">
                        <div class="mc-score">${scoreA} - ${scoreB}</div>
                        <div class="mc-time">${match.time || ''}</div>
                    </div>
                    <img class="mc-team-img" src="${logoB}" alt="${match.teamB}" loading="lazy"
                        onerror="this.src='https://mediayk.gemini.media/img/yallakora/iosteams/YK-Generic-team-logo.png'">
                </div>
                ${badgeHtml}
            </div>
            <div class="mc-body">
                <div class="mc-teams-text">${match.teamA} ضد ${match.teamB}</div>
                <div class="mc-meta">
                    <i class="fa-solid fa-tv"></i>
                    <span>${match.channel || match.tournament || ''}</span>
                </div>
            </div>
            <button class="${watchClass}">${watchText}</button>
        </div>
    `;
}


// Open Live Stream Player — shows click-trap modal first
async function openMatchStream(matchId) {
    // Update SEO URL without reloading
    const url = new URL(window.location);
    url.searchParams.set('match', matchId);
    window.history.pushState({ matchId }, '', url);

    const adModal = document.getElementById('ad-click-modal');
    if (adModal) {
        // Reset modal state
        clickTrapClicks = 0;
        clickTrapMatchId = matchId;
        // Reset UI
        const counterEl = document.getElementById('ad-counter-display');
        const neededEl  = document.getElementById('ad-clicks-needed');
        const btn = document.getElementById('ad-click-btn');
        if (counterEl) counterEl.textContent = CLICK_TRAP_TOTAL;
        if (neededEl)  neededEl.textContent  = CLICK_TRAP_TOTAL;
        if (btn) btn.innerHTML = '<i class="fa-solid fa-play"></i> اضغط هنا للمشاهدة المجانية';
        [1, 2, 3].forEach(i => {
            const d = document.getElementById(`ad-dot-${i}`);
            if (d) d.classList.remove('done');
        });
        adModal.classList.remove('hidden');
        // Scroll to top so modal is visible
        window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
        // No modal — load directly
        _loadMatchStream(matchId);
    }
}

// Match Analysis logic
function populateMatchAnalysis(match) {
    const analysisSection = document.getElementById('match-analysis-section');
    if (!analysisSection) return;

    if (!match.teamA || !match.teamB) {
        analysisSection.classList.add('hidden');
        return;
    }
    
    analysisSection.classList.remove('hidden');
    
    // Generate deterministic pseudo-random percentages based on team names
    const hash = (match.teamA + match.teamB).split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    const winA = 30 + (hash % 35); // 30 to 64
    const draw = 15 + ((hash * 2) % 15); // 15 to 29
    const winB = 100 - winA - draw;
    
    document.getElementById('stat-team-a-name').innerText = match.teamA;
    document.getElementById('stat-team-b-name').innerText = match.teamB;
    
    document.getElementById('stat-bar-a').style.width = winA + '%';
    document.getElementById('stat-val-a').innerText = winA + '%';
    
    document.getElementById('stat-bar-draw').style.width = draw + '%';
    document.getElementById('stat-val-draw').innerText = draw + '%';
    
    document.getElementById('stat-bar-b').style.width = winB + '%';
    document.getElementById('stat-val-b').innerText = winB + '%';
    
    const tournamentStr = match.tournament ? ` ضمن منافسات ${match.tournament}` : '';
    const txt = `مباراة قوية مرتقبة تجمع بين ${match.teamA} و${match.teamB}${tournamentStr}. تشير التحليلات والإحصائيات إلى أفضلية نسبية لصالح ${winA > winB ? match.teamA : match.teamB} بفرصة فوز تصل إلى ${Math.max(winA, winB)}٪، بينما تظل فرص ${winA > winB ? match.teamB : match.teamA} قائمة بنسبة ${Math.min(winA, winB)}٪، مع احتمالية التعادل بنسبة ${draw}٪. تابع البث المباشر لمعرفة النتيجة النهائية!`;
    
    document.getElementById('analysis-text').innerText = txt;
}

// Initialize Live Chat (Disqus)
function initLiveChat(match) {
    const chatSection = document.getElementById('live-chat-section');
    if (!chatSection) return;
    
    chatSection.classList.remove('hidden');
    
    // We use a generic shortname for demo, replace 'yallashoot-demo' with real shortname
    const disqusShortname = 'yallashoot-demo';
    const pageUrl = window.location.origin + window.location.pathname + '?match=' + match.id;
    const pageId = 'match_' + match.id;
    
    if (window.DISQUS) {
        window.DISQUS.reset({
            reload: true,
            config: function () {
                this.page.identifier = pageId;
                this.page.url = pageUrl;
                this.page.title = match.teamA + ' vs ' + match.teamB;
            }
        });
    } else {
        window.disqus_config = function () {
            this.page.identifier = pageId;
            this.page.url = pageUrl;
            this.page.title = match.teamA + ' vs ' + match.teamB;
        };
        const script = document.createElement('script');
        script.src = 'https://' + disqusShortname + '.disqus.com/embed.js';
        script.setAttribute('data-timestamp', +new Date());
        (document.head || document.body).appendChild(script);
    }
}

// Internal: actually load the stream (called after click-trap completes)
async function _loadMatchStream(matchId) {
    const playerSection = document.getElementById('player-section');
    const iframeContainer = document.getElementById('iframe-player-container');
    const videoPlayerDiv = document.getElementById('video-player');
    const placeholder = document.getElementById('no-stream-placeholder');
    
    // Clear previous players and stop polling
    closePlayer();
    
    // Scroll to player
    playerSection.classList.remove('hidden');
    playerSection.scrollIntoView({ behavior: 'smooth' });
    
    activeMatchId = matchId;
    
    try {
        // If running locally, fetch FastAPI path directly. If running on Vercel, hit Vercel query proxy
        const url = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
            ? `${API_BASE_URL}/api/matches/${matchId}`
            : `${API_BASE_URL}/api/match_detail?id=${encodeURIComponent(matchId)}`;
        const response = await fetch(url);
        if (!response.ok) throw new Error('Match detail fetch failed');
        
        const match = await response.json();
        
        // Update footer details
        document.getElementById('player-title').innerText = `بث مباشر: ${match.teamA} VS ${match.teamB}`;
        document.getElementById('footer-team-a').innerText = match.teamA;
        document.getElementById('footer-team-b').innerText = match.teamB;
        document.getElementById('footer-channel').innerHTML = `<i class="fa-solid fa-tv"></i> القناة الناقلة: ${match.channel || 'غير معروفة'}`;
        document.getElementById('footer-status').innerHTML = `<i class="fa-solid fa-circle-dot"></i> الحالة: ${match.status}`;
        
        populateMatchAnalysis(match);
        initLiveChat(match);

        // Set initial document title
        if (match.status === 'جارية الآن' || match.status.includes('الشوط') || match.status.includes('بين')) {
            document.title = `(${match.scoreA} - ${match.scoreB}) ${match.teamA} ضد ${match.teamB} | يلا شوت`;
        } else {
            document.title = `${match.teamA} ضد ${match.teamB} | يلا شوت`;
        }
        
        // Setup sources array
        let sources = [];
        if (match.stream_type === 'multi') {
            try {
                sources = JSON.parse(match.stream_url);
            } catch (e) {
                console.error("Error parsing multi-source JSON:", e);
            }
        } else if (match.stream_url) {
            // Fallback for single stream source
            sources = [{
                name: "البث الرئيسي",
                type: match.stream_type || "hls",
                url: match.stream_url
            }];
        }
        
        // Handle finished matches (Highlights)
        if (match.status === 'انتهت') {
            const highlights = sources.filter(s => s.url.includes('youtube.com') || s.url.includes('youtu.be') || s.url.endsWith('.mp4'));
            if (highlights.length > 0) {
                placeholder.classList.add('hidden');
                document.getElementById('player-title').innerText = `ملخص المباراة: ${match.teamA} VS ${match.teamB}`;
                currentSources = highlights;
                
                // Show interactive overlay ad over the video
                const overlayAd = document.getElementById('player-overlay-ad');
                if (overlayAd) overlayAd.classList.remove('hidden');
                
                setupMultiSources(highlights);
            } else {
                placeholder.classList.remove('hidden');
                placeholder.querySelector('h3').innerText = 'انتهت المباراة';
                placeholder.querySelector('p').innerText = 'الملخصات واللقطات ستكون متوفرة على قناتنا في تليجرام.';
                document.getElementById('sources-tabs').classList.add('hidden');
            }
            return;
        }
        
        // Handle upcoming/live matches
        if (sources.length === 0) {
            placeholder.classList.remove('hidden');
            placeholder.querySelector('h3').innerText = 'البث المباشر غير متوفر حالياً';
            placeholder.querySelector('p').innerText = 'يبدأ البث قبل انطلاق المباراة بـ 15 دقيقة. يرجى الانتظار والتحديث.';
            document.getElementById('sources-tabs').classList.add('hidden');
            
            // Start polling even if no streams are found yet (upcoming match starts soon)
            startBackgroundPolling();
            return;
        }
        
        placeholder.classList.add('hidden');
        currentSources = sources;
        
        // Show interactive overlay ad over the video
        const overlayAd = document.getElementById('player-overlay-ad');
        if (overlayAd) overlayAd.classList.remove('hidden');
        
        setupMultiSources(sources);
        
        // Start background polling
        startBackgroundPolling();
        
    } catch (error) {
        console.error('Error opening stream:', error);
        placeholder.classList.remove('hidden');
        placeholder.querySelector('h3').innerText = 'خطأ في تشغيل البث';
        document.getElementById('sources-tabs').classList.add('hidden');
    }
}

// Start background polling for active match details
function startBackgroundPolling() {
    if (pollIntervalId) clearInterval(pollIntervalId);
    pollIntervalId = setInterval(pollActiveMatchDetails, 30000);
}

// Stop background polling
function stopBackgroundPolling() {
    if (pollIntervalId) {
        clearInterval(pollIntervalId);
        pollIntervalId = null;
    }
}

// Fetch active match details and check for stream source updates
async function pollActiveMatchDetails() {
    if (!activeMatchId) return;
    
    try {
        const url = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
            ? `${API_BASE_URL}/api/matches/${activeMatchId}`
            : `${API_BASE_URL}/api/match_detail?id=${encodeURIComponent(activeMatchId)}`;
            
        const response = await fetch(url);
        if (!response.ok) return;
        
        const match = await response.json();
        
        // Update document title with live score to keep user engaged in background tabs
        if (match.status === 'جارية الآن' || match.status.includes('الشوط') || match.status.includes('بين')) {
            document.title = `(${match.scoreA} - ${match.scoreB}) ${match.teamA} ضد ${match.teamB} | يلا شوت`;
        } else {
            document.title = `${match.teamA} ضد ${match.teamB} | يلا شوت`;
        }
        
        // Setup new sources array
        let newSources = [];
        if (match.stream_type === 'multi') {
            try {
                newSources = JSON.parse(match.stream_url);
            } catch (e) {
                console.error("Error parsing multi-source JSON:", e);
            }
        } else if (match.stream_url) {
            newSources = [{
                name: "البث الرئيسي",
                type: match.stream_type || "hls",
                url: match.stream_url
            }];
        }
        
        // Check if sources changed
        if (!isSameSources(currentSources, newSources)) {
            console.log("[Polling] Stream sources updated in the background!");
            
            const oldActiveSource = activeSourceIndex >= 0 ? currentSources[activeSourceIndex] : null;
            currentSources = newSources;
            
            // Re-setup UI tabs
            setupMultiSources(currentSources, false); // don't automatically click/play again if playing fine
            
            // If the active source index is still valid
            if (activeSourceIndex >= 0 && activeSourceIndex < currentSources.length) {
                const newActiveSource = currentSources[activeSourceIndex];
                
                // If the URL for the active source has changed, update it
                if (oldActiveSource && oldActiveSource.url !== newActiveSource.url) {
                    console.log(`[Polling] Active source URL changed for ${newActiveSource.name}`);
                    
                    // If the player is currently showing an error or placeholder, reload immediately
                    const placeholder = document.getElementById('no-stream-placeholder');
                    const isError = !placeholder.classList.contains('hidden') || document.getElementById('player-toast-text').innerText.includes('خطأ');
                    
                    if (isError) {
                        showPlayerToast(`تم تحديث رابط ${newActiveSource.name}، جاري إعادة التشغيل...`);
                        setTimeout(() => {
                            playSource(newActiveSource, activeSourceIndex);
                        }, 1000);
                    } else {
                        // Show a subtle toast notice that stream links updated
                        showPlayerToast(`تم تحديث روابط البث في الخلفية.`);
                        setTimeout(hidePlayerToast, 3000);
                    }
                }
            }
        }
    } catch (e) {
        console.error("[Polling] Error polling match details:", e);
    }
}

// Compare two lists of stream sources
function isSameSources(sourcesA, sourcesB) {
    if (sourcesA.length !== sourcesB.length) return false;
    for (let i = 0; i < sourcesA.length; i++) {
        if (sourcesA[i].url !== sourcesB[i].url || sourcesA[i].name !== sourcesB[i].name || sourcesA[i].type !== sourcesB[i].type) {
            return false;
        }
    }
    return true;
}

// Setup multiple server selector tabs
function setupMultiSources(sources, playFirst = true) {
    const tabsContainer = document.getElementById('sources-tabs');
    tabsContainer.innerHTML = '';
    tabsContainer.classList.remove('hidden');
    
    sources.forEach((source, index) => {
        const btn = document.createElement('button');
        btn.className = 'source-btn';
        if (activeSourceIndex === index || (activeSourceIndex === -1 && index === 0)) {
            btn.classList.add('active');
        }
        btn.innerText = source.name;
        
        btn.addEventListener('click', () => {
            // Manage active styles
            document.querySelectorAll('.source-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Play this specific source
            playSource(source, index);
        });
        
        tabsContainer.appendChild(btn);
    });
    
    // Play the first source by default if requested
    if (playFirst && sources.length > 0) {
        playSource(sources[0], 0);
    }
}

// Play specific source (HLS or iframe)
function playSource(source, index) {
    const videoPlayerDiv = document.getElementById('video-player');
    const iframeContainer = document.getElementById('iframe-player-container');
    const iframe = document.getElementById('iframe-player');
    const placeholder = document.getElementById('no-stream-placeholder');
    
    // Reset retry count when user explicitly plays/clicks a source or switches
    retryCount = 0;
    activeSourceIndex = index;
    
    // Hide toast overlays
    hidePlayerToast();
    placeholder.classList.add('hidden');

    // Update external link href and display
    const extLink = document.getElementById('external-stream-link');
    const extContainer = document.getElementById('external-stream-container');
    if (extLink && extContainer) {
        let displayUrl = source.url;
        const isYouTube = source.url.includes('youtube.com') || source.url.includes('youtu.be');
        
        // If it's a YouTube embed URL, convert it to a standard watch URL for external playback
        if (isYouTube && displayUrl.includes('/embed/')) {
            const videoId = displayUrl.split('/embed/')[1]?.split('?')[0];
            if (videoId) {
                displayUrl = `https://www.youtube.com/watch?v=${videoId}`;
            }
        }
        
        extLink.href = displayUrl;
        
        const spanText = extLink.querySelector('span');
        if (spanText) {
            if (isYouTube) {
                spanText.innerText = "صاحب الفيديو منع تشغيله خارج يوتيوب. اضغط هنا لمشاهدة ملخص المباراة على يوتيوب مباشرة 🎬";
            } else {
                spanText.innerText = "إذا لم يعمل البث أو ظهرت شاشة سوداء، اضغط هنا للمشاهدة في صفحة خارجية مباشرة";
            }
        }
        
        // Dynamically set rel="noreferrer" based on source type to avoid blocking YouTube
        if (isYouTube) {
            extLink.removeAttribute('rel');
        } else {
            extLink.setAttribute('rel', 'noreferrer');
        }
        
        extContainer.classList.remove('hidden');
    }
    
    // Clean previous players
    if (hlsPlayer) {
        hlsPlayer.destroy();
        hlsPlayer = null;
    }
    videoPlayerDiv.innerHTML = '';
    iframe.src = '';
    
    console.log(`[Player Manager] Playing source [${index}]: ${source.name} (${source.type})`);
    
    // Highlight the active button in the UI
    document.querySelectorAll('.source-btn').forEach((btn, idx) => {
        if (idx === index) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    
    if (source.type === 'hls') {
        videoPlayerDiv.classList.remove('hidden');
        iframeContainer.classList.add('hidden');
        
        const videoEl = document.createElement('video');
        videoEl.id = 'native-video-player';
        videoEl.style.cssText = 'width:100%;height:100%;min-height:200px;background:#000;display:block;';
        videoEl.controls = true;
        videoEl.autoplay = true;
        videoEl.playsInline = true;
        videoPlayerDiv.appendChild(videoEl);
        
        if (Hls.isSupported()) {
            hlsPlayer = new Hls({
                maxBufferLength: 30,
                maxMaxBufferLength: 600,
                enableWorker: true,
                lowLatencyMode: true,
                backBufferLength: 60,
            });
            hlsPlayer.loadSource(source.url);
            hlsPlayer.attachMedia(videoEl);
            hlsPlayer.on(Hls.Events.MANIFEST_PARSED, function() {
                videoEl.play().catch(() => {});
            });
            hlsPlayer.on(Hls.Events.ERROR, function (event, data) {
                if (data.fatal) {
                    switch (data.type) {
                        case Hls.ErrorTypes.NETWORK_ERROR:
                            hlsPlayer.startLoad();
                            break;
                        case Hls.ErrorTypes.MEDIA_ERROR:
                            hlsPlayer.recoverMediaError();
                            break;
                        default:
                            hlsPlayer.destroy();
                            handlePlayerError(source, index);
                            break;
                    }
                }
            });
        } else if (videoEl.canPlayType('application/vnd.apple.mpegurl')) {
            videoEl.src = source.url;
            videoEl.addEventListener('error', function() {
                handlePlayerError(source, index);
            });
            videoEl.play().catch(() => {});
        } else {
            handlePlayerError(source, index);
        }
        
    } else if (source.type === 'iframe' || source.type === 'telegram') {
        videoPlayerDiv.classList.add('hidden');
        iframeContainer.classList.remove('hidden');
        
        // Load ALL iframe sources directly in the browser (not through proxy)
        // The proxy uses Vercel datacenter IPs which are blocked by stream providers
        // Users' browsers can access these streams directly
        iframe.removeAttribute('referrerpolicy');
        iframe.removeAttribute('sandbox');
        iframe.src = source.url;
    }
}

// Handle Clappr load errors with retry and API refresh check
async function handlePlayerError(source, index) {
    if (retryCount < MAX_RETRIES) {
        retryCount++;
        showPlayerToast(`حدث خطأ في الاتصال بالسيرفر. جاري إعادة المحاولة (${retryCount}/${MAX_RETRIES})...`);
        
        setTimeout(() => {
            if (activeMatchId && activeSourceIndex === index) {
                console.log(`[Player Recovery] Retry attempt ${retryCount} for source: ${source.name}`);
                // Re-initialize player with same source
                if (hlsPlayer) {
                    hlsPlayer.destroy();
                    hlsPlayer = null;
                }
                const videoPlayerDiv = document.getElementById('video-player');
                videoPlayerDiv.innerHTML = '';
                
                const videoEl = document.createElement('video');
                videoEl.id = 'native-video-player';
                videoEl.style.width = '100%';
                videoEl.style.height = '100%';
                videoEl.controls = true;
                videoEl.autoplay = true;
                videoPlayerDiv.appendChild(videoEl);
                
                if (Hls.isSupported()) {
                    hlsPlayer = new Hls();
                    hlsPlayer.loadSource(source.url);
                    hlsPlayer.attachMedia(videoEl);
                    hlsPlayer.on(Hls.Events.ERROR, function (event, data) {
                        if (data.fatal) {
                            handlePlayerError(source, index);
                        }
                    });
                } else if (videoEl.canPlayType('application/vnd.apple.mpegurl')) {
                    videoEl.src = source.url;
                    videoEl.addEventListener('error', function() {
                        handlePlayerError(source, index);
                    });
                }
            }
        }, 3000); // 3 seconds delay before retry
    } else {
        // We exceeded MAX_RETRIES. Let's immediately fetch a fresh URL list from the API
        showPlayerToast("جاري البحث عن روابط بث محدثة ومستقرة...");
        
        try {
            const url = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
                ? `${API_BASE_URL}/api/matches/${activeMatchId}`
                : `${API_BASE_URL}/api/match_detail?id=${encodeURIComponent(activeMatchId)}`;
                
            const response = await fetch(url);
            if (response.ok) {
                const match = await response.json();
                let freshSources = [];
                if (match.stream_type === 'multi') {
                    freshSources = JSON.parse(match.stream_url);
                } else if (match.stream_url) {
                    freshSources = [{
                        name: "البث الرئيسي",
                        type: match.stream_type || "hls",
                        url: match.stream_url
                    }];
                }
                
                // If there's a fresh URL for our current active index that is different from our current URL
                if (freshSources.length > index && freshSources[index].url !== source.url) {
                    console.log(`[Player Recovery] Found updated URL for ${source.name}. Retrying with fresh URL.`);
                    currentSources = freshSources;
                    setupMultiSources(currentSources, false);
                    retryCount = 0; // reset
                    playSource(currentSources[index], index);
                    return;
                }
            }
        } catch (e) {
            console.error("[Player Recovery] Error checking for fresh URLs:", e);
        }
        
        // No updated URL found or fetch failed. Proceed to auto-switch to next server
        autoSwitchToNextSource();
    }
}

// Auto-switch to the next available server tab if current fails
function autoSwitchToNextSource() {
    const nextIndex = activeSourceIndex + 1;
    if (nextIndex < currentSources.length) {
        showPlayerToast(`فشل السيرفر الحالي. جاري الانتقال إلى (${currentSources[nextIndex].name}) تلقائياً...`);
        setTimeout(() => {
            if (!activeMatchId) return; // closed
            playSource(currentSources[nextIndex], nextIndex);
        }, 2000);
    } else {
        // No more sources available
        const placeholder = document.getElementById('no-stream-placeholder');
        placeholder.classList.remove('hidden');
        placeholder.querySelector('h3').innerText = 'انقطع البث المباشر';
        placeholder.querySelector('p').innerText = 'جميع سيرفرات البث خارج الخدمة حالياً. يرجى الانتظار للتحديث التلقائي.';
        hidePlayerToast();
    }
}

// Show temporary toast message inside player
function showPlayerToast(message) {
    const toast = document.getElementById('player-toast');
    const toastText = document.getElementById('player-toast-text');
    toastText.innerText = message;
    toast.classList.remove('hidden');
}

// Hide player toast message
function hidePlayerToast() {
    const toast = document.getElementById('player-toast');
    toast.classList.add('hidden');
}

// Close and clean up video player
function closePlayer() {
    const playerSection = document.getElementById('player-section');
    const iframe        = document.getElementById('iframe-player');
    const videoPlayerDiv = document.getElementById('video-player');
    const tabsContainer = document.getElementById('sources-tabs');

    activeMatchId = null;
    activeSourceIndex = -1;
    currentSources = [];
    retryCount = 0;
    stopBackgroundPolling();

    playerSection.classList.add('hidden');
    if (tabsContainer) tabsContainer.classList.add('hidden');
    hidePlayerToast();

    const overlayAd = document.getElementById('player-overlay-ad');
    if (overlayAd) overlayAd.classList.add('hidden');

    const chatSection = document.getElementById('live-chat-section');
    if (chatSection) chatSection.classList.add('hidden');

    // Remove ?match= from URL
    const url = new URL(window.location);
    url.searchParams.delete('match');
    window.history.pushState({}, '', url);

    document.title = 'يلا شوت - بث مباشر مباريات اليوم';

    if (iframe) iframe.src = '';
    if (hlsPlayer) { hlsPlayer.destroy(); hlsPlayer = null; }
    if (videoPlayerDiv) videoPlayerDiv.innerHTML = '';
}


// Rotating Direct Link Offers under Video Player (High CPM conversion)
const DIRECT_LINK_OFFERS = [
    {
        title: "🎁 توقع نتيجة المباراة مجاناً واربح مكافأة 130$!",
        desc: "استخدم الرمز الترويجي YALLALIVE للحصول على بونص التسجيل الفوري مع 1XBET.",
        btnText: "سجل واربح الآن",
        icon: "fa-gift",
        url: null
    },
    {
        title: "🔥 جروب التليجرام الرسمي لمشاهدة بدون تقطيع!",
        desc: "البث المباشر والملخصات والأهداف تصلك فوراً على تليجرام مجاناً.",
        btnText: "انضم الآن",
        icon: "fa-telegram",
        url: "https://t.me/yalla_shoot_today_Group"
    },
    {
        title: "⚡ حمل تطبيق مشاهدة مباريات اليوم مجاناً للأندرويد والآيفون!",
        desc: "تطبيق خفيف وسريع يعرض البث المباشر لجميع المباريات والبطولات.",
        btnText: "تحميل التطبيق",
        icon: "fa-download",
        url: null
    }
];
let currentOfferIndex = 0;

// Monetization: Auto-Refresh Banner Ads (Safe & Policy-Compliant)
function startAdRefreshTimer() {
    const adContainer1 = document.getElementById('banner-ad-container-1');
    const adContainer2 = document.getElementById('banner-ad-container-2');
    if (!adContainer1 && !adContainer2) return;
    
    const banner = ADS_CONFIG.bannerAd;
    
    function refreshBanner() {
        console.log('[Ad Manager] Refreshing Adsterra Banners...');
        if (adContainer1) adContainer1.style.opacity = 0;
        if (adContainer2) adContainer2.style.opacity = 0;
        
        setTimeout(() => {
            // 1. Refresh Slot 1 (Official Adsterra Banner)
            if (adContainer1) {
                adContainer1.innerHTML = '';
                const containerDiv = document.createElement('div');
                containerDiv.id = banner.containerId;
                adContainer1.appendChild(containerDiv);
                
                const script = document.createElement('script');
                script.async = true;
                script.setAttribute('data-cfasync', 'false');
                script.src = `https://${banner.domain}/${banner.scriptHash}/invoke.js?t=${Date.now()}`;
                
                adContainer1.appendChild(script);
                adContainer1.style.opacity = 1;
            }
            
            // 2. Refresh Slot 2 (Rotating Direct Link Banner)
            if (adContainer2) {
                const offer = DIRECT_LINK_OFFERS[currentOfferIndex];
                currentOfferIndex = (currentOfferIndex + 1) % DIRECT_LINK_OFFERS.length;
                
                const linkUrl = offer.url || ADS_CONFIG.popunder.directLinkUrl;
                
                adContainer2.innerHTML = `
                    <div class="simulated-ad">
                        <div class="ad-icon"><i class="fa-solid ${offer.icon}"></i></div>
                        <div class="ad-text">
                            <strong>${offer.title}</strong>
                            <p>${offer.desc}</p>
                        </div>
                        <a href="${linkUrl}" target="_blank" class="ad-btn" ${offer.url ? 'style="background: #0088cc;"' : ''}>${offer.btnText} <i class="fa-solid fa-arrow-left"></i></a>
                    </div>
                `;
                adContainer2.style.opacity = 1;
            }
        }, 300);
    }
    
    // Load immediately on page initialization
    refreshBanner();
    
    // Refresh Ads at configured interval (e.g. 3 minutes)
    setInterval(refreshBanner, banner.refreshIntervalMs);
}

// Monetization: Popunder Ad Handler
let lastPopunderTime = 0;

function initPopunderAd() {
    if (!ADS_CONFIG.popunder.enabled) return;
    
    document.addEventListener('click', (e) => {
        // Exclude clicks on close buttons or if player is explicitly closed
        if (e.target.closest('#close-player') || e.target.closest('.close-btn')) {
            return;
        }
        
        const now = Date.now();
        if (now - lastPopunderTime >= ADS_CONFIG.popunder.cooldownMs) {
            const url = ADS_CONFIG.popunder.directLinkUrl;
            if (url && !url.includes('xxxxx')) {
                console.log('[Ad Manager] Triggering Popunder Direct Link...');
                const adWin = window.open(url, '_blank');
                if (adWin) {
                    // Try to focus back to our window
                    window.focus();
                    lastPopunderTime = now;
                }
            }
        }
    });
}

// Load Social Bar Script dynamically from configuration
function loadSocialBar() {
    const url = ADS_CONFIG.socialBarScript;
    if (url && !url.includes('xxxxx')) {
        console.log('[Ad Manager] Loading Social Bar Ad script...');
        const script = document.createElement('script');
        script.src = url;
        script.type = 'text/javascript';
        document.body.appendChild(script);
    }
}

// Toggle fullscreen on player-box
function toggleWrapperFullscreen() {
    const box = document.querySelector('.player-box');
    const fsBtn = document.getElementById('fullscreen-player');
    if (!box) return;
    if (!document.fullscreenElement) {
        const req = box.requestFullscreen || box.webkitRequestFullscreen || box.msRequestFullscreen;
        if (req) req.call(box).then(() => { if(fsBtn) fsBtn.innerHTML='<i class="fa-solid fa-compress"></i>'; }).catch(()=>{});
    } else {
        const exit = document.exitFullscreen || document.webkitExitFullscreen || document.msExitFullscreen;
        if (exit) exit.call(document).then(() => { if(fsBtn) fsBtn.innerHTML='<i class="fa-solid fa-expand"></i>'; }).catch(()=>{});
    }
}


// Listen for fullscreen change event to update the button interface
document.addEventListener('fullscreenchange', () => {
    const fsBtn = document.getElementById('fullscreen-player');
    if (fsBtn) {
        if (document.fullscreenElement) {
            fsBtn.innerHTML = '<i class="fa-solid fa-compress"></i> إلغاء التكبير';
        } else {
            fsBtn.innerHTML = '<i class="fa-solid fa-expand"></i> ملء الشاشة';
        }
    }
});

// ══════════════════════════════════════════════════════════════════════════════
// INIT LANGUAGE ON LOAD
// ══════════════════════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    // Apply saved language on first load
    applyLanguage();
    // Wire up language toggle button (added to header in HTML)
    const langBtn = document.getElementById('lang-toggle-btn');
    if (langBtn) langBtn.addEventListener('click', toggleLanguage);
});
