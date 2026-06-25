// API Configuration
// Replace this URL with your actual Hugging Face Space API URL once deployed!
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://127.0.0.1:7860'
    : 'https://mmossad824-sports-bot.hf.space'; 

let clapprPlayer = null;

// Initialize Page
document.addEventListener('DOMContentLoaded', () => {
    // Set current date
    const dateOptions = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', calendar: 'islamic' };
    const today = new Date();
    document.getElementById('current-date').innerText = today.toLocaleDateString('ar-EG', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    
    // Load Matches
    fetchMatches();
    
    // Setup manual refresh or auto-reload every 60 seconds
    setInterval(fetchMatches, 60000);
    
    // Setup Ad Banner Auto-Refresh
    startAdRefreshTimer();
    
    // Close Player Event
    document.getElementById('close-player').addEventListener('click', closePlayer);
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
        spinner.classList.add('hidden');
        
        if (matches.length === 0) {
            noMatches.classList.remove('hidden');
            container.innerHTML = '';
            return;
        }
        
        noMatches.classList.add('hidden');
        renderMatches(matches);
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

// Render Individual Match Card
function renderMatchCard(match) {
    let statusClass = 'upcoming';
    let statusText = match.status;
    let pulseHtml = '';
    
    if (match.status === 'جارية الآن') {
        statusClass = 'live';
        statusText = 'بث مباشر';
        pulseHtml = '<span class="status-indicator"></span>';
    } else if (match.status === 'انتهت') {
        statusClass = 'finished';
        statusText = 'انتهت';
    }
    
    // Handle logo fallbacks
    const logoA = match.logoA || 'https://mediayk.gemini.media/img/yallakora/iosteams/YK-Generic-team-logo.png';
    const logoB = match.logoB || 'https://mediayk.gemini.media/img/yallakora/iosteams/YK-Generic-team-logo.png';
    
    return `
        <div class="match-card" onclick="openMatchStream('${match.id}')">
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
                    <div class="match-time">${match.time}</div>
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
                <button class="watch-now-btn">شاهد الآن <i class="fa-solid fa-circle-play"></i></button>
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
    
    // Clear previous players
    closePlayer();
    
    // Scroll to player
    playerSection.classList.remove('hidden');
    playerSection.scrollIntoView({ behavior: 'smooth' });
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/matches/${matchId}`);
        if (!response.ok) throw new Error('Match detail fetch failed');
        
        const match = await response.json();
        
        // Update footer details
        document.getElementById('player-title').innerText = `بث مباشر: ${match.teamA} VS ${match.teamB}`;
        document.getElementById('footer-team-a').innerText = match.teamA;
        document.getElementById('footer-team-b').innerText = match.teamB;
        document.getElementById('footer-channel').innerHTML = `<i class="fa-solid fa-tv"></i> القناة الناقلة: ${match.channel || 'غير معروفة'}`;
        document.getElementById('footer-status').innerHTML = `<i class="fa-solid fa-circle-dot"></i> الحالة: ${match.status}`;
        
        // If match finished, tell the user
        if (match.status === 'انتهت') {
            placeholder.classList.remove('hidden');
            placeholder.querySelector('h3').innerText = 'انتهت المباراة';
            placeholder.querySelector('p').innerText = 'الملخصات واللقطات ستكون متوفرة على قناتنا في تليجرام.';
            return;
        }
        
        // Check if stream link exists
        if (!match.stream_url) {
            placeholder.classList.remove('hidden');
            placeholder.querySelector('h3').innerText = 'البث المباشر غير متوفر حالياً';
            placeholder.querySelector('p').innerText = 'يبدأ البث قبل انطلاق المباراة بـ 15 دقيقة. يرجى الانتظار والتحديث.';
            return;
        }
        
        placeholder.classList.add('hidden');
        
        // Play Stream based on Type
        if (match.stream_type === 'hls') {
            videoPlayerDiv.classList.remove('hidden');
            iframeContainer.classList.add('hidden');
            
            // Initialize Clappr Player for HLS (.m3u8)
            clapprPlayer = new Clappr.Player({
                source: match.stream_url,
                parentId: "#video-player",
                width: '100%',
                height: '100%',
                autoPlay: true,
                mute: false,
                mimeType: "application/x-mpegURL"
            });
        } else if (match.stream_type === 'iframe') {
            videoPlayerDiv.classList.add('hidden');
            iframeContainer.classList.remove('hidden');
            document.getElementById('iframe-player').src = match.stream_url;
        }
        
    } catch (error) {
        console.error('Error opening stream:', error);
        placeholder.classList.remove('hidden');
        placeholder.querySelector('h3').innerText = 'خطأ في تشغيل البث';
    }
}

// Close and clean up video player
function closePlayer() {
    const playerSection = document.getElementById('player-section');
    const iframe = document.getElementById('iframe-player');
    const videoPlayerDiv = document.getElementById('video-player');
    
    // Hide section
    playerSection.classList.add('hidden');
    
    // Stop iframe stream
    iframe.src = '';
    
    // Destroy Clappr Instance
    if (clapprPlayer) {
        clapprPlayer.destroy();
        clapprPlayer = null;
    }
    
    // Clear inner html of player div
    videoPlayerDiv.innerHTML = '';
}

// Monetization: Auto-Refresh Banner Ads (Safe & Policy-Compliant)
function startAdRefreshTimer() {
    const adPool = [
        {
            title: "توقع نتيجة المباراة مجاناً واربح مكافأة ترحيبية 130$ مع 1XBET!",
            promo: "YALLALIVE",
            url: "https://1xbet.com",
            btn: "سجل الآن"
        },
        {
            title: "احصل على بونص إيداع 100% يصل لـ 200$ مع شركة Melbet الرياضية!",
            promo: "SPORTSBOT",
            url: "https://melbet.com",
            btn: "احصل على البونص"
        },
        {
            title: "قناتنا الرسمية في تليجرام تغطي الأهداف والملخصات لحظة بلحظة!",
            promo: "رابط القناة",
            url: "https://t.me/your_channel",
            btn: "اشترك الآن"
        }
    ];
    
    let adIndex = 0;
    
    // Refresh Ad every 3 minutes (180000 milliseconds)
    setInterval(() => {
        const adContainer = document.getElementById('banner-ad-container');
        if (!adContainer) return;
        
        adIndex = (adIndex + 1) % adPool.length;
        const currentAd = adPool[adIndex];
        
        console.log(`[Ad Manager] Refreshing banner slot to Ad Index: ${adIndex}`);
        
        // In a real network implementation, you would do:
        // adContainer.innerHTML = '';
        // const script = document.createElement('script');
        // script.src = 'https://www.highperformanceformat.com/YOUR_ZONE_ID/invoke.js';
        // adContainer.appendChild(script);
        
        // For our simulated high-conversion banner:
        adContainer.style.opacity = 0;
        
        setTimeout(() => {
            adContainer.innerHTML = `
                <div class="simulated-ad">
                    <div class="ad-icon"><i class="fa-solid fa-bullhorn"></i></div>
                    <div class="ad-text">
                        <strong>${currentAd.title}</strong>
                        <p>استخدم الرمز الترويجي: <code>${currentAd.promo}</code> للحصول على العرض فوراً.</p>
                    </div>
                    <a href="${currentAd.url}" target="_blank" class="ad-btn">${currentAd.btn} <i class="fa-solid fa-arrow-left"></i></a>
                </div>
            `;
            adContainer.style.opacity = 1;
        }, 300);
        
    }, 180000); // 3 minutes refresh rate
}
