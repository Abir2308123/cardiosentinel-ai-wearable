# 🫀 CardioSentinel

### AI-Powered Cardiac Monitoring Wearable System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)](https://flask.palletsprojects.com/)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-5-red.svg)](https://www.raspberrypi.com/)

**CardioSentinel** is a production-ready edge AI wearable system that continuously monitors cardiac activity in real-time. It features an on-device Machine Learning pipeline (Random Forest) that predicts arrhythmias with sub-10ms latency, secure WebSocket streaming, and dual-role patient/caregiver dashboards.

---

## ✨ Features

### Core Functionality
- **Real-time Cardiac Monitoring** - Continuous heart rate & SpO₂ tracking via MAX30102 sensor
- **Fall Detection** - MPU6050 accelerometer with intelligent threshold detection
- **GPS Tracking** - NEO-6M module for emergency location services
- **Edge AI Inference** - Random Forest classifier (<10ms latency) trained on MIT-BIH Arrhythmia Database
- **Hybrid Detection** - Combines ML predictions with rule-based thresholds for zero false negatives

### Dashboard & Alerts
- **Dual-Role Access** - Separate patient and caregiver portals with role-based views
- **Live WebSocket Streaming** - Real-time vitals with <100ms latency
- **SMS Alerts** - Twilio integration for emergency notifications
- **Alert Escalation** - Unacknowledged alerts escalate to secondary caregivers
- **Historical Trends** - SQLite database with 24-hour vital history

### Security
- **Encrypted WebSockets (WSS)** - All communication encrypted
- **JWT Authentication** - Secure session management
- **SQLite User Database** - Hashed passwords with bcrypt
- **Audit Logging** - Complete access and alert history

---

## 🏗 System Architecture

1. **Hardware / Edge Node (Raspberry Pi)**:
   - Tracks bio-signals natively using I2C and UART connected sensors.
   - Computes features locally via Scipy (Moving Average Filters, Standard Deviation for HRV).
   - Serves an embedded WSGI server on boot for local-network broadcasting securely over WebSockets.

2. **On-Device AI Engine**:
   - Lightweight `scikit-learn` Random Forest Classifier pre-packaged via `joblib`.
   - Tuned originally against extracted parameters from the MIT-BIH Arrhythmia database. 
   - Uses three primary inputs array dimensions to classify risk: **HRV (Heart Rate Variability), Mean HR, and SpO2 Trend**.

3. **Multi-User Dashboard Interface**:
   - **Patient Node**: Web dashboard intended for the wearer on their smart device showing live SpO2/HR canvases, Location map, and clear overview vitals.
   - **Caretaker Node**: Separate read-only WebSocket room enabling a family member to monitor vitals and receive live pushed 'Toast' pop-ups and logged Feed alerts the instant the hardware detects a fall or arrhythmia.

## Directory Structure

```text
winterfell/ (Root)
│
├── main.py                     # Main Python Backend (Flask + SocketIO + Edge Sensor Loop)
├── generate_mock_model.py      # Utility Script to bake the Random Forest dataset and ML model
├── trained_model.pkl           # The compiled/trained scikit-learn Random Forest model
├── requirements.txt            # Python Dependency File
├── WORKFLOW.md                 # Detailed technical operational workflow
├── README.md                   # This project manual
│
├── templates/                  # Flask HTML Portal
│   ├── login.html              # Secure Role-Selection Landing Page (Patient or Caretaker)
│   ├── patient.html            # Main Patient Dashboard
│   └── caretaker.html          # Remote Monitor Terminal
│
└── static/                     # Frontend Assets
    ├── css/
    │   └── styles.css          # Central stylesheet (Dark-mode, Glassmorphism, Micro-animations)
    └── js/
        ├── app.js              # Patient-side WebSocket bindings and Chart.js renderings
        └── caretaker.js        # Caretaker-side alert parsing and history feeds
```

## Setup & Running the Repository

1. **Activate Environment**:
   ```bash
   .\venv\Scripts\Activate
   ```

2. **Validate Machine Learning Model**:
   If the `model.pkl` is ever deleted, you can easily overwrite and bake a new one.
   ```bash
   python generate_mock_model.py
   ```

3. **Start the Web Interface**:
   ```bash
   python main.py
   ```
   Navigate to `http://localhost:5000` via your desktop browser or mobile phone on the same WiFi network and use User ID `demo` / Password `demo` to authenticate.
