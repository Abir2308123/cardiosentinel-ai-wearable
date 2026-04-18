import logging
from flask import Flask, request, jsonify, render_template
from datetime import datetime

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


# ---------------- HEALTH CHECK ----------------

@app.route('/')
def dashboard():
    return render_template('index.html')


@app.route('/latest')
def latest():
    return latest_data
# ---------------- MAIN ----------------
if __name__ == '__main__':
    print("\n🔥 SERVER STARTED")
    socketio.run(app, host='0.0.0.0', port=5000)
