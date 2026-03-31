const socket = io();

const sysStatus = document.getElementById('system-status');
const initBtn = document.getElementById('init-btn');
const btnText = document.getElementById('btn-text');
const sessionTimer = document.getElementById('session-timer');
const deviationsCount = document.getElementById('deviations-count');

const feedStatus = document.getElementById('feed-status');
const offlineState = document.getElementById('offline-state');
const videoStream = document.getElementById('video-stream');
const recIndicator = document.getElementById('rec-indicator');

let isSystemActive = false;

// Socket.io listeners
socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('update_metrics', (data) => {
    // data: { status: str, deviations: int, timer: str }
    deviationsCount.innerText = data.deviations;
    sessionTimer.innerText = data.timer;
    
    // Update Master Status Display based on state
    if (!isSystemActive) {
        sysStatus.innerText = "STANDBY";
        sysStatus.className = "status-display";
    } else {
        if (data.status === 'F') {
            sysStatus.innerText = "FOCUSED";
            sysStatus.className = "status-display monitoring";
        } else if (data.status === 'D') {
            sysStatus.innerText = "DISTRACTED";
            sysStatus.className = "status-display alert";
        } else if (data.status === 'E') {
            sysStatus.innerText = "DROWSY";
            sysStatus.className = "status-display alert";
        } else if (data.status === 'A') {
            sysStatus.innerText = "USER AWAY";
            sysStatus.className = "status-display";
            sysStatus.style.color = "#0055ff";
            sysStatus.style.textShadow = "0 0 10px #0055ff";
        } else {
            sysStatus.innerText = "MONITORING";
            sysStatus.className = "status-display monitoring";
        }
    }
});


// Toggle Button Logic
initBtn.addEventListener('click', async () => {
    try {
        const response = await fetch('/toggle_system', { method: 'POST' });
        const data = await response.json();
        
        isSystemActive = data.is_active;
        
        if (isSystemActive) {
            // UI Update for Active State
            btnText.innerText = "DEACTIVATE";
            initBtn.classList.add('active');
            initBtn.querySelector('i').className = "fa-solid fa-stop";
            
            feedStatus.innerText = "[LIVE]";
            feedStatus.style.color = "var(--neon-red)";
            
            offlineState.classList.add('hidden');
            videoStream.classList.remove('hidden');
            recIndicator.classList.remove('hidden');
            
            // Start video stream
            videoStream.src = "/video_feed?" + new Date().getTime(); // Anti-cache
            
        } else {
            // UI Update for Standby State
            btnText.innerText = "INITIALIZE";
            initBtn.classList.remove('active');
            initBtn.querySelector('i').className = "fa-solid fa-play";
            
            feedStatus.innerText = "[OFF]";
            feedStatus.style.color = "var(--border-dim)";
            
            offlineState.classList.remove('hidden');
            videoStream.classList.add('hidden');
            recIndicator.classList.add('hidden');
            
            // Kill video stream load
            videoStream.src = "";
            sysStatus.innerText = "STANDBY";
            sysStatus.className = "status-display";
            sysStatus.style.color = ""; // reset inline color
        }
    } catch (err) {
        console.error("Error toggling system:", err);
    }
});
