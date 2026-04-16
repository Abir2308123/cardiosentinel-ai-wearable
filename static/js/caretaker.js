// ===== CARETAKER DASHBOARD JS =====

// ----- Tab Navigation -----
const tabs = document.querySelectorAll('.nav-tab');
const contents = document.querySelectorAll('.tab-content');
const pageTitle = document.getElementById('pageTitle');

const tabTitles = {
    vitals: 'Patient Vitals',
    alerts: 'Alerts & Notifications',
    tracking: 'Patient Tracking'
};

let unreadAlerts = 0;

let caretakerMap = null;
let caretakerMarker = null;
const OSM_TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
const DEFAULT_LAT = 48.1173;
const DEFAULT_LNG = 11.5167;

function initMap() {
    if (caretakerMap) {
        caretakerMap.invalidateSize();
        return;
    }
    caretakerMap = L.map('caretakerMap', {
        zoomControl: true,
        attributionControl: true
    }).setView([DEFAULT_LAT, DEFAULT_LNG], 15);

    L.tileLayer(OSM_TILE_URL, {
        attribution: '&copy; <a href="https://master.apis.dev.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19
    }).addTo(caretakerMap);

    const cyberIcon = L.divIcon({
        className: 'custom-marker',
        html: '<div style="background:#00f0ff;width:18px;height:18px;border-radius:50%;box-shadow:0 0 20px #00f0ff,0 0 40px rgba(0,240,255,0.3);border:2px solid #fff;"></div>',
        iconSize: [18, 18],
        iconAnchor: [9, 9]
    });
    caretakerMarker = L.marker([DEFAULT_LAT, DEFAULT_LNG], {icon: cyberIcon}).addTo(caretakerMap);

    setTimeout(() => caretakerMap.invalidateSize(), 200);
    setTimeout(() => caretakerMap.invalidateSize(), 500);
}

tabs.forEach(tab => {
    tab.addEventListener('click', () => {
        const target = tab.dataset.tab;

        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        contents.forEach(c => c.classList.remove('active'));
        const targetContent = document.getElementById('content' + target.charAt(0).toUpperCase() + target.slice(1));
        if (targetContent) targetContent.classList.add('active');

        pageTitle.textContent = tabTitles[target] || 'Dashboard';

        // Clear badge when viewing alerts tab
        if (target === 'alerts') {
            unreadAlerts = 0;
            updateAlertBadge();
        }

        // Resize chart
        if (target === 'vitals') {
            setTimeout(() => { ctHrChart.resize(); }, 50);
        }
        if (target === 'tracking') {
            setTimeout(() => { 
                initMap(); 
                if (caretakerMap) caretakerMap.invalidateSize(); 
            }, 100);
        }
    });
});

// ----- Live Clock -----
function updateClock() {
    const now = new Date();
    const el = document.getElementById('liveTime');
    if (el) el.textContent = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}
setInterval(updateClock, 1000);
updateClock();

// ----- Chart.js Setup -----
const MAX_DATA_POINTS = 60;
const ctHrData = new Array(MAX_DATA_POINTS).fill(null);
const labels = new Array(MAX_DATA_POINTS).fill('');

Chart.defaults.color = '#6b6b80';
Chart.defaults.font.family = 'Inter';

const ctHrChart = new Chart(
    document.getElementById('ctHrChart').getContext('2d'),
    {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                data: ctHrData,
                borderColor: '#ff4757',
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.35,
                fill: true,
                backgroundColor: (ctx) => {
                    const gradient = ctx.chart.ctx.createLinearGradient(0, 0, 0, ctx.chart.height);
                    gradient.addColorStop(0, 'rgba(255, 71, 87, 0.35)');
                    gradient.addColorStop(1, 'rgba(0,0,0,0)');
                    return gradient;
                }
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 0 },
            plugins: { legend: { display: false }, tooltip: { enabled: false } },
            scales: {
                x: { display: false },
                y: { min: 40, max: 180, border: { display: false }, grid: { color: 'rgba(255,255,255,0.03)' } }
            }
        }
    }
);

// ----- WebSocket -----
const socket = io();

socket.on('connect', () => {
    console.log('Caretaker WebSocket connected.');
    socket.emit('join', { role: 'caretaker' });
    document.getElementById('errorOverlay').classList.add('hidden');
    setConnectionStatus(true);
});

socket.on('disconnect', () => {
    setConnectionStatus(false);
    showError('Connection to patient device lost');
});

socket.on('system_error', (data) => {
    showError(data.error);
});

