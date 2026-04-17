# CardioSentinel AI Wearable

CardioSentinel is an end-to-end cardiac monitoring system utilizing an ESP32 hardware device and a Raspberry Pi server. The ESP32 gathers real-time biometric and location data, which is published via MQTT to the Raspberry Pi. The Pi performs continuous inference using a Machine Learning model to detect arrhythmia risks and fall events, serving a real-time web dashboard.

## System Architecture
*   **Hardware / Edge:** ESP32 with MAX30102 (HR/SpO2), MPU6050 (Motion/Fall), and NEO-6M (GPS).
*   **Message Broker:** Mosquitto MQTT running locally on the Raspberry Pi.
*   **Backend Server:** Python Flask with SocketIO and Scikit-learn (Joblib) for ML inference.
*   **Frontend Dashboard:** Modern Glassmorphism UI (HTML/CSS/JS) with Chart JS.

---

## 1. Raspberry Pi Setup Instructions

### Step 1: Update System & Install MQTT Broker
First, ensure your Raspberry Pi is up to date and install the Mosquitto MQTT broker.
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y mosquitto mosquitto-clients
```

Restart the Mosquitto service to ensure it is running:
```bash
sudo systemctl enable mosquitto
sudo systemctl restart mosquitto
```

### Step 2: Set up the Python Environment
Check out this repository to your Raspberry Pi. Then create a virtual environment to install dependencies safely.
```bash
cd cardiosentinel-ai-wearable/server
python3 -m venv venv
source venv/bin/activate
```

Next, install the required packages:
```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Copy the `.env.example` file to `.env` and fill in your actual credentials.
```bash
cp ../.env.example ../.env
```
*Note: Make sure to set a unique `FLASK_SECRET_KEY` and your Pi's actual IP for `MQTT_BROKER` if connecting from outside.*

### Step 4: Ensure Machine Learning Model is Present
Make sure the `trained_model.pkl` file is located in the root `cardiosentinel-ai-wearable` directory. The AI relies on this model file for predicting arrhythmia risk.

---

## 2. Running the Server

With the virtual environment activated, run the Python server script:
```bash
python app.py
```
*   The Flask-SocketIO server should now be running.
*   The script automatically connects to the local Mosquitto broker on `127.0.0.1` at port `1883`, listening to `cardiosentinel/telemetry`.

You can now view the dashboard by opening a web browser on any device on the same network and navigating to:
```
http://<RASPBERRY_PI_IP_ADDRESS>:5000
```

---

## 3. ESP32 Setup Instructions

The firmware is located in the `esp32_firmware/` directory.

### Libraries Required (Install via Arduino IDE Library Manager)
*   `PubSubClient` by Nick O'Leary
*   `TinyGPSPlus` by Mikal Hart
*   `ArduinoJson` by Benoit Blanchon
*   `MAX30105 Particle Sensor` by SparkFun (Works for MAX30102)
*   `Adafruit MPU6050` by Adafruit

### Wiring Guide
*   **MAX30102 & MPU6050 (I2C Shared)**
    *   SDA -> GPIO 21
    *   SCL -> GPIO 22
    *   VIN -> 3.3V
    *   GND -> GND
*   **NEO-6M GPS (UART)**
    *   TX -> GPIO 16 (ESP32 RX)
    *   RX -> GPIO 17 (ESP32 TX)
    *   VCC -> 3.3V / 5V (Check your module version)
    *   GND -> GND

### Configuration
Before flashing the ESP32, open `esp32_firmware.ino` and update the following lines:
```cpp
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* mqtt_server = "192.168.1.100"; // Replace with your Raspberry Pi's IP!
```

After flashing, the ESP32 will automatically connect to your WiFi, connect to your Pi's MQTT broker, and publish data every 500ms to `cardiosentinel/telemetry`.
