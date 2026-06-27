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

// Helper to get date string in Cairo Time (UTC+3)
function getCairoDateString(offsetDays = 0) {
    const d = new Date();
    const utc = d.getTime() + (d.getTimezoneOffset() * 60000);
    const cairoTime = new Date(utc + (3600000 * 3));
    
    if (offsetDays !== 0) {
        cairoTime.setDate(cairoTime.getDate() + offsetDays);
    }
    
    const year = cairoTime.getFullYear();
    const month = String(cairoTime.getMonth() + 1).padStart(2, '0');
    const day = String(cairoTime.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// Filter matches array based on the active tab
function filterMatchesByTab(matches, tab) {
    const targetDate = getCairoDateString(tab === 'yesterday' ? -1 : (tab === 'tomorrow' ? 1 : 0));
    return matches.filter(m => {
        if (!m.match_date) {
            // Default to today if date is missing
            return tab === 'today';
        }
        return m.match_date === targetDate;
    });
}

// Update the display badge for current selected date
function updateDateBadge() {
    const badge = document.getElementById('current-date');
    if (!badge) return;
    
    const d = new Date();
    const utc = d.getTime() + (d.getTimezoneOffset() * 60000);
    const cairoTime = new Date(utc + (3600000 * 3));
    
    let offset = 0;
    if (activeTab === 'yesterday') offset = -1;
    if (activeTab === 'tomorrow') offset = 1;
    
    cairoTime.setDate(cairoTime.getDate() + offset);
    
    badge.innerText = cairoTime.toLocaleDateString('ar-EG', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    });
}

// Render filtered matches
function displayMatchesForActiveTab() {
    const container = document.getElementById('matches-container');
    const noMatches = document.getElementById('no-matches');
    
    const filtered = filterMatchesByTab(allMatches, activeTab);
    
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
    // Set current date badge
    updateDateBadge();
    
    // Setup Tab click handlers
    document.querySelectorAll('.date-tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.date-tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            activeTab = btn.getAttribute('data-tab');
            updateDateBadge();
            displayMatchesForActiveTab();
        });
    });
    
    // Load Matches
    fetchMatches();
    
    // Setup manual refresh or auto-reload every 60 seconds
    setInterval(fetchMatches, 60000);
    
    // Setup Ad Banner Auto-Refresh
    startAdRefreshTimer();
    
    // Initialize Popunder Ads
    initPopunderAd();
    
    // Load Social Bar Ad dynamically
    loadSocialBar();
    
    // Close Player Event
    document.getElementById('close-player').addEventListener('click', closePlayer);
    
    // Fullscreen Player Event
    const fsBtn = document.getElementById('fullscreen-player');
    if (fsBtn) {
        fsBtn.addEventListener('click', toggleWrapperFullscreen);
    }
    
    // Overlay Ad Event (Guarantees direct link clicks)
    const overlayAd = document.getElementById('player-overlay-ad');
    const closeOverlayBtn = document.getElementById('close-overlay-btn');
    
    if (closeOverlayBtn) {
        closeOverlayBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // Don't trigger the overlay ad click
            overlayAd.classList.add('hidden');
            const videoEl = document.getElementById('native-video-player');
            if (videoEl) videoEl.play().catch(() => {});
        });
    }
    
    if (overlayAd) {
        overlayAd.addEventListener('click', (e) => {
            // Don't trigger if close button was clicked
            if (e.target.closest('#close-overlay-btn')) return;
            const url = ADS_CONFIG.popunder.directLinkUrl;
            if (url) {
                console.log("[Ad Manager] Overlay clicked. Opening direct link...");
                window.open(url, '_blank');
            }
            overlayAd.classList.add('hidden');
            const videoEl = document.getElementById('native-video-player');
            if (videoEl) videoEl.play().catch(() => {});
        });
    }

    // External Stream Link Event (opens only the stream link to avoid popup blockers)
    const extLink = document.getElementById('external-stream-link');
    if (extLink) {
        extLink.addEventListener('click', (e) => {
            // Stop propagation to prevent the global popunder handler from opening an ad tab
            e.stopPropagation();
            console.log("[Player Manager] Opening external stream tab natively...");
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
        
        const matches = await response.json();
        allMatches = matches; // Store globally
        spinner.classList.add('hidden');
        
        displayMatchesForActiveTab();
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

// Render Individual Match Card
function renderMatchCard(match) {
    let statusClass = 'upcoming';
    let statusText = match.status;
    let pulseHtml = '';
    let watchBtnText = 'شاهد الآن';
    
    if (match.status === 'جارية الآن') {
        statusClass = 'live';
        statusText = 'بث مباشر';
        pulseHtml = '<span class="status-indicator"></span>';
    } else if (match.status === 'انتهت') {
        statusClass = 'finished';
        statusText = 'انتهت';
        watchBtnText = 'شاهد الملخص والاهداف الآن';
    }
    
    // Handle logo fallbacks
    const logoA = match.logoA || 'https://mediayk.gemini.media/img/yallakora/iosteams/YK-Generic-team-logo.png';
    const logoB = match.logoB || 'https://mediayk.gemini.media/img/yallakora/iosteams/YK-Generic-team-logo.png';
    
    // Escaping single quotes in match.id to prevent inline click handler syntax errors
    const escapedMatchId = match.id.replace(/'/g, "\\'");
    
    return `
        <div class="match-card" onclick="openMatchStream('${escapedMatchId}')">
            <div class="match-top">
                <span class="match-badge ${statusClass}">${pulseHtml} ${statusText}</span>
                <span class="match-round">${match.round || ''}</span>
            </div>
            <div class="match-teams">
                <div class="team">
                    <img class="team-logo" src="${logoA}" alt="${match.teamA}" onerror="this.src='https://mediayk.gemini.media/img/yallakora/iosteams/YK-Generic-team-logo.png'">
                    <span class="team-name">${match.teamA}</span>
                </div>
                <div class="match-score-center">
                    <div class="score-display">${match.scoreA} - ${match.scoreB}</div>
                    <div class="match-time">${formatMatchTime(match.time)}</div>
                </div>
                <div class="team">
                    <img class="team-logo" src="${logoB}" alt="${match.teamB}" onerror="this.src='https://mediayk.gemini.media/img/yallakora/iosteams/YK-Generic-team-logo.png'">
                    <span class="team-name">${match.teamB}</span>
                </div>
            </div>
            <div class="match-bottom">
                <div class="channel-info">
                    <i class="fa-solid fa-tv"></i>
                    <span>${match.channel || 'صوتية/غير معروفة'}</span>
                </div>
                <button class="watch-now-btn">${watchBtnText} <i class="fa-solid fa-circle-play"></i></button>
            </div>
        </div>
    `;
}

// Open Live Stream Player
async function openMatchStream(matchId) {
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
    const iframe = document.getElementById('iframe-player');
    const videoPlayerDiv = document.getElementById('video-player');
    const tabsContainer = document.getElementById('sources-tabs');
    
    // Clear active match and stop polling
    activeMatchId = null;
    activeSourceIndex = -1;
    currentSources = [];
    retryCount = 0;
    stopBackgroundPolling();
    
    // Hide section & overlay
    playerSection.classList.add('hidden');
    tabsContainer.classList.add('hidden');
    hidePlayerToast();
    
    const overlayAd = document.getElementById('player-overlay-ad');
    if (overlayAd) overlayAd.classList.add('hidden');

    const extContainer = document.getElementById('external-stream-container');
    if (extContainer) extContainer.classList.add('hidden');
    
    // Reset document title to default
    document.title = "يلا شوت توداي - جدول المباريات والبث المباشر";
    
    // Stop iframe stream
    iframe.src = '';
    
    // Destroy HLS Instance
    if (hlsPlayer) {
        hlsPlayer.destroy();
        hlsPlayer = null;
    }
    
    // Clear inner html of player div
    videoPlayerDiv.innerHTML = '';
}

// Rotating Direct Link Offers under Video Player (High CPM conversion)
const DIRECT_LINK_OFFERS = [
    {
        title: "🎁 توقع نتيجة المباراة مجاناً واربح مكافأة 130$!",
        desc: "استخدم الرمز الترويجي YALLALIVE للحصول على بونص التسجيل الفوري مع 1XBET.",
        btnText: "سجل واربح الآن",
        icon: "fa-gift"
    },
    {
        title: "🔥 اشترك في القناة الرسمية لمشاهدة بدون تقطيع وبأعلى جودة!",
        desc: "البث المباشر والملخصات والأهداف تصلك فوراً على تليجرام مجاناً.",
        btnText: "انضم الآن",
        icon: "fa-bell"
    },
    {
        title: "⚡ حمل تطبيق مشاهدة مباريات اليوم مجاناً للأندرويد والآيفون!",
        desc: "تطبيق خفيف وسريع يعرض البث المباشر لجميع المباريات والبطولات.",
        btnText: "تحميل التطبيق",
        icon: "fa-download"
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
                
                adContainer2.innerHTML = `
                    <div class="simulated-ad">
                        <div class="ad-icon"><i class="fa-solid ${offer.icon}"></i></div>
                        <div class="ad-text">
                            <strong>${offer.title}</strong>
                            <p>${offer.desc}</p>
                        </div>
                        <a href="${ADS_CONFIG.popunder.directLinkUrl}" target="_blank" class="ad-btn">${offer.btnText} <i class="fa-solid fa-arrow-left"></i></a>
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

// Toggle custom wrapper fullscreen (including video + ads)
function toggleWrapperFullscreen() {
    const wrapper = document.querySelector('.player-wrapper');
    const fsBtn = document.getElementById('fullscreen-player');
    
    if (!document.fullscreenElement) {
        const req = wrapper.requestFullscreen || wrapper.webkitRequestFullscreen || wrapper.msRequestFullscreen;
        if (req) {
            req.call(wrapper).then(() => {
                if (fsBtn) fsBtn.innerHTML = '<i class="fa-solid fa-compress"></i> إلغاء التكبير';
            }).catch(err => {
                console.log("Fullscreen request rejected:", err);
            });
        }
    } else {
        const exit = document.exitFullscreen || document.webkitExitFullscreen || document.msExitFullscreen;
        if (exit) {
            exit.call(document).then(() => {
                if (fsBtn) fsBtn.innerHTML = '<i class="fa-solid fa-expand"></i> ملء الشاشة';
            }).catch(err => {
                console.log("Exit fullscreen failed:", err);
            });
        }
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
