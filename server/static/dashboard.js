const socket = io();

// DOM Elements
const statusDot = document.getElementById('socket-status-dot');
const statusText = document.getElementById('socket-status-text');

const hrVal = document.getElementById('val-hr');
const spo2Val = document.getElementById('val-spo2');
const spo2Ring = document.getElementById('spo2-ring');
const hrvVal = document.getElementById('val-hrv');
const motionVal = document.getElementById('val-motion');

const latVal = document.getElementById('val-lat');
const lngVal = document.getElementById('val-lng');

const arrhyVal = document.getElementById('val-arrhythmia');
const arrhyIcon = document.getElementById('icon-arrhythmia');
const arrhyPanel = document.getElementById('arrhythmia-status-panel');

const fallVal = document.getElementById('val-fall');
const fallIcon = document.getElementById('icon-fall');
const fallPanel = document.getElementById('fall-status-panel');

// Chart Setup
const ctx = document.getElementById('hrChart').getContext('2d');
Chart.defaults.color = '#94a3b8';
Chart.defaults.font.family = 'Outfit';

const gradient = ctx.createLinearGradient(0, 0, 0, 400);
gradient.addColorStop(0, 'rgba(244, 63, 94, 0.5)');   
gradient.addColorStop(1, 'rgba(244, 63, 94, 0.0)');

const hrChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: Array(30).fill(''),
        datasets: [{
            label: 'Heart Rate',
            data: Array(30).fill(null),
            borderColor: '#f43f5e',
            backgroundColor: gradient,
            borderWidth: 2,
            tension: 0.4,
            fill: true,
            pointRadius: 0,
            pointHoverRadius: 4
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false }
        },
        scales: {
            x: {
                display: false,
                grid: { display: false }
            },
            y: {
                min: 40,
                max: 180,
                grid: {
                    color: 'rgba(255, 255, 255, 0.05)',
                    drawBorder: false
                }
            }
        },
        animation: {
            duration: 0 // Disable animation for performance on high update rates
        }
    }
});

// Socket Events
socket.on('connect', () => {
    statusDot.className = 'status-dot connected';
    statusText.textContent = 'Live';
});

socket.on('disconnect', () => {
    statusDot.className = 'status-dot disconnected';
    statusText.textContent = 'Disconnected';
});

socket.on('telemetry_update', (data) => {
    // Update simple values
    hrVal.textContent = data.heart_rate || '--';
    hrvVal.textContent = data.hrv || '--';
    motionVal.textContent = (data.motion_energy || 0).toFixed(2);
    
    // SpO2 Ring calculation
    const spo2 = data.spo2 || 0;
    spo2Val.textContent = spo2 > 0 ? spo2 : '--';
    const radius = 54;
    const circumference = radius * 2 * Math.PI;
    const offset = circumference - (spo2 / 100) * circumference;
    spo2Ring.style.strokeDashoffset = spo2 > 0 ? offset : circumference;

    // GPS
    latVal.textContent = (data.lat && data.lat !== 0) ? data.lat.toFixed(6) : 'Searching...';
    lngVal.textContent = (data.lng && data.lng !== 0) ? data.lng.toFixed(6) : 'Searching...';

    // Chart Update
    if (data.heart_rate) {
        const hData = hrChart.data.datasets[0].data;
        hData.push(data.heart_rate);
        hData.shift();
        hrChart.update();
    }

    // Arrhythmia Risk UI
    if (data.arrhythmia_risk) {
        arrhyVal.textContent = `High Risk (${data.risk_level})`;
        arrhyIcon.className = 'fa-solid fa-triangle-exclamation';
        arrhyPanel.classList.add('danger-bg');
    } else {
        arrhyVal.textContent = 'Normal';
        arrhyIcon.className = 'fa-solid fa-circle-check';
        arrhyPanel.classList.remove('danger-bg');
    }

    // Fall Detection UI
    if (data.fall_detected) {
        fallVal.textContent = 'FALL DETECTED!';
        fallIcon.className = 'fa-solid fa-person-falling';
        fallPanel.classList.add('danger-bg');
    } else {
        fallVal.textContent = 'Monitoring';
        fallIcon.className = 'fa-solid fa-person-walking';
        fallPanel.classList.remove('danger-bg');
    }
});
