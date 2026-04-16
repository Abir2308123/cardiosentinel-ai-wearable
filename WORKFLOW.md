# CardioSentinel: Detailed Operational Workflow

This document outlines the end-to-end data pipeline and operational logic for the CardioSentinel Cardiac Monitoring System.

## 1. Data Acquisition Layer (Hardware/Edge)
The system initiates at the **Edge Node** (Raspberry Pi). The `sensor_loop` in `main.py` handles high-frequency polling:
- **Cardiac Data**: MAX30102 sensor reads raw Red/IR reflectometry via I2C.
- **Motion Data**: MPU6050 accelerometer tracks Y/Z gravitational vectors to detect impact (falls).
- **Location Data**: NEO-6M GPS modules stream NMEA-0183 sentences via UART/Serial.
- **Mock Mode**: If hardware is detached, the system injects Gaussian-noise-modulated synthetic signals to maintain pipeline continuity.

## 2. Signal Processing & Feature Extraction
Raw signals are piped into the `SignalProcessor` class:
- **Moving Average Filters**: Smooths jittery raw Heart Rate and SpO2 readings using a sliding window.
- **HRV Calculation**: Computes the Standard Deviation of NN-intervals (RR-intervals derived from the last heart peak time).
- **Motion Energy**: Transforms raw accelerometer bytes into a vector magnitude (`sqrt(y²+z²)`) representing physical intensity.

## 3. Real-Time AI Inference
The processed feature vector `[HR, SpO2, HRV, MotionEnergy]` is passed to the ML Engine:
- **Model**: A Scikit-Learn Random Forest Classifier (`trained_model.pkl`).
- **Execution**: `model.predict()` evaluates the vector in <10ms.
- **Fallback**: If the model file is missing or inference fails, a **Rule-Based Threshold System** takes over, ensuring the patient is never unmonitored.
- **Categorization**: Data is tagged as **Normal** or **Abnormal**.

## 4. Communication & Real-Time Sync
The backend uses **Flask-SocketIO** for ultra-low latency broadcasting:
- **WebSocket Rooms**: Users are segmented into `patients` and `caretakers` rooms.
- **Dynamic Emission**: 
    - Full sensor telemetry is sent to the patient's dashboard.
    - Mirror telemetry + Critical Alerts are pushed to caretakers.
- **Alert Logic**: If `status == "Abnormal"` or `fall_detected == True`, the `send_alert()` function is triggered, prepending a notification to the history feed and flashing UI "Toasts".

## 5. View Layer (Dual-Dashboard UI)
The frontend utilizes a modular, glassmorphism-based design:
- **Patient Interface (`app.js`)**:
    - Uses **Chart.js** with `requestAnimationFrame` for high-performance scrolling ECG/SpO2 waveforms.
    - Tabbed navigation allows the user to switch between Overview, Detailed Cardiac, and GPS Map views.
- **Caretaker Interface (`caretaker.js`)**:
    - **Notification Center**: Listens for `caretaker_alert` events to show non-intrusive popups.
    - **History Feed**: Maintains a persistent (per-session) list of recent anomalies.
    - **Live Tracker**: Displays the patient's GPS coordinates and vital markers.

---

## Technical Stack Summary
- **Backend**: Python 3, Flask, Flask-SocketIO, NumPy, Scikit-Learn, Joblib.
- **Frontend**: HTML5, Vanilla CSS3 (Custom Grid), JavaScript (ES6+), Chart.js.
- **Communication**: WebSockets (io), REST API (for alert history).
- **Inference**: Random Forest (On-Device).
