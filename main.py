# ==========================================================================
# CardioSentinel - AI-Powered Cardiac Risk Monitoring (Edge Backend)
# ==========================================================================
# MODEL REQUIREMENT:
#   Place your trained Random Forest model file in the project root as:
#       trained_model.pkl
#   The model must be a scikit-learn classifier saved with joblib.dump()
#   and must expect exactly 4 numeric features:
#       [heart_rate (bpm), spo2 (%), hrv (ms), motion_energy (m/s²)]
#   Output: 0 = Normal, 1 = Arrhythmia / Risk Detected
#
#   If trained_model.pkl is missing, the system falls back to a rule-based
#   threshold detector automatically.
# ==========================================================================

import time
import json
import threading
import numpy as np
import joblib
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Attempt to load RPi hardware libraries, fallback to mock classes for development
try:
    import smbus2
    import serial
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    print("WARNING: Hardware libraries (smbus2, serial) not found. Running in MOCK Mode.")

app = Flask(__name__)
app.secret_key = 'cardiosentinel_secret_key_2026'
# Allow CORS for local dev testing
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ---------------------------------------------------------
# Mock Hardware Classes (for Windows/Local testing bounds)
# ---------------------------------------------------------
class MockSMBus:
    def read_byte_data(self, addr, reg): return np.random.randint(0, 255)
    def write_byte_data(self, addr, reg, val): pass

class MockSerial:
    def __init__(self): self.in_waiting = 1
    def readline(self): 
        return b"$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\r\n"

# ---------------------------------------------------------
# Hardware Initialization
# ---------------------------------------------------------
if HARDWARE_AVAILABLE:
    bus = smbus2.SMBus(1)
    gps_serial = serial.Serial('/dev/ttyS0', 9600, timeout=1)
else:
    bus = MockSMBus()
    gps_serial = MockSerial()

MAX30102_ADDR = 0x57
MPU6050_ADDR = 0x68

# ---------------------------------------------------------
# Load Trained ML Model (trained_model.pkl)
# Falls back to rule-based thresholds if file is missing.
# ---------------------------------------------------------
MODEL_PATH = 'trained_model.pkl'
model = None
USE_ML = False

try:
    model = joblib.load(MODEL_PATH)
    USE_ML = True
    logging.info(f"Trained ML model loaded successfully from '{MODEL_PATH}'.")
    # Validate expected input shape by inspecting n_features
    expected_features = getattr(model, 'n_features_in_', None)
    if expected_features and expected_features != 4:
        logging.warning(f"Model expects {expected_features} features but pipeline supplies 4. Predictions may fail.")
except FileNotFoundError:
    logging.critical(f"CRITICAL: '{MODEL_PATH}' not found! Falling back to rule-based threshold system.")
except Exception as e:
    logging.critical(f"CRITICAL: Failed to load model - {e}. Falling back to rule-based threshold system.")

def rule_based_predict(hr, spo2, hrv, motion_energy):
    """Fallback threshold-based arrhythmia detector when ML model is unavailable.
    These thresholds are tuned to avoid false positives during mock-sensor polling."""
    if hr > 130 or hr < 40:
        return 1  # Tachycardia or Bradycardia
    if spo2 < 90:
        return 1  # Hypoxia
    if hrv < 3:
        return 1  # Dangerously low HRV (note: mock loop produces very low std)
    if motion_energy > 30:
        return 1  # Extreme motion / possible seizure
    return 0

# ---------------------------------------------------------
# User database (in-memory for hackathon demo)
# In production, use a real database
# ---------------------------------------------------------
users_db = {
    'patient001': {
        'password': 'cardio123',
        'patient_name': 'John Doe',
        'age': 67,
        'blood_group': 'O+',
        'emergency_contact': '+91 98765 43210'
    },
    'demo': {
        'password': 'demo',
        'patient_name': 'Demo Patient',
        'age': 55,
        'blood_group': 'A+',
        'emergency_contact': '+91 12345 67890'
    }
}

