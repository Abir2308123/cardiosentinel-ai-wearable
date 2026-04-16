// ===== PATIENT DASHBOARD APP.JS =====

// ----- Tab Navigation -----
const tabs = document.querySelectorAll('.nav-tab');
const contents = document.querySelectorAll('.tab-content');
const pageTitle = document.getElementById('pageTitle');

const tabTitles = {
    overview: 'Overview',
    cardiac: 'Cardiac Monitoring',
    location: 'GPS Location'
};

let patientMap = null;
let patientMarker = null;
const OSM_TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
const DEFAULT_LAT = 48.1173;
const DEFAULT_LNG = 11.5167;

function initMap() {
    if (patientMap) {
        patientMap.invalidateSize();
        return;
    }
    patientMap = L.map('patientMap', {
        zoomControl: true,
        attributionControl: true
    }).setView([DEFAULT_LAT, DEFAULT_LNG], 15);

    // OpenStreetMap tile layer
    L.tileLayer(OSM_TILE_URL, {
        attribution: '&copy; <a href="https://master.apis.dev.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19
    }).addTo(patientMap);

    const cyberIcon = L.divIcon({
        className: 'custom-marker',
        html: '<div style="background:#00f0ff;width:18px;height:18px;border-radius:50%;box-shadow:0 0 20px #00f0ff,0 0 40px rgba(0,240,255,0.3);border:2px solid #fff;"></div>',
        iconSize: [18, 18],
        iconAnchor: [9, 9]
    });
    patientMarker = L.marker([DEFAULT_LAT, DEFAULT_LNG], {icon: cyberIcon}).addTo(patientMap);
    
    // Force re-render after the container is fully visible
    setTimeout(() => patientMap.invalidateSize(), 200);
    setTimeout(() => patientMap.invalidateSize(), 500);
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
        
        // Resize charts when switching to their tab
        if (target === 'cardiac') {
            setTimeout(() => { hrChart.resize(); spo2Chart.resize(); }, 50);
        }
        if (target === 'overview') {
            setTimeout(() => { miniHrChart.resize(); }, 50);
        }
        if (target === 'location') {
            setTimeout(() => { 
                initMap(); 
                if (patientMap) patientMap.invalidateSize(); 
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
const hrData = new Array(MAX_DATA_POINTS).fill(null);
const spo2Data = new Array(MAX_DATA_POINTS).fill(null);
const miniHrData = new Array(MAX_DATA_POINTS).fill(null);
const labels = new Array(MAX_DATA_POINTS).fill('');

Chart.defaults.color = '#6b6b80';
Chart.defaults.font.family = 'Inter';

function createChartConfig(dataArray, lineColor, gradientColor) {
    return {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                data: dataArray,
                borderColor: lineColor,
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.35,
                fill: true,
                backgroundColor: (ctx) => {
                    const gradient = ctx.chart.ctx.createLinearGradient(0, 0, 0, ctx.chart.height);
                    gradient.addColorStop(0, gradientColor);
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
                y: { border: { display: false }, grid: { color: 'rgba(255,255,255,0.03)' } }
            }
        }
    };
}

// Full HR Chart (Cardiac Tab)
const hrChart = new Chart(
    document.getElementById('hrChart').getContext('2d'),
    createChartConfig(hrData, '#ff4757', 'rgba(255, 71, 87, 0.4)')
);
hrChart.options.scales.y.min = 40;
hrChart.options.scales.y.max = 180;

// Full SpO2 Chart (Cardiac Tab)
const spo2Chart = new Chart(
    document.getElementById('spo2Chart').getContext('2d'),
    createChartConfig(spo2Data, '#1e90ff', 'rgba(30, 144, 255, 0.4)')
);
spo2Chart.options.scales.y.min = 80;
spo2Chart.options.scales.y.max = 100;

// Mini HR Chart (Overview Tab)
const miniHrChart = new Chart(
    document.getElementById('miniHrChart').getContext('2d'),
    createChartConfig(miniHrData, '#ff4757', 'rgba(255, 71, 87, 0.3)')
);
miniHrChart.options.scales.y.min = 40;
miniHrChart.options.scales.y.max = 180;

// ----- WebSocket -----
const socket = io();

socket.on('connect', () => {
    console.log('WebSocket connected.');
    socket.emit('join', { role: 'patient' });
    document.getElementById('errorOverlay').classList.add('hidden');
});

socket.on('disconnect', () => {
    showError('Connection to Edge Device Lost');
});

socket.on('system_error', (data) => {
    showError(data.error);
});

socket.on('sensor_data', (data) => {
    // Push chart data
    hrData.push(data.raw_hr); hrData.shift();
    spo2Data.push(data.raw_spo2); spo2Data.shift();
    miniHrData.push(data.raw_hr); miniHrData.shift();
    
    hrChart.update();
    spo2Chart.update();
    miniHrChart.update();
    
    // Overview tab metrics
    setText('overviewHR', data.mean_hr.toFixed(0));
    setText('overviewSpO2', data.spo2.toFixed(1));
    setText('overviewHRV', data.hrv.toFixed(1));
    setText('overviewLocation', data.location);
    setText('latency', data.latency_ms);
    
    // Cardiac tab metrics
    setText('meanHrValue', data.mean_hr.toFixed(0));
    setText('spo2Value', data.spo2.toFixed(1));
    
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
    
    // Fall detection (overview)
    const overviewFall = document.getElementById('overviewFall');
    if (data.fall_detected) {
        overviewFall.textContent = 'FALL DETECTED!';
        overviewFall.classList.add('fall-alert-text');
    } else {
        overviewFall.textContent = 'All Clear';
        overviewFall.classList.remove('fall-alert-text');
    }
    
    // GPS (location tab)
    if (patientMarker && data.location.includes('N')) {
        // Slight mock movement for testing
        const lat = 48.1173 + (Math.random() - 0.5) * 0.0005;
        const lng = 11.5167 + (Math.random() - 0.5) * 0.0005;
        
        setText('gpsLocation', `${lat.toFixed(4)}°N, ${lng.toFixed(4)}°E`);
        patientMarker.setLatLng([lat, lng]);
        patientMap.panTo([lat, lng], {animate: true});
        
        // OpenStreetMap API Reverse Geocoding (throttled)
        if (!window.lastGeocodeTime || Date.now() - window.lastGeocodeTime > 15000) {
            window.lastGeocodeTime = Date.now();
            fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`)
                .then(res => res.json())
                .then(apiData => {
                    if (apiData && apiData.display_name) {
                        setText('overviewLocation', apiData.display_name.split(',').slice(0,2).join(', '));
                    }
                }).catch(err => console.log('OSM API Error:', err));
        }
    } else {
        setText('gpsLocation', data.location);
    }
});

// ----- Helpers -----
function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

function showError(msg) {
    document.getElementById('errorMessage').textContent = msg;
    document.getElementById('errorOverlay').classList.remove('hidden');
}
