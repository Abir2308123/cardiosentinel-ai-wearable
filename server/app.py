import os
import json
import logging
import pandas as pd
from flask import Flask, render_template
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import joblib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask and SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'cardiosentinel_secret')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Configuration
MQTT_BROKER = os.getenv('MQTT_BROKER', '127.0.0.1')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
TOPIC_TELEMETRY = os.getenv('TOPIC_TELEMETRY', 'cardiosentinel/telemetry')
TOPIC_ALERT = os.getenv('TOPIC_ALERT', 'cardiosentinel/alert')
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'trained_model.pkl')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load ML Model
try:
    if os.path.exists(MODEL_PATH):
        model = joblib.load(MODEL_PATH)
        logger.info(f"Successfully loaded ML model from {MODEL_PATH}")
    else:
        logger.warning(f"Model file not found at {MODEL_PATH}. Inference will use dummy predictions.")
        model = None
except Exception as e:
    logger.error(f"Error loading model: {e}")
    model = None

# MQTT Callbacks
def on_connect(client, userdata, flags, rc):
    # paho-mqtt 1.x / 2.x compatibility: rc is return code, sometimes properties
    if hasattr(rc, 'getName'):
        rc = rc.value
    if rc == 0:
        logger.info(f"Connected to MQTT Broker at {MQTT_BROKER}")
        client.subscribe(TOPIC_TELEMETRY)
    else:
        logger.error(f"Failed to connect to MQTT Broker, return code {rc}")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)
        
        # Prepare features for inference: ['heart_rate', 'spo2', 'hrv', 'motion_energy']
        features = pd.DataFrame([{
            'heart_rate': data.get('heart_rate', 0),
            'spo2': data.get('spo2', 0),
            'hrv': data.get('hrv', 0),
            'motion_energy': data.get('motion_energy', 0.0)
        }])
        
        # Perform inference
        prediction = 0
        risk_level = "Low"
        
        if model is not None:
            # Predict
            try:
                pred_result = model.predict(features)
                prediction = int(pred_result[0])
                
                # Check for probability if available to give confidence
                if hasattr(model, 'predict_proba'):
                    prob = model.predict_proba(features)[0][1]
                    if prob > 0.8: risk_level = "High"
                    elif prob > 0.4: risk_level = "Medium"
            except Exception as e:
                logger.error(f"Inference error: {e}")
        else:
            # Fallback mock logic if no model
            if data.get('heart_rate', 0) > 100 or data.get('spo2', 100) < 90:
                prediction = 1
                risk_level = "High"
        
        # Determine Arrhythmia/Risk Status
        has_arrhythmia = bool(prediction)
        
        alert_payload = {
            "arrhythmia_risk": has_arrhythmia,
            "risk_level": risk_level,
            "fall_detected": bool(data.get('fall_detected', 0))
        }
        
        # Publish Alert back to MQTT
        client.publish(TOPIC_ALERT, json.dumps(alert_payload))
        
        # Combine telemetry and alert for the dashboard
        dashboard_data = {
            **data,
            **alert_payload
        }
        
        # Emit over WebSockets
        socketio.emit('telemetry_update', dashboard_data)
        
    except Exception as e:
        logger.error(f"Error processing MQTT message: {e}")

# Initialize MQTT Client
# paho-mqtt > 2.0 requires CallbackAPIVersion
try:
    from paho.mqtt.enums import CallbackAPIVersion
    mqtt_client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2, client_id="CardioSentinel-Server")
except ImportError:
    mqtt_client = mqtt.Client(client_id="CardioSentinel-Server")

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

def start_mqtt():
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()  # Run in background thread
    except Exception as e:
        logger.error(f"Failed to start MQTT loop: {e}")

# Routes
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    start_mqtt()
    logger.info("Starting Flask-SocketIO Server on http://0.0.0.0:5000")
    # run with eventlet
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