// Live sensor data (same stream as patient, for read-only display)
socket.on('sensor_data', (data) => {
    // Chart
    ctHrData.push(data.raw_hr); ctHrData.shift();
    ctHrChart.update();

    // Vitals
    setText('ctHR', data.mean_hr.toFixed(0));
    setText('ctSpO2', data.spo2.toFixed(1));

    // Status Card
    const statusCard = document.getElementById('statusCard');
    const statusValue = document.getElementById('statusValue');
    statusCard.classList.remove('status-normal', 'status-abnormal');
    if (data.status === 'Normal') {
        statusCard.classList.add('status-normal');
        statusValue.textContent = 'NORMAL';
    } else {
        statusCard.classList.add('status-abnormal');
        statusValue.textContent = 'RISK DETECTED';
    }

    // Fall
    const ctFall = document.getElementById('ctFall');
    if (data.fall_detected) {
        ctFall.textContent = 'FALL DETECTED!';
        ctFall.style.color = '#ff4757';
    } else {
        ctFall.textContent = 'All Clear';
        ctFall.style.color = '';
    }

    // Location
    setText('ctLocation', data.location);
    setText('ctGpsTime', data.timestamp || '--');
    
    if (caretakerMarker && data.location.includes('N')) {
        const lat = 48.1173 + (Math.random() - 0.5) * 0.0005;
        const lng = 11.5167 + (Math.random() - 0.5) * 0.0005;
        
        setText('ctGpsLocation', `${lat.toFixed(4)}°N, ${lng.toFixed(4)}°E`);
        caretakerMarker.setLatLng([lat, lng]);
        caretakerMap.panTo([lat, lng], {animate: true});
        
        // OpenStreetMap API Reverse Geocoding (throttled)
        if (!window.lastGeocodeTime || Date.now() - window.lastGeocodeTime > 15000) {
            window.lastGeocodeTime = Date.now();
            fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`)
                .then(res => res.json())
                .then(apiData => {
                    if (apiData && apiData.display_name) {
                        setText('ctLocation', apiData.display_name.split(',').slice(0,2).join(', '));
                    }
                }).catch(err => console.log('OSM API Error:', err));
        }
    } else {
        setText('ctGpsLocation', data.location);
    }
});

// Real-time alert notifications from server
socket.on('caretaker_alert', (alert) => {
    addAlertToFeed(alert);
    showToast(alert);

    // Increment badge if not on alerts tab
    const alertsTab = document.getElementById('tabAlerts');
    if (!alertsTab.classList.contains('active')) {
        unreadAlerts++;
        updateAlertBadge();
    }
});

// ----- Alert Feed -----
function addAlertToFeed(alert) {
    const feed = document.getElementById('alertsFeed');

    // Remove empty state if present
    const empty = feed.querySelector('.empty-alerts');
    if (empty) empty.remove();

    const isCritical = alert.message.includes('EMERGENCY') || alert.message.includes('Fall');
    const item = document.createElement('div');
    item.className = `alert-item ${isCritical ? 'critical' : 'warning'}`;
    item.innerHTML = `
        <div class="alert-dot ${isCritical ? 'red' : 'orange'}"></div>
        <div class="alert-body">
            <div class="alert-msg">${escapeHtml(alert.message)}</div>
            <div class="alert-time">${alert.time}</div>
        </div>
    `;

    // Prepend (newest on top)
    feed.insertBefore(item, feed.firstChild);

    // Cap visible alerts
    while (feed.children.length > 50) {
        feed.removeChild(feed.lastChild);
    }
}

function updateAlertBadge() {
    const badge = document.getElementById('alertBadge');
    if (unreadAlerts > 0) {
        badge.textContent = unreadAlerts > 9 ? '9+' : unreadAlerts;
        badge.classList.remove('hidden');
    } else {
        badge.classList.add('hidden');
    }
}

// Clear all alerts
document.getElementById('clearAlerts').addEventListener('click', () => {
    const feed = document.getElementById('alertsFeed');
    feed.innerHTML = `
        <div class="empty-alerts">
            <span class="empty-icon">🔕</span>
            <p>No alerts yet. You'll be notified here in real-time if any anomaly or fall is detected.</p>
        </div>
    `;
    unreadAlerts = 0;
    updateAlertBadge();
});

// Load existing alerts on page load
fetch('/api/alerts')
    .then(res => res.json())
    .then(alerts => {
        if (alerts.length > 0) {
            alerts.forEach(a => addAlertToFeed(a));
        }
    })
    .catch(err => console.warn('Could not load alert history:', err));

// ----- Toast Notifications -----
function showToast(alert) {
    const container = document.getElementById('toastContainer');
    const isCritical = alert.message.includes('EMERGENCY') || alert.message.includes('Fall');

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `
        <div class="toast-icon">${isCritical ? '🚨' : '⚠️'}</div>
        <div class="toast-body">
            <div class="toast-title">${isCritical ? 'EMERGENCY ALERT' : 'Health Warning'}</div>
            <div class="toast-msg">${escapeHtml(alert.message)}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;

    container.appendChild(toast);

    // Auto-dismiss after 8 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(30px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }
    }, 8000);
}

// ----- Helpers -----
function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

function setConnectionStatus(connected) {
    const dot = document.querySelector('.conn-dot');
    const text = document.getElementById('connectionText');
    if (connected) {
        dot.className = 'conn-dot connected';
        text.textContent = 'Connected';
    } else {
        dot.className = 'conn-dot disconnected';
        text.textContent = 'Disconnected';
    }
}

function showError(msg) {
    document.getElementById('errorMessage').textContent = msg;
    document.getElementById('errorOverlay').classList.remove('hidden');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
