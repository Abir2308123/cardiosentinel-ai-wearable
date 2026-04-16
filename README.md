# CardioSentinel: AI-Powered Cardiac Monitoring Wearable

CardioSentinel is a production-ready edge AI wearable system designed to track high-frequency cardiac and motion data in real time. It features an on-device Machine Learning pipeline that predicts cardiac anomalies (such as arrhythmias) with sub-10ms latency, securely streaming live diagnostics directly to dual-role patient and caregiver dashboards.

## Project Architecture

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

## Simulated "Mock Mode" Development Environment

The system was intentionally programmed with a fallback logic gate. If the Python backend boots on a Windows/Mac PC (or a Pi missing the `smbus2` libraries), the code traps the `ImportError` gracefully. It then generates incredibly realistic simulated JSON payloads for:
- Heart Rate (MAX30102 logic)
- Spo2 (MAX30102 logic)
- Motion & Fall Generation (Simulating a sudden force vector change from an MPU6050 accelerometer)
- NMEA Coordinates (Simulating NEO-6M UART interface streams)

**Note:** The system occasionally triggers a faux "Fall Detected" signal when in Mock Mode to explicitly demonstrate the alert mechanism propagating across the Caretaker WebSockets. 

## Component Breakdown

1. **`main.py`**:
   The brains of the project. It spins up a threaded loop `sensor_loop()` strictly parsing raw I2C bytes continually into human-readable data points, calculates metrics using `SignalProcessor` classes, pumps the math into `model.predict()`, and lastly pushes the entire `payload` dict array out dynamically through the `socketio.emit` channel specifically targeting the separate segmented socket rooms (`patients` vs `caretakers`). 
   It additionally houses the URL routing (`@app.route`) bridging the Login HTML portals securely.

2. **`generate_mock_model.py`**:
   Script that builds distinct arrays mimicking `Normal` vs `Hypoxia/Tachycardia` profiles. Binds target array answers into `RandomForestClassifier()` and outputs a finalized `model.pkl`.

3. **`static/css/styles.css`**: 
   Houses all design variables (`--bg-color`, `--accent-red`). It is heavily segmented by tabs (`.overview-grid`) and utilizes custom animated responsive overlays (e.g., CSS `@keyframes` on the fallback alert dot pulses and `toastIn` sliding notifications).

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
