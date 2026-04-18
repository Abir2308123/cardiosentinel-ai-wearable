import logging
from flask import Flask, request, jsonify, render_template
from datetime import datetime
<<<<<<< HEAD
=======
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from collections import deque
>>>>>>> bd902bdae060a44419c49b2a61ef1a3b9b6e9f07

# Optional ML
import joblib
import os

# Optional realtime UI
from flask_socketio import SocketIO

# ---------------- CONFIG ----------------
USE_MOCK_FALLBACK = False
MODEL_PATH = "trained_model.pkl"

# ---------------- INIT ----------------
app = Flask(__name__)
latest_data = {}
socketio = SocketIO(app, cors_allowed_origins="*")

logging.basicConfig(level=logging.INFO)

# ---------------- LOAD ML MODEL ----------------
model = None
if os.path.exists(MODEL_PATH):
    try:
        model = joblib.load(MODEL_PATH)
        logging.info("✅ ML model loaded successfully")
    except Exception as e:
        logging.warning(f"⚠️ Failed to load model: {e}")
else:
    logging.warning("⚠️ No ML model found")

# ---------------- ROUTE ----------------
@app.route('/api/sensor-data', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.get_json()
        global latest_data
        latest_data = data

        # -------- EXTRACT DATA --------
        heart_rate = data.get("heart_rate")
        spo2 = data.get("spo2")
        g_force = data.get("g_force")
        fall_detected = data.get("fall_detected")
        latitude = data.get("latitude")
        longitude = data.get("longitude")

        # -------- LOG --------
        print("\n📡 ESP32 DATA RECEIVED")
        print(f"❤️ HR: {heart_rate}")
        print(f"🫁 SpO2: {spo2}")
        print(f"📉 G-Force: {g_force}")
        print(f"🚨 Fall: {fall_detected}")
        print(f"📍 Location: {latitude}, {longitude}")

        # -------- ML PREDICTION --------
        prediction = None
        if model:
            try:
                prediction = model.predict([[heart_rate, spo2, g_force]])[0]
                print(f"🧠 ML Prediction: {prediction}")
            except Exception as e:
                print("ML Error:", e)

        # -------- ALERT LOGIC --------
        alerts = []

        if fall_detected:
            alerts.append("🚨 FALL DETECTED")

        if spo2 is not None and spo2 < 92:
            alerts.append("⚠️ LOW SpO2")

        if heart_rate is not None and (heart_rate < 50 or heart_rate > 120):
            alerts.append("⚠️ ABNORMAL HEART RATE")

        if alerts:
            print("\n🚨 ALERTS:")
            for alert in alerts:
                print(alert)

        # -------- SEND TO FRONTEND --------
        socketio.emit("sensor_update", {
            "heart_rate": heart_rate,
            "spo2": spo2,
            "g_force": g_force,
            "fall_detected": fall_detected,
            "latitude": latitude,
            "longitude": longitude,
            "prediction": prediction,
            "alerts": alerts,
            "timestamp": str(datetime.now())
        })

        return jsonify({
            "status": "success",
            "alerts": alerts,
            "prediction": str(prediction)
        }), 200

    except Exception as e:
        logging.error(f"❌ Error processing data: {e}")
        return jsonify({"error": str(e)}), 500


<<<<<<< HEAD
# ---------------- HEALTH CHECK ----------------
=======
# ---------------------------------------------------------
# Background Sensor Polling Thread (mock fallback)
# ---------------------------------------------------------
last_esp32_data_time = time.time()
USE_MOCK_FALLBACK = True   # Set False to rely only on ESP32

def sensor_loop():
    global latest_sensor_data, last_esp32_data_time
    print("Starting mock sensor polling loop (fallback mode)...")
    fall_debounce = 0
    
    while True:
        # If ESP32 data arrived recently, skip mock generation
        if time.time() - last_esp32_data_time < 10:
            time.sleep(1)
            continue

        try:
            raw_hr = np.random.uniform(60, 100)
            raw_spo2 = np.random.uniform(96, 100)
>>>>>>> bd902bdae060a44419c49b2a61ef1a3b9b6e9f07

@app.route('/')
def dashboard():
    return render_template('index.html')

<<<<<<< HEAD
=======
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
# ESP32 Data Ingestion Endpoint
# ---------------------------------------------------------
@app.route('/api/sensor-data', methods=['POST'])
def receive_sensor_data():
    global last_esp32_data_time, latest_sensor_data
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400

        # Extract fields sent by ESP32
        hr = data.get('heart_rate', 0)
        spo2 = data.get('spo2', 0)
        g_force = data.get('g_force', 0.0)
        fall = data.get('fall_detected', False)
        lat = data.get('latitude', 0.0)
        lng = data.get('longitude', 0.0)
        temp = data.get('temperature', 0.0)

        # Update last receive time
        last_esp32_data_time = time.time()

        # Maintain rolling HR buffer for HRV calculation (std of last 10 HR values)
        if not hasattr(receive_sensor_data, 'hr_history'):
            receive_sensor_data.hr_history = deque(maxlen=10)
        if hr > 0:
            receive_sensor_data.hr_history.append(hr)
        hrv = np.std(receive_sensor_data.hr_history) if len(receive_sensor_data.hr_history) > 1 else 50.0

        # Use g_force as motion_energy
        motion_energy = float(g_force)

        # Run prediction (ML or rule-based)
        if USE_ML and model is not None:
            X = np.array([[hr, spo2, hrv, motion_energy]])
            pred = model.predict(X)[0]
            status = "Abnormal" if pred == 1 else "Normal"
        else:
            pred = rule_based_predict(hr, spo2, hrv, motion_energy)
            status = "Abnormal" if pred == 1 else "Normal"

        # Trigger alerts if needed
        if status == "Abnormal":
            send_alert(f"Cardiac anomaly from ESP32: HR={hr}, SpO2={spo2}")
        if fall:
            send_alert("EMERGENCY: Fall detected by ESP32!")

        # Build payload for WebSocket clients
        location_str = f"https://maps.google.com/?q={lat},{lng}" if lat != 0 and lng != 0 else "GPS not fixed"
        payload = {
            'raw_hr': hr,
            'raw_spo2': spo2,
            'mean_hr': hr,
            'hrv': round(hrv, 2),
            'spo2': spo2,
            'motion_energy': motion_energy,
            'status': status,
            'fall_detected': fall,
            'location': location_str,
            'temperature': temp,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }
        latest_sensor_data = payload

        # Broadcast to all connected clients
        socketio.emit('sensor_data', payload, room='patients')
        socketio.emit('sensor_data', payload, room='caretakers')

        return jsonify({'status': 'ok'}), 200

    except Exception as e:
        logging.error(f"Error processing sensor data: {e}")
        return jsonify({'error': str(e)}), 500

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
>>>>>>> bd902bdae060a44419c49b2a61ef1a3b9b6e9f07

@app.route('/latest')
def latest():
    return latest_data
# ---------------- MAIN ----------------
if __name__ == '__main__':
<<<<<<< HEAD
    print("\n🔥 SERVER STARTED")
    socketio.run(app, host='0.0.0.0', port=5000)
=======
    if USE_MOCK_FALLBACK:
        sensor_thread = threading.Thread(target=sensor_loop, daemon=True)
        sensor_thread.start()
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
>>>>>>> bd902bdae060a44419c49b2a61ef1a3b9b6e9f07
