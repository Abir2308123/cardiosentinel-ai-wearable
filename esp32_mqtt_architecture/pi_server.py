import json
import logging
import numpy as np
import paho.mqtt.client as mqtt
import joblib
from flask import Flask
from flask_socketio import SocketIO

# ==========================================
# 1. FLASK APP & SOCKET.IO SETUP
# ==========================================
app = Flask(__name__)
# Enable CORS for SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# ==========================================
# 2. LOAD MACHINE LEARNING MODEL
# ==========================================
try:
    # Loads the trained ML model. Make sure trained_model.pkl is placed next to this script.
    model = joblib.load('../trained_model.pkl')
    print("[INFO] AI Model loaded successfully.")
except Exception as e:
    print(f"[ERROR] Could not load ML model: {e}")
    model = None

# ==========================================
# 3. HTML DASHBOARD TEMPLATE (Embedded)
# ==========================================
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>CardioSentinel Live</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: Arial, sans-serif; background: #121212; color: white; text-align: center; padding: 50px; }
        .card { background: #1e1e1e; padding: 20px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 8px rgba(0,0,0,0.5); }
        .metric { font-size: 24px; margin: 10px; }
        .value { font-size: 32px; font-weight: bold; color: #00f0ff; }
        .status-normal { color: #00ff00; font-size: 28px; font-weight: bold; margin-top: 20px; }
        .status-abnormal { color: #ff0000; font-size: 28px; font-weight: bold; margin-top: 20px; border: 2px solid red; padding: 10px; border-radius: 5px; animation: blink 1s infinite;}
        @keyframes blink { 50% { opacity: 0.5; } }
    </style>
</head>
<body>
    <h1>CardioSentinel Live Monitor</h1>
    <div class="card">
        <div class="metric">Heart Rate: <span class="value" id="hr">--</span> BPM</div>
        <div class="metric">SpO2: <span class="value" id="spo2">--</span> %</div>
        <div class="metric">Motion: <span class="value" id="motion">--</span> G</div>
        <div id="status" class="status-normal">WAITING FOR DATA</div>
    </div>

    <script>
        var socket = io();
        socket.on('sensor_update', function(data) {
            document.getElementById('hr').textContent = data.hr;
            document.getElementById('spo2').textContent = data.spo2;
            document.getElementById('motion').textContent = data.motion;
            
            var statusEl = document.getElementById('status');
            if (data.status === 'Abnormal') {
                statusEl.textContent = '⚠ ABNORMAL / ANOMALY DETECTED ⚠';
                statusEl.className = 'status-abnormal';
            } else {
                statusEl.textContent = 'NORMAL';
                statusEl.className = 'status-normal';
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    # Serves the embedded HTML dashboard on the root URL
    return HTML_PAGE

# ==========================================
# 4. MQTT BROKER HANDLING
# ==========================================
def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Connected with result code {rc}")
    # Subscribes to the topic where ESP32 is pushing data
    client.subscribe("cardio/data")

def on_message(client, userdata, msg):
    payload = msg.payload.decode('utf-8')
    print(f"[MQTT] Received: {payload}")
    try:
        data = json.loads(payload)
        hr = data.get('hr', 0)
        spo2 = data.get('spo2', 0)
        motion = data.get('motion', 0.0)
        
        # Static HRV value since it's hard to simulate without raw ECG/PPG waves
        hrv = 50 
        
        # Format feature vector: [hr, spo2, hrv, motion]
        # (Must match the dimensions your trained Random Forest expects)
        features = np.array([[hr, spo2, hrv, motion]])
        
        # Run ML Prediction
        status = "Normal"
        if model is not None:
            prediction = model.predict(features)[0]
            if prediction == 1:
                status = "Abnormal"
        else:
            # Fallback simple rule if model is missing
            if hr > 100 or spo2 < 95:
                status = "Abnormal"
                
        # Send processed data and ML prediction to the web dashboard via WebSockets
        socket_payload = {
            'hr': hr,
            'spo2': spo2,
            'motion': motion,
            'status': status
        }
        socketio.emit('sensor_update', socket_payload)
        
    except Exception as e:
        print(f"[ERROR] Failed to parse/predict: {e}")

# Setup MQTT Client Thread
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

# ==========================================
# 5. START SERVER
# ==========================================
if __name__ == '__main__':
    # Connects to the local mosquitto broker running on the Pi
    try:
        mqtt_client.connect("127.0.0.1", 1883, 60)
        mqtt_client.loop_start()  # Run MQTT logic in a background thread
    except Exception as e:
        print(f"[WARNING] Could not connect to local Mosquitto TCP broker: {e}")

    print("[INFO] Starting Flask WebSocket Server on http://0.0.0.0:5000")
    # Starts the Flask Web Server on port 5000
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