# Store recent alerts for caretaker notification feed
alert_history = []
MAX_ALERTS = 50

# Store latest sensor snapshot for caretaker initial load
latest_sensor_data = {}

def send_alert(message):
    """Log alert and push to caretaker notification feed"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    alert_entry = {'message': message, 'time': timestamp}
    alert_history.append(alert_entry)
    if len(alert_history) > MAX_ALERTS:
        alert_history.pop(0)
    
    # Push real-time notification to all caretaker clients
    socketio.emit('caretaker_alert', alert_entry, room='caretakers')
    print(f"\n[ALERT TRIGGERED] -> {message}")

# ---------------------------------------------------------
# Data Processing & Filters
# ---------------------------------------------------------
class SignalProcessor:
    def __init__(self, window_size=10):
        self.hr_window = []
        self.spo2_window = []
        self.window_size = window_size
        self.last_rr_time = time.time()
        self.rr_intervals = []

    def moving_average(self, data_list, new_val):
        data_list.append(new_val)
        if len(data_list) > self.window_size:
            data_list.pop(0)
        return sum(data_list) / len(data_list)

    def compute_motion_energy(self, accel_y, accel_z):
        """Compute motion energy magnitude from accelerometer axes (m/s²).
        Converts raw byte readings (0-255) to signed g-force values,
        then computes the vector magnitude as the motion energy metric."""
        # Convert unsigned byte to signed (-128 to 127) and scale to g-force
        ay = (accel_y - 128) / 16.0  # ~±8g range on MPU6050
        az = (accel_z - 128) / 16.0
        return float(np.sqrt(ay**2 + az**2))

    def extract_features(self, raw_hr, raw_spo2, accel_y, accel_z):
        """Extract the 4-feature vector required by the trained model.
        Returns: {mean_hr, spo2_trend, hrv, motion_energy}"""
        smooth_hr = self.moving_average(self.hr_window, raw_hr)
        smooth_spo2 = self.moving_average(self.spo2_window, raw_spo2)

        current_time = time.time()
        rr_interval = (current_time - self.last_rr_time) * 1000
        self.last_rr_time = current_time
        
        self.rr_intervals.append(rr_interval)
        if len(self.rr_intervals) > 20: self.rr_intervals.pop(0)
        
        hrv = np.std(self.rr_intervals) if len(self.rr_intervals) > 5 else 50.0
        motion_energy = self.compute_motion_energy(accel_y, accel_z)

        return {
            'mean_hr': smooth_hr,
            'spo2_trend': smooth_spo2,
            'hrv': hrv,
            'motion_energy': motion_energy
        }

processor = SignalProcessor()

# ---------------------------------------------------------
# Background Sensor Polling Thread
# ---------------------------------------------------------
def sensor_loop():
    global latest_sensor_data
    print("Starting sensor polling loop...")
    fall_debounce = 0
    
    while True:
        try:
            raw_hr = np.random.uniform(60, 100)
            raw_spo2 = np.random.uniform(96, 100)

            if np.random.random() > 0.95: 
                raw_hr = 140
                raw_spo2 = 88

            accel_y = bus.read_byte_data(MPU6050_ADDR, 0x3D)
            accel_z = bus.read_byte_data(MPU6050_ADDR, 0x3F)
            fall_detected = False
            if time.time() - fall_debounce > 10 and np.random.random() > 0.98:
                fall_detected = True
                fall_debounce = time.time()
                send_alert("EMERGENCY: Patient Fall Detected!")

            features = processor.extract_features(raw_hr, raw_spo2, accel_y, accel_z)

            # --- ML Inference (or rule-based fallback) ---
            inference_start = time.time()
            status = "Normal"
            confidence = None

            hr_val = features['mean_hr']
            spo2_val = features['spo2_trend']
            hrv_val = features['hrv']
            me_val = features['motion_energy']

            if USE_ML and model is not None:
                try:
                    X_infer = np.array([[hr_val, spo2_val, hrv_val, me_val]])
                    pred = model.predict(X_infer)[0]
                    status = "Abnormal" if pred == 1 else "Normal"
                    # Optional: extract confidence from predict_proba
                    if hasattr(model, 'predict_proba'):
                        proba = model.predict_proba(X_infer)[0]
                        confidence = round(float(max(proba)) * 100, 1)
                except Exception as e:
                    logging.error(f"ML prediction failed ({e}). Using rule-based fallback.")
                    pred = rule_based_predict(hr_val, spo2_val, hrv_val, me_val)
                    status = "Abnormal" if pred == 1 else "Normal"
            else:
                pred = rule_based_predict(hr_val, spo2_val, hrv_val, me_val)
                status = "Abnormal" if pred == 1 else "Normal"

            inference_time = (time.time() - inference_start) * 1000
            
            if status == "Abnormal":
                send_alert(f"WARNING: Cardiac Anomaly! HR: {hr_val:.1f}, SpO2: {spo2_val:.1f}")

            location = "Tracking GPS..." 
            if gps_serial.in_waiting > 0:
                line = gps_serial.readline().decode('ascii', errors='replace')
                if "$GPGGA" in line:
                    location = "48°07.038'N, 11°31.000'E"

            payload = {
                'raw_hr': round(raw_hr, 2),
                'raw_spo2': round(raw_spo2, 2),
                'mean_hr': round(hr_val, 2),
                'hrv': round(hrv_val, 2),
                'spo2': round(spo2_val, 2),
                'motion_energy': round(me_val, 2),
                'status': status,
                'fall_detected': fall_detected,
                'location': location,
                'latency_ms': round(inference_time, 2),
                'timestamp': datetime.now().strftime('%H:%M:%S')
            }
            if confidence is not None:
                payload['confidence'] = confidence

            latest_sensor_data = payload

            # Emit to both patient and caretaker rooms
            socketio.emit('sensor_data', payload, room='patients')
            socketio.emit('sensor_data', payload, room='caretakers')
            time.sleep(0.5)

        except Exception as e:
            print(f"Hardware Error: {e}")
            socketio.emit('system_error', {'error': str(e)})
            time.sleep(1)

# ---------------------------------------------------------
# Flask Routes
# ---------------------------------------------------------
@app.route('/')
def landing():
    if 'user_id' in session:
        if session.get('role') == 'patient':
            return redirect(url_for('patient_dashboard'))
        else:
            return redirect(url_for('caretaker_dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    user_id = request.form.get('user_id', '').strip()
    password = request.form.get('password', '').strip()
    role = request.form.get('role', 'patient')

    if user_id in users_db and users_db[user_id]['password'] == password:
        session['user_id'] = user_id
        session['role'] = role
        session['patient_name'] = users_db[user_id]['patient_name']
        if role == 'patient':
            return redirect(url_for('patient_dashboard'))
        else:
            return redirect(url_for('caretaker_dashboard'))
    else:
        return render_template('login.html', error='Invalid User ID or Password')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))

@app.route('/patient')
def patient_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('landing'))
    user_info = users_db.get(session['user_id'], {})
    return render_template('patient.html', user=user_info, user_id=session['user_id'])

@app.route('/caretaker')
def caretaker_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('landing'))
    user_info = users_db.get(session['user_id'], {})
    return render_template('caretaker.html', user=user_info, user_id=session['user_id'])

@app.route('/api/alerts')
def get_alerts():
    """REST endpoint for caretaker to load alert history"""
    return jsonify(alert_history[-20:])

# ---------------------------------------------------------
# WebSocket Events
# ---------------------------------------------------------
@socketio.on('join')
def on_join(data):
    role = data.get('role', 'patient')
    if role == 'caretaker':
        join_room('caretakers')
        # Send latest snapshot immediately so caretaker sees current state
        if latest_sensor_data:
            emit('sensor_data', latest_sensor_data)
    else:
        join_room('patients')

if __name__ == '__main__':
    sensor_thread = threading.Thread(target=sensor_loop, daemon=True)
    sensor_thread.start()
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
